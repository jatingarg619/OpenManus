import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import traceback

from app.config import config
from app.api.websocket import WebSocketHandler
from app.agent.manus import Manus
from app.llm import LLM
from app.tool.browser_use_tool import BrowserUseTool
from app.tool.python_execute import PythonExecute
from app.tool.file_saver import FileSaver
from app.tool.google_search import GoogleSearch
from app.tool import Terminate
from app.logger import logger

# Initialize FastAPI app
app = FastAPI(
    title="OpenManus API",
    description="API for OpenManus AI assistant",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize LLM with appropriate config
llm = LLM()  # This will use the config from config.toml

# Initialize tools
tools_list = [
    BrowserUseTool(),
    PythonExecute(timeout=30),
    FileSaver(),
    GoogleSearch(),
    Terminate()
]

# Convert tools list to dictionary before passing to Manus
tools_dict = {tool.name: tool for tool in tools_list}

try:
    # Initialize agent with tools as a dictionary
    agent = Manus(
        llm=llm,
        tools=tools_dict  # Pass as dictionary to satisfy Pydantic validation
    )
    ws_handler = WebSocketHandler(agent)
except Exception as e:
    logger.error(f"Error initializing agent: {e}")
    logger.error(traceback.format_exc())
    raise

@app.get("/")
async def root():
    return {"message": "OpenManus API is running"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "components": {
            "agent": agent is not None,
            "websocket": ws_handler is not None,
            "llm": llm is not None,
            "tools": {
                tool_name: True for tool_name in tools_dict.keys()
            }
        }
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_handler.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await ws_handler.handle_message(websocket, data)
    except WebSocketDisconnect:
        await ws_handler.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await ws_handler.disconnect(websocket)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port) 