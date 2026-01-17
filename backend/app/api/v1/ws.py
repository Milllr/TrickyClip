from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Set
import json
import asyncio
from datetime import datetime
import sys

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
    
    redis = None
    pubsub = None
    
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings
        
        print("[WS] Client connected to log stream")
        
        # send initial connection message
        await websocket.send_json({
            "timestamp": datetime.utcnow().isoformat(),
            "source": "system",
            "level": "SUCCESS",
            "message": "🔌 websocket connected successfully",
            "metadata": {}
        })
        
        # connect to redis
        try:
            redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            pubsub = redis.pubsub()
            await pubsub.subscribe('system_logs')
            print("[WS] Subscribed to system_logs channel")
            
            # send confirmation
            await websocket.send_json({
                "timestamp": datetime.utcnow().isoformat(),
                "source": "system",
                "level": "INFO",
                "message": "📡 listening for system logs...",
                "metadata": {}
            })
        except Exception as e:
            print(f"[WS] Failed to connect to Redis: {e}")
            await websocket.send_json({
                "timestamp": datetime.utcnow().isoformat(),
                "source": "system",
                "level": "ERROR",
                "message": f"⚠️  redis connection failed: {str(e)}",
                "metadata": {}
            })
            # keep connection open for heartbeat even if Redis fails
            
        # heartbeat and message loop
        last_heartbeat = datetime.utcnow()
        
        while True:
            try:
                # send heartbeat every 30 seconds
                if (datetime.utcnow() - last_heartbeat).total_seconds() > 30:
                    await websocket.send_json({
                        "timestamp": datetime.utcnow().isoformat(),
                        "source": "system",
                        "level": "DEBUG",
                        "message": "💓 heartbeat",
                        "metadata": {}
                    })
                    last_heartbeat = datetime.utcnow()
                
                # check for messages from Redis if connected
                if pubsub:
                    message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=1.0)
                    if message and message['type'] == 'message':
                        try:
                            log_data = json.loads(message['data'])
                            await websocket.send_json(log_data)
                        except Exception as e:
                            print(f"[WS] Error parsing log message: {e}")
                else:
                    # no Redis - just wait a bit
                    await asyncio.sleep(1.0)
                    
            except asyncio.TimeoutError:
                # no message received, continue
                continue
            except WebSocketDisconnect:
                print("[WS] Client disconnected normally")
                break
            except Exception as e:
                print(f"[WS] Error in message loop: {e}")
                break
                
    except WebSocketDisconnect:
        print("[WS] Client disconnected from log stream")
    except Exception as e:
        print(f"[WS] WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[WS] Cleaning up connection")
        if pubsub:
            try:
                await pubsub.unsubscribe('system_logs')
                await pubsub.close()
            except Exception as e:
                print(f"[WS] Error unsubscribing: {e}")
        if redis:
            try:
                await redis.close()
            except Exception as e:
                print(f"[WS] Error closing Redis: {e}")




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



