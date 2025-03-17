from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import List, Literal, Optional, Dict, Any
import asyncio

from pydantic import BaseModel, Field, model_validator

from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Memory, Message
from app.config import config


class BaseAgent(BaseModel, ABC):
    """Abstract base class for managing agent state and execution.

    Provides foundational functionality for state transitions, memory management,
    and a step-based execution loop. Subclasses must implement the `step` method.
    """

    # Core attributes
    name: str = Field(..., description="Unique name of the agent")
    description: Optional[str] = Field(None, description="Optional agent description")

    # Prompts
    system_prompt: Optional[str] = Field(
        None, description="System-level instruction prompt"
    )
    next_step_prompt: Optional[str] = Field(
        None, description="Prompt for determining next action"
    )

    # Dependencies
    llm: LLM = Field(default_factory=LLM, description="Language model instance")
    memory: Memory = Field(default_factory=Memory, description="Agent's memory store")
    state: AgentState = Field(
        default=AgentState.IDLE, description="Current agent state"
    )

    # Execution control
    max_steps: int = Field(default=10, description="Maximum steps before termination")
    current_step: int = Field(default=0, description="Current step in execution")

    duplicate_threshold: int = 2

    def __init__(self, **data):
        super().__init__(**data)
        self.thinking_enabled = True
        self.progress_enabled = True

    class Config:
        arbitrary_types_allowed = True
        extra = "allow"  # Allow extra fields for flexibility in subclasses

    @model_validator(mode="after")
    def initialize_agent(self) -> "BaseAgent":
        """Initialize agent with default settings if not provided."""
        if self.llm is None or not isinstance(self.llm, LLM):
            self.llm = LLM(config_name=self.name.lower())
        if not isinstance(self.memory, Memory):
            self.memory = Memory()
        return self

    @asynccontextmanager
    async def state_context(self, new_state: AgentState):
        """Context manager for safe agent state transitions.

        Args:
            new_state: The state to transition to during the context.

        Yields:
            None: Allows execution within the new state.

        Raises:
            ValueError: If the new_state is invalid.
        """
        if not isinstance(new_state, AgentState):
            raise ValueError(f"Invalid state: {new_state}")

        previous_state = self.state
        self.state = new_state
        try:
            yield
        except Exception as e:
            self.state = AgentState.ERROR  # Transition to ERROR on failure
            raise e
        finally:
            self.state = previous_state  # Revert to previous state

    async def update_memory(
        self,
        role: Literal["user", "system", "assistant", "tool"],
        content: str,
        **kwargs,
    ) -> None:
        """Add a message to the agent's memory."""
        message_map = {
            "user": Message.user_message,
            "system": Message.system_message,
            "assistant": Message.assistant_message,
            "tool": lambda content, **kw: Message.tool_message(content, **kw),
        }

        if role not in message_map:
            raise ValueError(f"Unsupported message role: {role}")

        msg_factory = message_map[role]
        msg = msg_factory(content, **kwargs) if role == "tool" else msg_factory(content)
        await self.memory.add_message(msg)

    async def run(self, request: Optional[str] = None) -> str:
        """Execute the agent's main loop asynchronously."""
        if self.state != AgentState.IDLE:
            raise RuntimeError(f"Cannot run agent from state: {self.state}")

        if request:
            await self.update_memory("user", request)

        results: List[str] = []
        stuck_count = 0
        max_stuck_retries = 3

        async with self.state_context(AgentState.RUNNING):
            while (
                self.current_step < self.max_steps and 
                self.state != AgentState.FINISHED
            ):
                self.current_step += 1
                logger.info(f"Executing step {self.current_step}/{self.max_steps}")
                
                try:
                    step_result = await self.step()
                    
                    # Check for stuck state
                    if self.is_stuck():
                        stuck_count += 1
                        if stuck_count >= max_stuck_retries:
                            logger.warning("Agent appears to be stuck, terminating execution")
                            break
                        self.handle_stuck_state()
                    else:
                        stuck_count = 0  # Reset stuck count if we make progress
                    
                    results.append(f"Step {self.current_step}: {step_result}")
                except Exception as e:
                    error_msg = f"Error in step {self.current_step}: {str(e)}"
                    logger.error(error_msg)
                    results.append(error_msg)
                    break

            if self.current_step >= self.max_steps:
                self.current_step = 0
                self.state = AgentState.IDLE
                results.append(f"Terminated: Reached max steps ({self.max_steps})")

        return "\n".join(results) if results else "No steps executed"

    @abstractmethod
    async def step(self) -> str:
        """Execute a single step in the agent's workflow.

        Must be implemented by subclasses to define specific behavior.
        """

    def handle_stuck_state(self):
        """Handle stuck state by adding a prompt to change strategy"""
        stuck_prompt = "\
        Observed duplicate responses. Consider new strategies and avoid repeating ineffective paths already attempted."
        self.next_step_prompt = f"{stuck_prompt}\n{self.next_step_prompt}"
        logger.warning(f"Agent detected stuck state. Added prompt: {stuck_prompt}")

    def is_stuck(self) -> bool:
        """Check if the agent is stuck in a loop by detecting duplicate content"""
        if len(self.memory.messages) < 2:
            return False

        last_message = self.memory.messages[-1]
        if not last_message.content:
            return False

        # Count identical content occurrences
        duplicate_count = sum(
            1
            for msg in reversed(self.memory.messages[:-1])
            if msg.role == "assistant" and msg.content == last_message.content
        )

        return duplicate_count >= self.duplicate_threshold

    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value

    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process a user message and return a response"""
        # Override in subclasses
        pass
        
    async def send_thinking(self, thought: str):
        """Send thinking update to frontend"""
        if self.thinking_enabled and config.websocket:
            await config.websocket.send_json({
                "type": "thinking",
                "content": thought
            })
            # Add small delay for realistic effect
            await asyncio.sleep(0.5)
            
    async def send_progress(self, step: str):
        """Send progress update to frontend"""
        if self.progress_enabled and config.websocket:
            await config.websocket.send_json({
                "type": "progress",
                "content": step
            })
            
    async def send_result(self, content: str, files: Optional[List[Dict]] = None):
        """Send final result with any file attachments"""
        if config.websocket:
            await config.websocket.send_json({
                "type": "result",
                "content": content,
                "files": files or []
            })
