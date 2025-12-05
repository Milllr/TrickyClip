from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio

router = APIRouter()

# active WebSocket connections
active_connections: Set[WebSocket] = set()

@router.websocket("/progress")
async def websocket_progress(websocket: WebSocket):
    """websocket endpoint for real-time progress updates"""
    await websocket.accept()
    active_connections.add(websocket)
    
    try:
        while True:
            # keep connection alive and receive any client messages
            data = await websocket.receive_text()
            # client can send "ping" to keep alive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        print(f"websocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


async def broadcast_progress(job_id: str, progress: int, status: str, message: str = ""):
    """broadcast progress update to all connected clients"""
    if not active_connections:
        return
    
    payload = json.dumps({
        "type": "job_progress",
        "job_id": job_id,
        "progress": progress,
        "status": status,
        "message": message
    })
    
    # send to all connected clients
    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_text(payload)
        except Exception:
            disconnected.add(connection)
    
    # cleanup disconnected clients
    for conn in disconnected:
        active_connections.discard(conn)

