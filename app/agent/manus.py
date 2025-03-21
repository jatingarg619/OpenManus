from pydantic import Field
import asyncio

from app.agent.toolcall import ToolCallAgent
from app.prompt.manus import NEXT_STEP_PROMPT, SYSTEM_PROMPT
from app.tool import Terminate, ToolCollection
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.file_saver import FileSaver
from app.tool.google_search import GoogleSearch
from app.tool.python_execute import PythonExecute


class Manus(ToolCallAgent):
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
            GoogleSearch(),  # Will now properly handle parameters
            BrowserUseTool(),
            FileSaver(),
            Terminate()
        )
    )

    max_steps: int = 20
    duplicate_threshold: int = 3  # Increase threshold for better retry handling

    async def initialize(self):
        """Initialize agent and its tools"""
        # Connect browser tool to agent's event handler
        browser_tool = self.available_tools.get_tool("browser_use")
        if browser_tool:
            browser_tool.event_handler = self.send_browser_event
            print("Connected browser tool to event handler")
        
        # Also connect Google Search tool to event handler
        google_tool = self.available_tools.get_tool("google_search")
        if google_tool:
            google_tool.event_handler = self.send_browser_event
            print("Connected Google Search tool to event handler")
        
        return await super().initialize()

    async def send_browser_event(self, event_data):
        """Send browser events to the frontend"""
        print(f"BROWSER EVENT DEBUG: {event_data}")
        print(f"EVENT TYPE: {event_data.get('type')}")
        
        # Ensure the event has a valid type
        if 'type' not in event_data:
            if 'content' in event_data and 'html' in event_data['content']:
                event_data['type'] = 'browser_content'
            elif 'content' in event_data and 'url' in event_data['content']:
                event_data['type'] = 'browser_event'
            else:
                event_data['type'] = 'browser_event'  # Default type
        
        print(f"EVENT CONTENT: {event_data.get('content')}")
        
        # Cache the event if WebSocket isn't ready yet
        if not hasattr(self, 'send_websocket_message'):
            print("WebSocket not available, storing event for later delivery")
            if not hasattr(self, '_pending_events'):
                self._pending_events = []
            self._pending_events.append(event_data)
            return
        
        try:
            # Send with a small delay to ensure client readiness
            await asyncio.sleep(0.1)
            await self.send_websocket_message(event_data)
            print(f"Browser {event_data['type']} event sent to WebSocket successfully")
        except Exception as e:
            print(f"Error sending browser event: {e}")
            import traceback
            traceback.print_exc()
