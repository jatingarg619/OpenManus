# Look for the WebSocket handler function that sends messages to the client
# It should be sending messages with these types:
# - 'start' (when starting a new request)
# - 'executing' (when running a command)
# - 'creating' (when creating a file)
# - 'searching' (when doing a search)
# - 'browsing' (when browsing the web)
# - 'progress' (for general progress updates)
# - 'response' (for final responses)

# Example of what to look for:
async def send_thinking_update(websocket, message):
    await websocket.send_json({
        "type": "thinking",
        "content": message
    })

# This should be updated to:
async def send_thinking_update(websocket, message, task=None):
    await websocket.send_json({
        "type": "progress",
        "task": task or "Analyzing request...",
        "message": message,
        "status": "in_progress"
    }) 