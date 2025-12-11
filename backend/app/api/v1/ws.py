from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json
import asyncio
from datetime import datetime

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


@router.websocket("/logs")
async def websocket_logs(websocket: WebSocket):
    """Stream real-time logs from all services via Redis pub/sub"""
    await websocket.accept()
    
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings
        
        redis = await aioredis.from_url(settings.REDIS_URL)
        pubsub = redis.pubsub()
        await pubsub.subscribe('system_logs')
        
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.utcnow().isoformat(),
            "source": "system",
            "level": "INFO",
            "message": "🔌 Log stream connected",
            "metadata": {}
        })
        
        # Stream logs
        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    log_data = json.loads(message['data'])
                    await websocket.send_json(log_data)
                except Exception as e:
                    print(f"Error parsing log message: {e}")
                
    except WebSocketDisconnect:
        print("Client disconnected from log stream")
    except Exception as e:
        print(f"WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            await pubsub.unsubscribe('system_logs')
            await redis.close()
        except:
            pass




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



