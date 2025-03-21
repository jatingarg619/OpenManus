from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import base64
from PIL import Image
import io
from datetime import datetime

from app.agent.manus import Manus
from app.schema import Message
from app.logger import setup_logger
from app.tool.browser_use_tool import BrowserUseTool

app = FastAPI()

# Get the base directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / 'static'
TEMP_DIR = STATIC_DIR / 'temp'

# Create directories if they don't exist
STATIC_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Mount static files directory
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create API-specific logger
logger = setup_logger("api")

class BrowserEvent:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket

    async def on_browser_update(self, data: dict):
        """Handle browser state updates"""
        try:
            await self.websocket.send_text(json.dumps({
                "type": "browser_event",
                "content": {
                    "url": data.get("url"),
                    "timestamp": str(datetime.now())
                }
            }))
        except Exception as e:
            logger.error(f"Error sending browser update: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    agent = None
    
    try:
        agent = Manus()
        browser_event = BrowserEvent(websocket)
        
        while True:
            try:
                data = await websocket.receive_text()
                request = json.loads(data)
                prompt = request.get("prompt")
                
                if prompt:
                    logger.info(f"\n{prompt}\n")  # Log the user's prompt
                    
                # Add message observer to capture agent's thoughts and actions
                async def message_observer(message: Message):
                    """Send real-time updates about agent's progress"""
                    try:
                        if message.role == "assistant":
                            await websocket.send_text(json.dumps({
                                "type": "thinking",
                                "content": message.content
                            }))
                        elif message.role == "tool":
                            await websocket.send_text(json.dumps({
                                "type": "action",
                                "content": f"Using tool: {message.name}\nResult: {message.content}"
                            }))
                    except WebSocketDisconnect:
                        logger.warning("WebSocket disconnected while sending updates")
                        raise

                try:
                    # Register message observer
                    agent.memory.add_observer(message_observer)
                    
                    # Initialize agent with the prompt
                    await agent.update_memory("user", prompt)
                    
                    # Send initial status
                    await websocket.send_text(json.dumps({
                        "type": "status",
                        "content": "Agent is analyzing your request..."
                    }))
                    
                    # Run agent
                    result = await agent.run()
                    
                    # Send final result
                    await websocket.send_text(json.dumps({
                        "type": "result",
                        "content": result
                    }))
                    
                except Exception as e:
                    logger.error(f"Error during agent execution: {str(e)}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "content": f"Agent error: {str(e)}"
                    }))
                finally:
                    # Clean up observer and memory
                    agent.memory.remove_observer(message_observer)
                    agent.memory.clear()
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(str(e))
                break
                    
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}", exc_info=True)
    finally:
        if agent:
            logger.info("Cleaning up agent resources")
            agent.memory.clear()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Add any additional health checks here
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/docs")
async def get_docs():
    """Swagger documentation endpoint"""
    return {"openapi_url": "/openapi.json"} 