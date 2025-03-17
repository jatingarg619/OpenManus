import asyncio
import json
import os
import base64
from typing import Optional, Callable, Dict, Any, List
from PIL import Image
from playwright.async_api import async_playwright, Browser, Page
from datetime import datetime
import aiohttp
from pathlib import Path
from urllib.parse import urljoin, urlparse

from browser_use import Browser as BrowserUseBrowser
from browser_use import BrowserConfig
from browser_use.browser.context import BrowserContext
from browser_use.dom.service import DomService
from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from app.tool.base import BaseTool, ToolResult
from app.logger import setup_logger

MAX_LENGTH = 2000
logger = setup_logger("browser_tool")

class BrowserUseTool(BaseTool):
    name: str = "browser_use"
    description: str = """Interact with a web browser to perform various actions."""
    
    browser: Optional[Browser] = None
    page: Optional[Page] = None
    event_handler: Optional[Callable[[Dict[str, Any]], None]] = None
    context: Optional[BrowserContext] = None
    dom_service: Optional[DomService] = None
    
    # Add base directory for local files
    base_dir: str = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    async def _ensure_browser(self) -> None:
        """Ensure browser is initialized"""
        if not self.browser:
            logger.info("Initializing browser...")
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True  # Run in headless mode
            )
            self.page = await self.browser.new_page()
            
            # Set up event handlers
            def handle_navigation(frame):
                if frame is self.page.main_frame:
                    asyncio.create_task(self._notify_url_change(frame.url))
            
            self.page.on("framenavigated", handle_navigation)
            logger.info("Browser initialized successfully")

    async def _notify_url_change(self, url: str) -> None:
        """Notify frontend of URL changes via API endpoint"""
        try:
            print(f"Updating URL to: {url}")
            # Change port to 8001 to match our test server
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8001/api/browser/update-url", 
                    json={"url": url}
                ) as response:
                    if response.status == 200:
                        print(f"Successfully updated URL via API")
                    else:
                        print(f"Failed to update URL: {await response.text()}")
        except Exception as e:
            print(f"Error updating URL: {e}")
            
        # Still try the event handler as a fallback
        if self.event_handler:
            try:
                await self.event_handler({
                    "type": "browser_event",
                    "content": {"url": url}
                })
            except Exception as e:
                print(f"Error with event handler: {e}")

    async def _update_url(self, url: str) -> None:
        """Update the current URL in the browser state"""
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(
                    "http://localhost:8001/api/browser/update-url",
                    json={"url": url}
                )
        except Exception as e:
            logger.error(f"Failed to update URL: {e}")

    async def execute(self, **kwargs) -> ToolResult:
        """Execute browser actions"""
        try:
            await self._ensure_browser()
            action = kwargs.get("action", "navigate")
            url = kwargs.get("url")
            filepath = kwargs.get("filepath")

            logger.info(f"Executing action '{action}' with URL: {url} or file: {filepath}")

            if action == "navigate":
                # If we have a filepath, prioritize it
                if filepath:
                    # Convert relative paths to absolute using base_dir
                    if not os.path.isabs(filepath):
                        filepath = os.path.join(self.base_dir, filepath)

                    # Get file contents from server
                    async with aiohttp.ClientSession() as session:
                        response = await session.post(
                            "http://localhost:8001/api/browser/open-local-file",
                            json={"file_path": filepath}
                        )
                        if response.status == 200:
                            data = await response.json()
                            # Set content directly in page
                            await self.page.set_content(data["content"])
                            # Update URL to show filepath
                            await self._update_url(f"file://{filepath}")
                            return ToolResult(output=f"Loaded local file: {filepath}")
                        else:
                            error_text = await response.text()
                            return ToolResult(error=f"Failed to load file: {error_text}")
                elif url:
                    await self.page.goto(url, wait_until="networkidle")
                    return ToolResult(output=f"Navigated to {url}")
                else:
                    return ToolResult(error="Either URL or filepath is required")

            elif action == "click":
                selector = kwargs.get("selector")
                if not selector:
                    return ToolResult(error="Selector is required for clicking")
                
                await self.page.click(selector)
                current_url = self.page.url
                await self._update_url(current_url)
                return ToolResult(output=f"Clicked element: {selector}")

            elif action == "read":
                # Get page content
                content = await self.page.content()
                return ToolResult(output=f"Read page content: {content[:MAX_LENGTH]}")

            elif action == "type":
                selector = kwargs.get("selector")
                text = kwargs.get("text")
                if not selector or not text:
                    return ToolResult(error="Selector and text are required for typing")
                
                await self.page.type(selector, text)
                return ToolResult(output=f"Typed text into {selector}")

            else:
                return ToolResult(error=f"Unknown action: {action}. Supported actions are: navigate, click, read, type")

        except Exception as e:
            logger.error(f"Browser action failed: {e}", exc_info=True)
            return ToolResult(error=str(e))

    async def cleanup(self) -> None:
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close()
            self.browser = None
            self.page = None

    def __del__(self) -> None:
        """Ensure cleanup when object is destroyed"""
        if self.browser:
            try:
                asyncio.run(self.cleanup())
            except RuntimeError:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self.cleanup())
                loop.close()
