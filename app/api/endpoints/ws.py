from fastapi import APIRouter, WebSocket
from fastapi.websockets import WebSocketDisconnect
from app.agent.manus import Manus

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("\n=== WebSocket Connected ===\n")
    
    # Create a callback function to send messages back to the client
    async def send_websocket_message(message):
        print("\n=== Sending WebSocket Message ===")
        print(f"Message: {message}")
        try:
            # Ensure browser events are properly typed
            if isinstance(message, dict):
                if "content" in message and "url" in message.get("content", {}):
                    message["type"] = "browser_event"
                elif "type" not in message:
                    message["type"] = "result"
            
            print(f"Formatted message: {message}")
            await websocket.send_json(message)
            print("Message sent successfully")
            print("=== Message Send Complete ===\n")
        except Exception as e:
            print(f"Error sending message: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Initialize the agent with the callback
    agent = Manus()
    agent.send_websocket_message = send_websocket_message
    await agent.initialize()  # Initialize after setting the callback
    print("Agent initialized with WebSocket callback")  # Debug log
    
    try:
        while True:
            data = await websocket.receive_text()
            print(f"\n=== Received WebSocket Message ===\n{data}\n")
            response = await agent.process_message(data)
            if response:
                await send_websocket_message(response)
    except WebSocketDisconnect:
        print("\n=== WebSocket Disconnected ===\n")
    except Exception as e:
        print(f"\n=== WebSocket Error ===\n{str(e)}")
        import traceback
        traceback.print_exc() 