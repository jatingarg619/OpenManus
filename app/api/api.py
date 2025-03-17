from fastapi import APIRouter
from app.api.endpoints import ws, health, browser

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(ws.router, tags=["ws"])
api_router.include_router(browser.router, prefix="/browser", tags=["browser"]) 