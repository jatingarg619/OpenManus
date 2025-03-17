from pydantic import Field
import asyncio
import os
from typing import List, Dict, Any, Optional

from app.agent.toolcall import ToolCallAgent
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tool import Terminate, ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.file_saver import FileSaver
from app.tool.google_search import GoogleSearch
from app.tool.python_execute import PythonExecute
from app.agent.base import BaseAgent
from app.tool.base import BaseTool
from app.llm import LLM


class Manus(BaseAgent):
    """
    A versatile general-purpose agent that uses planning to solve various tasks.

    This agent extends PlanningAgent with a comprehensive set of tools and capabilities,
    including Python execution, web browsing, file operations, and information retrieval
    to handle a wide range of user requests.
    """

    name: str = "Manus"
    description: str = (
        "A versatile agent that can solve various tasks using multiple tools"
    )

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    # Add general-purpose tools to the tool collection
    available_tools: ToolCollection = Field(
        default_factory=lambda: ToolCollection(
            PythonExecute(timeout=30),  # Add timeout to prevent hanging
            GoogleSearch(),
            BrowserUseTool(),
            FileSaver(),
            Terminate()
        )
    )

    max_steps: int = 20
    duplicate_threshold: int = 3  # Increase threshold for better retry handling

    # Define tools as a dictionary field
    tools: Dict[str, BaseTool] = Field(default_factory=dict)
    conversation_history: List[Dict[str, Any]] = []

    def __init__(self, **data):
        # Initialize BaseAgent first (Pydantic model initialization)
        super().__init__(**data)
        
        # Convert tools list to dictionary if needed
        if 'tools' in data and isinstance(data['tools'], list):
            data['tools'] = {tool.name: tool for tool in data['tools']}
        
        # Store tools
        self.tools = data.get('tools', {})
        self.conversation_history = []
        self.thinking_enabled = True
        self.progress_enabled = True

    async def initialize(self):
        """Initialize agent and its tools"""
        # Connect browser tool to agent's event handler
        browser_tool = self.available_tools.get_tool("browser_use")
        if browser_tool:
            browser_tool.event_handler = self.send_browser_event
            print("Connected browser tool to event handler")
        
        return await super().initialize()

    async def send_browser_event(self, event_data):
        """Send browser events to the frontend"""
        print(f"Sending browser event from agent: {event_data}")
        if hasattr(self, 'send_websocket_message'):
            try:
                await self.send_websocket_message(event_data)
                print("Browser event sent to WebSocket")
            except Exception as e:
                print(f"Error sending browser event: {e}")
                import traceback
                traceback.print_exc()
        else:
            print("Warning: send_websocket_message not available")

    async def process_message(self, message: str) -> Dict[str, Any]:
        """Process user message with thinking, progress updates, and results"""
        # Add user message to history
        self.conversation_history.append({"role": "user", "content": message})
        
        # 1. Initial thinking about the task
        await self.send_thinking(f"Analyzing your request: {message}")
        await asyncio.sleep(1)
        
        # 2. Generate a plan with multiple steps
        await self.send_thinking("Developing a structured approach to help with your request...")
        
        # Get initial plan from LLM
        plan_prompt = f"Create a task plan to address this user request: {message}"
        plan_response = await self.llm.generate(plan_prompt)
        
        # Parse plan into steps
        plan_steps = self._extract_steps(plan_response)
        
        # 3. Show plan steps as thinking
        for step in plan_steps:
            await self.send_thinking(f"Planning: {step}")
        
        # 4. Execute plan with progress updates
        results = []
        files = []
        
        for i, step in enumerate(plan_steps):
            # Show progress 
            await self.send_progress(f"Working on step {i+1}/{len(plan_steps)}: {step}")
            
            # Execute step using LLM and tools
            step_result = await self._execute_step(step, message)
            results.append(step_result)
            
            # If step produced files, collect them
            if "files" in step_result:
                files.extend(step_result["files"])
        
        # 5. Prepare final response
        final_response = await self._generate_final_response(message, results)
        
        # 6. Send final result with files
        await self.send_result(final_response, files)
        
        return {"response": final_response, "files": files}
    
    async def _execute_step(self, step: str, context: str) -> Dict[str, Any]:
        """Execute a single step of the plan"""
        # Determine which tool to use based on step
        tool_name = self._determine_tool(step)
        
        if tool_name in self.tools:
            # Execute tool
            await self.send_thinking(f"Using {tool_name} to {step}")
            tool_result = await self.tools[tool_name].execute(step=step, context=context)
            
            # Check if file was created
            if tool_name == "file_saver" and tool_result.output:
                file_path = tool_result.output
                file_name = os.path.basename(file_path)
                file_type = self._determine_file_type(file_path)
                file_size = os.path.getsize(file_path)
                
                return {
                    "output": tool_result.output,
                    "files": [{
                        "name": file_name,
                        "type": file_type,
                        "path": file_path,
                        "size": f"{file_size // 1024} KB"
                    }]
                }
            
            return {"output": tool_result.output}
        else:
            # Use LLM for this step
            await self.send_thinking(f"Researching: {step}")
            llm_response = await self.llm.generate(f"Complete this task: {step}\nContext: {context}")
            return {"output": llm_response}
    
    def _determine_tool(self, step: str) -> str:
        """Determine which tool to use based on step description"""
        if "save" in step.lower() or "create file" in step.lower():
            return "file_saver"
        elif "browse" in step.lower() or "search" in step.lower():
            return "browser_use"
        elif "code" in step.lower() or "script" in step.lower():
            return "python_execute"
        return "none"
    
    def _determine_file_type(self, file_path: str) -> str:
        """Determine file type from extension"""
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".html":
            return "html"
        elif ext == ".txt":
            return "text"
        elif ext == ".md":
            return "markdown"
        elif ext == ".json":
            return "json"
        return "file"
    
    def _extract_steps(self, plan: str) -> List[str]:
        """Extract steps from a plan text"""
        lines = plan.strip().split("\n")
        steps = []
        
        for line in lines:
            line = line.strip()
            # Look for numbered steps or bullet points
            if (line.startswith("- ") or 
                line.startswith("* ") or 
                (line[0].isdigit() and line[1:3] in [". ", ") "])):
                
                # Remove the bullet or number
                step = line[2:] if line[0] in "-*" else line[line.index(" ")+1:]
                steps.append(step)
        
        # If no structured steps found, create at least one
        if not steps and plan:
            steps = [plan]
            
        return steps
    
    async def _generate_final_response(self, message: str, results: List[Dict[str, Any]]) -> str:
        """Generate a final response summarizing all results"""
        summary_prompt = f"Summarize the results of these steps into a final response for the user:\n"
        
        for i, result in enumerate(results):
            summary_prompt += f"Step {i+1} result: {result.get('output', 'No output')}\n"
            
        summary_prompt += f"\nOriginal request: {message}\n"
        summary_prompt += "Provide a comprehensive final response that addresses the user's request fully."
        
        final_response = await self.llm.generate(summary_prompt)
        return final_response

    async def step(self) -> str:
        """Execute a single step in the agent's workflow."""
        # This will be called by the BaseAgent's run method
        # The simplest implementation is to delegate to our process_message logic
        current_messages = self.memory.messages
        if current_messages:
            # Get the last user message if any
            last_user_message = next((msg.content for msg in reversed(current_messages) 
                                     if msg.role == "user"), None)
            if last_user_message:
                # Process this step based on the last user message
                result = await self._execute_single_step(last_user_message)
                return result.get("output", "Step completed")
        
        return "No action taken"
    
    async def _execute_single_step(self, context: str) -> Dict[str, Any]:
        """Execute a single step based on context"""
        # Determine best action for this step
        step_prompt = f"What's the next action I should take for: {context}"
        step_plan = await self.llm.generate(step_prompt)
        
        # Execute the planned step
        await self.send_thinking(f"Executing: {step_plan}")
        
        # Determine tool and execute
        tool_name = self._determine_tool(step_plan)
        if tool_name in self.tools:
            # Use the appropriate tool
            tool_result = await self.tools[tool_name].execute(step=step_plan, context=context)
            return {"output": tool_result.output}
        else:
            # Use LLM to generate a response
            response = await self.llm.generate(
                f"Respond to this: {context}\nBased on this plan: {step_plan}"
            )
            # Add response to memory
            await self.update_memory("assistant", response)
            return {"output": response}
