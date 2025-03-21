import asyncio
import os
from pathlib import Path
from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from playwright.async_api import async_playwright
import json
from urllib.parse import unquote
from fastapi.responses import FileResponse, HTMLResponse
import mimetypes
from fastapi.staticfiles import StaticFiles
import base64

# Create API for browser control
router = APIRouter()
current_browser_url = ""
browser_state = {
    "currentUrl": "",
    "pageContent": "",
    "pageTitle": "",
    "error": None
}

# Store browser instance
browser_instance = None
page_instance = None

class UrlUpdate(BaseModel):
    url: str

class BrowserAction(BaseModel):
    action: str
    selector: str = None
    text: str = None
    url: str = None
    file_path: str = None  # Changed from filepath to file_path

class SPAStaticFiles(StaticFiles):
    """Custom static files handler that serves index.html for SPA routes"""
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as e:
            if e.status_code == 404:
                return await super().get_response("index.html", scope)
            raise e

# Get the base directory for serving files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def convert_to_file_url(filepath: str) -> str:
    """Convert a local file path to a file:// URL"""
    if not filepath:
        return None
        
    # Handle both absolute and relative paths
    abs_path = os.path.abspath(filepath)
    return f"file://{abs_path}"

def get_file_mime_type(filepath: str) -> str:
    """Get the MIME type for a file"""
    mime_type, _ = mimetypes.guess_type(filepath)
    if filepath.endswith('.js'):
        return 'application/javascript'
    return mime_type or 'application/octet-stream'

@router.get("/current-url")
async def get_current_url():
    """Get the current browser URL"""
    return {"url": browser_state["currentUrl"]}

@router.get("/state")
async def get_browser_state():
    """Get the full browser state"""
    return browser_state

@router.post("/update-url")
async def update_url(url_data: UrlUpdate):
    """Update the current browser URL"""
    global browser_state
    browser_state["currentUrl"] = url_data.url
    return {"status": "success", "url": url_data.url}

