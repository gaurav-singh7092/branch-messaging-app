from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import json

from ..database import get_db
from ..services import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, agent_id: int = Query(None)):
    """
    WebSocket endpoint for real-time messaging.
    Agents connect with their agent_id to receive real-time updates.
    """
    await manager.connect(websocket, agent_id)
    
    try:
        # Send initial connection confirmation
        await manager.send_personal_message({
            "type": "connected",
            "data": {"agent_id": agent_id, "message": "Connected to messaging server"}
        }, websocket)
        
        while True:
            # Receive messages from the WebSocket
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                message_type = message.get("type")
                
                if message_type == "ping":
                    # Respond to ping with pong
                    await manager.send_personal_message({
                        "type": "pong",
                        "data": {}
                    }, websocket)
                
                elif message_type == "typing":
                    # Broadcast typing indicator
                    conversation_id = message.get("data", {}).get("conversation_id")
                    is_typing = message.get("data", {}).get("is_typing", False)
                    
                    if conversation_id and agent_id:
                        await manager.notify_agent_typing(
                            conversation_id, agent_id, is_typing
                        )
                
                elif message_type == "viewing":
                    # Track which conversation agent is viewing
                    conversation_id = message.get("data", {}).get("conversation_id")
                    if conversation_id and agent_id:
                        manager.set_agent_viewing(agent_id, conversation_id)
                
                elif message_type == "stop_viewing":
                    # Remove conversation from agent's viewing list
                    conversation_id = message.get("data", {}).get("conversation_id")
                    if conversation_id and agent_id:
                        manager.remove_agent_viewing(agent_id, conversation_id)
                
            except json.JSONDecodeError:
                await manager.send_personal_message({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                }, websocket)
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, agent_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(websocket, agent_id)
