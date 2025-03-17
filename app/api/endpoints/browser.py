from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

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