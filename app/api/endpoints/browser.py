from fastapi import APIRouter, HTTPException, StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import os
from pydantic import BaseModel

router = APIRouter()

# Get the base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
STATIC_DIR = BASE_DIR / 'static'
TEMP_DIR = STATIC_DIR / 'temp'

# Create directories if they don't exist
STATIC_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Mount static files directory
router.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory storage for browser state
current_browser_url = "https://example.com"

class UrlUpdate(BaseModel):
    url: str

@router.get("/current-url")
async def get_current_url():
    """Get the current browser URL"""
    return {"url": current_browser_url}

@router.post("/update-url")
async def update_url(url_data: UrlUpdate):
    """Update the current browser URL"""
    global current_browser_url
    current_browser_url = url_data.url
    print(f"Updated browser URL to: {current_browser_url}")
    return {"status": "success", "url": current_browser_url} 