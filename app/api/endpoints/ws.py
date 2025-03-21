from fastapi import APIRouter, WebSocket
from fastapi.websockets import WebSocketDisconnect
from app.agent.manus import Manus
import asyncio

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("\n=== WebSocket Connected ===\n")
    
    # Create a callback function to send messages back to the client
    async def send_websocket_message(message):
        print("\n=== Sending WebSocket Message ===")
        print(f"Message type: {message.get('type', 'unknown')}")
        
        try:
            # Make sure we pass through browser_content messages as-is
            if isinstance(message, dict) and message.get('type') == 'browser_content':
                print("Sending browser_content message directly")
                # Force a delay to ensure client is ready
                await asyncio.sleep(0.1)
                # Send twice to ensure receipt
                await websocket.send_json(message)
                print("Sent browser_content message")
            elif isinstance(message, dict):
                if "content" in message and "url" in message.get("content", {}):
                    message["type"] = "browser_event"
                elif "type" not in message:
                    message["type"] = "result"
            
            # Debugging
            if isinstance(message, dict) and 'content' in message and isinstance(message['content'], dict):
                if 'html' in message['content']:
                    html_len = len(message['content']['html'])
                    print(f"HTML content length: {html_len} chars")
                    
            await websocket.send_json(message)
            print("Message sent successfully to client")
        except Exception as e:
            print(f"Error sending message: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # Initialize the agent with the callback
    agent = Manus()
    # Explicitly set the websocket message handler
    agent.send_websocket_message = send_websocket_message
    await agent.initialize()  # Initialize after setting the callback
    print("Agent initialized with WebSocket callback")
    
    # Process any pending events that might have been stored
    if hasattr(agent, '_pending_events') and agent._pending_events:
        print(f"Processing {len(agent._pending_events)} pending events")
        for event in agent._pending_events:
            await send_websocket_message(event)
        agent._pending_events = []
    
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