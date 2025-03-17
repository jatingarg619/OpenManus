from enum import Enum
from typing import Any, List, Literal, Optional, Union, Callable
import asyncio

from pydantic import BaseModel, Field


class AgentState(str, Enum):
    """Agent execution states"""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


class Function(BaseModel):
    name: str
    arguments: str


class ToolCall(BaseModel):
    """Represents a tool/function call in a message"""

    id: str
    type: str = "function"
    function: Function


class Message(BaseModel):
    """Represents a chat message in the conversation"""

    role: Literal["system", "user", "assistant", "tool"] = Field(...)
    content: Optional[str] = Field(default=None)
    tool_calls: Optional[List[ToolCall]] = Field(default=None)
    name: Optional[str] = Field(default=None)
    tool_call_id: Optional[str] = Field(default=None)

    def __add__(self, other) -> List["Message"]:
        """支持 Message + list 或 Message + Message 的操作"""
        if isinstance(other, list):
            return [self] + other
        elif isinstance(other, Message):
            return [self, other]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(self).__name__}' and '{type(other).__name__}'"
            )

    def __radd__(self, other) -> List["Message"]:
        """支持 list + Message 的操作"""
        if isinstance(other, list):
            return other + [self]
        else:
            raise TypeError(
                f"unsupported operand type(s) for +: '{type(other).__name__}' and '{type(self).__name__}'"
            )

    def to_dict(self) -> dict:
        """Convert message to dictionary format"""
        message = {"role": self.role}
        if self.content is not None:
            message["content"] = self.content
        if self.tool_calls is not None:
            message["tool_calls"] = [tool_call.dict() for tool_call in self.tool_calls]
        if self.name is not None:
            message["name"] = self.name
        if self.tool_call_id is not None:
            message["tool_call_id"] = self.tool_call_id
        return message

    @classmethod
    def user_message(cls, content: str) -> "Message":
        """Create a user message"""
        return cls(role="user", content=content)

    @classmethod
    def system_message(cls, content: str) -> "Message":
        """Create a system message"""
        return cls(role="system", content=content)

    @classmethod
    def assistant_message(cls, content: Optional[str] = None) -> "Message":
        """Create an assistant message"""
        return cls(role="assistant", content=content)

    @classmethod
    def tool_message(cls, content: str, name, tool_call_id: str) -> "Message":
        """Create a tool message"""
        return cls(role="tool", content=content, name=name, tool_call_id=tool_call_id)

    @classmethod
    def from_tool_calls(
        cls, tool_calls: List[Any], content: Union[str, List[str]] = "", **kwargs
    ):
        """Create ToolCallsMessage from raw tool calls.

        Args:
            tool_calls: Raw tool calls from LLM
            content: Optional message content
        """
        formatted_calls = [
            {"id": call.id, "function": call.function.model_dump(), "type": "function"}
            for call in tool_calls
        ]
        return cls(
            role="assistant", content=content, tool_calls=formatted_calls, **kwargs
        )


class Memory:
    def __init__(self):
        self.messages: List[Message] = []
        self._observers: List[Callable[[Message], None]] = []
        self.max_messages: int = 100

    async def add_message(self, message: Message):
        """Add a message and notify observers"""
        try:
            self.messages.append(message)
            # Notify all observers
            for observer in self._observers:
                try:
                    await observer(message)
                except Exception as e:
                    logger.error(f"Error in observer: {str(e)}")
            
            # Optional: Implement message limit
            if len(self.messages) > self.max_messages:
                self.messages = self.messages[-self.max_messages:]
        except Exception as e:
            logger.error(f"Error adding message: {str(e)}")
            raise

    async def add_messages(self, messages: List[Message]):
        """Add multiple messages asynchronously"""
        for message in messages:
            await self.add_message(message)

    def add_observer(self, observer: Callable[[Message], None]):
        """Add an observer to receive message updates"""
        self._observers.append(observer)

    def remove_observer(self, observer: Callable[[Message], None]):
        """Remove an observer"""
        if observer in self._observers:
            self._observers.remove(observer)

    def clear(self) -> None:
        """Clear all messages"""
        self.messages.clear()

    def get_recent_messages(self, n: int) -> List[Message]:
        """Get n most recent messages"""
        return self.messages[-n:]

    def to_dict_list(self) -> List[dict]:
        """Convert messages to list of dicts"""
        return [msg.to_dict() for msg in self.messages]
