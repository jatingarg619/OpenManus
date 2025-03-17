import json
import traceback
from fastapi import WebSocket, WebSocketDisconnect
from app.config import config
from app.agent.manus import Manus
from app.logger import logger

class WebSocketHandler:
    def __init__(self, agent):
        self.agent = agent
        self.active_connections = set()
        # Connect agent to websocket handler for callbacks
        if hasattr(self.agent, 'send_websocket_message'):
            self.agent.send_websocket_message = self.send_message
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        config.websocket = websocket
        logger.info("WebSocket connected")
        
        # Send welcome message
        await websocket.send_json({
            "type": "system",
            "content": "Connected to OpenManus AI. How can I help you today?"
        })
    
    async def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        if config.websocket == websocket:
            config.websocket = None
        logger.info("WebSocket disconnected")
    
    async def send_message(self, message):
        """Send a message to all connected clients"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
    
    async def handle_message(self, websocket: WebSocket, data: str):
        try:
            logger.info(f"Received message: {data}")
            message_data = json.loads(data)
            message_type = message_data.get("type", "")
            content = message_data.get("content", "")
            
            if message_type == "user_input":
                # Process user message through agent
                logger.info(f"Processing user input: {content}")
                
                # Echo back the user message for display
                await websocket.send_json({
                    "type": "user",
                    "content": content
                })
                
                # Process with the agent
                try:
                    await self.agent.process_message(content)
                except Exception as e:
                    error_msg = f"Error processing message: {str(e)}"
                    logger.error(error_msg)
                    logger.error(traceback.format_exc())
                    await websocket.send_json({
                        "type": "error",
                        "content": error_msg
                    })
            
            elif message_type == "browser_action":
                # Handle browser action
                action = message_data.get("action", "")
                details = message_data.get("details", {})
                logger.info(f"Browser action: {action}, details: {details}")
                
                # Could process browser actions here
        
        except Exception as e:
            # Send error message
            error_msg = f"Error handling WebSocket message: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            if websocket in self.active_connections:
                await websocket.send_json({
                    "type": "error",
                    "content": error_msg
                }) 