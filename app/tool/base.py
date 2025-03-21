from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BaseTool(ABC, BaseModel):
    name: str
    description: str
    parameters: Optional[dict] = None

    class Config:
        arbitrary_types_allowed = True

    async def __call__(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""
        return await self.execute(**kwargs)

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """Execute the tool with given parameters."""

    def to_param(self) -> Dict:
        """Convert tool to function call format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolResult(BaseModel):
    """Represents the result of a tool execution."""

    output: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    system: Optional[str] = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    def __bool__(self):
        return any(getattr(self, field) for field in self.__fields__)

    def __add__(self, other: "ToolResult"):
        def combine_fields(
            field: Optional[str], other_field: Optional[str], concatenate: bool = True
        ):
            if field and other_field:
                if concatenate:
                    return field + other_field
                raise ValueError("Cannot combine tool results")
            return field or other_field

        return ToolResult(
            output=combine_fields(self.output, other.output),
            error=combine_fields(self.error, other.error),
            system=combine_fields(self.system, other.system),
        )

    def __str__(self):
        return f"Error: {self.error}" if self.error else self.output

    def replace(self, **kwargs):
        """Returns a new ToolResult with the given fields replaced."""
        # return self.copy(update=kwargs)
        return type(self)(**{**self.dict(), **kwargs})


class CLIResult(ToolResult):
    """A ToolResult that can be rendered as a CLI output."""


class ToolFailure(ToolResult):
    """A ToolResult that represents a failure."""


class AgentAwareTool:
    agent: Optional = None


class ToolCollection:
    """Collection of tools"""
    def __init__(self, *tools):
        self.tools = list(tools)
        self.tool_map = {tool.name: tool for tool in tools}

    def add_tool(self, tool):
        """Add a tool to the collection"""
        self.tools.append(tool)
        self.tool_map[tool.name] = tool

    def to_params(self):
        """Convert all tools to function call format"""
        return [tool.to_param() for tool in self.tools]

    def get_tool(self, name):
        """Get a tool by name"""
        return self.tool_map.get(name)

    async def execute(self, **kwargs):
        """Execute a tool by name with arguments"""
        name = kwargs.pop("name", None)
        tool_input = kwargs.pop("tool_input", {})
        
        if not name:
            return "Error: Tool name is required"
            
        tool = self.get_tool(name)
        if not tool:
            return f"Error: Tool '{name}' not found"
        
        print(f"DEBUG: Executing tool {name}, has event_handler: {hasattr(tool, 'event_handler')}")
        if hasattr(tool, 'event_handler'):
            print(f"DEBUG: Event handler for {name} is: {tool.event_handler}")
        
        try:
            result = await tool.execute(**tool_input)
            return str(result)
        except Exception as e:
            print(f"Error executing {name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return f"Error: {str(e)}"