@router.post("/open-local-file")
async def open_local_file(request: dict):
    """Open a local file and return its contents"""
    try:
        file_path = request.get("file_path")
        if not file_path:
            raise HTTPException(status_code=400, detail="file_path is required")

        # Remove file:// prefix if present
        if file_path.startswith("file://"):
            file_path = file_path[7:]

        # Convert to absolute path
        abs_path = os.path.abspath(file_path)
        
        # Security check
        if not os.path.exists(abs_path):
            raise HTTPException(status_code=404, detail=f"File not found: {abs_path}")
            
        if not os.access(abs_path, os.R_OK):
            raise HTTPException(status_code=403, detail="File not accessible")

        # Read file contents
        with open(abs_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Get MIME type
        mime_type = mimetypes.guess_type(abs_path)[0] or 'text/plain'
        if abs_path.endswith('.html'):
            mime_type = 'text/html'

        # Update browser state
        browser_state["currentUrl"] = f"file://{abs_path}"
        browser_state["pageContent"] = content

        return {
            "content": content,
            "mimeType": mime_type,
            "fileName": os.path.basename(abs_path)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/action")
async def perform_action(action: BrowserAction, background_tasks: BackgroundTasks):
    """Perform a browser action"""
    global browser_instance, page_instance
    
    try:
        # Initialize browser if needed
        if not browser_instance:
            background_tasks.add_task(initialize_browser)
            return {"status": "initializing", "message": "Browser is initializing"}
            
        if action.action == "navigate":
            # Handle file:// URLs by converting to filepath
            if action.url and action.url.startswith("file://"):
                action.file_path = action.url[7:]  # Remove file:// prefix
                action.url = None
            
            if action.file_path:
                # Get file contents
                try:
                    with open(action.file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Update browser state
                    browser_state["currentUrl"] = f"file://{action.file_path}"
                    browser_state["pageContent"] = content
                    
                    return {
                        "status": "success",
                        "content": content,
                        "url": f"file://{action.file_path}"
                    }
                except Exception as e:
                    raise HTTPException(status_code=500, detail=str(e))
            
            # Handle web URLs
            url = action.url
            if not url:
                raise HTTPException(status_code=400, detail="URL is required")
                
            # Execute navigation in background
            background_tasks.add_task(navigate_to, url)
            return {"status": "navigating", "url": url}
            
        elif action.action == "click":
            if not action.selector:
                raise HTTPException(status_code=400, detail="Selector is required for clicking")
            
            background_tasks.add_task(click_element, action.selector)
            return {"status": "clicking", "selector": action.selector}
            
        elif action.action == "type":
            if not action.selector or not action.text:
                raise HTTPException(
                    status_code=400, 
                    detail="Selector and text are required for typing"
                )
                
            background_tasks.add_task(type_text, action.selector, action.text)
            return {"status": "typing", "selector": action.selector}
            
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Unknown action: {action.action}"
            )
            
    except Exception as e:
        browser_state["error"] = str(e)
        raise HTTPException(status_code=500, detail=str(e))

async def initialize_browser():
    """Initialize the browser instance"""
    global browser_instance, page_instance
    
    try:
        playwright = await async_playwright().start()
        browser_instance = await playwright.chromium.launch(headless=True)
        page_instance = await browser_instance.new_page()
        
        # Set up event handlers for URL changes
        async def handle_url_change(url):
            browser_state["currentUrl"] = url
            
        page_instance.on("framenavigated", lambda frame: 
            asyncio.create_task(handle_url_change(frame.url)) 
            if frame is page_instance.main_frame else None
        )
        
    except Exception as e:
        browser_state["error"] = f"Failed to initialize browser: {str(e)}"

async def navigate_to(url: str):
    """Navigate to a URL or local file"""
    global page_instance, browser_state
    
    try:
        if not page_instance:
            raise Exception("Browser not initialized")
            
        # Handle file:// URLs specially
        if url.startswith("file://"):
            # Remove file:// prefix for local file access
            filepath = url[7:]
            if not os.path.exists(filepath):
                raise Exception(f"File not found: {filepath}")
                
        await page_instance.goto(url, wait_until="networkidle")
        
        # Update browser state
        browser_state["currentUrl"] = url
        browser_state["pageTitle"] = await page_instance.title()
        browser_state["pageContent"] = await page_instance.content()
        browser_state["error"] = None
        
    except Exception as e:
        browser_state["error"] = f"Navigation failed: {str(e)}"

async def click_element(selector):
    """Click an element"""
    global page_instance, browser_state
    
    try:
        if not page_instance:
            raise Exception("Browser not initialized")
            
        await page_instance.click(selector)
        
        # Update browser state after action
        browser_state["currentUrl"] = page_instance.url
        browser_state["pageTitle"] = await page_instance.title()
        browser_state["pageContent"] = await page_instance.content()
        browser_state["error"] = None
        
    except Exception as e:
        browser_state["error"] = f"Click failed: {str(e)}"

async def type_text(selector, text):
    """Type text into an element"""
    global page_instance, browser_state
    
    try:
        if not page_instance:
            raise Exception("Browser not initialized")
            
        await page_instance.fill(selector, text)
        
        # Update browser state after action
        browser_state["currentUrl"] = page_instance.url
        browser_state["pageTitle"] = await page_instance.title()
        browser_state["pageContent"] = await page_instance.content()
        browser_state["error"] = None
        
    except Exception as e:
        browser_state["error"] = f"Type failed: {str(e)}"

# Create the FastAPI app
app = FastAPI(
    title="AI Browser API", 
    description="API for AI-controlled browser automation",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Mount static files BEFORE including the router
app.mount("/files", StaticFiles(directory=BASE_DIR), name="files")

# Add router
app.include_router(router, prefix="/api/browser")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001) 