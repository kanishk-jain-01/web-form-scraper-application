from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, List
import json
import logging

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket client {client_id} connected")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket client {client_id} disconnected")

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to {client_id}: {e}")
                self.disconnect(client_id)

    async def send_json_message(self, data: dict, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_text(json.dumps(data))
            except Exception as e:
                logger.error(f"Failed to send JSON message to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, message: str):
        disconnected_clients = []
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    async def broadcast_json(self, data: dict):
        message = json.dumps(data)
        await self.broadcast(message)

    def get_connection_count(self) -> int:
        return len(self.active_connections)

    def get_connected_clients(self) -> List[str]:
        return list(self.active_connections.keys())


# Global WebSocket manager instance
websocket_manager = WebSocketManager()


async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket endpoint handler"""
    await websocket_manager.connect(websocket, client_id)
    try:
        while True:
            # Listen for incoming messages
            data = await websocket.receive_text()
            
            try:
                # Parse incoming message
                message = json.loads(data)
                logger.info(f"Received WebSocket message from {client_id}: {message}")
                
                # Handle different message types
                message_type = message.get('type')
                
                if message_type == 'ping':
                    # Respond to ping with pong
                    await websocket_manager.send_json_message({
                        'type': 'pong',
                        'message': 'Connection alive'
                    }, client_id)
                
                elif message_type == 'human_input':
                    # Handle human input for HITL workflow
                    logger.info(f"Human input received for client {client_id}: {message.get('input')}")
                    # This would be processed by the job queue/agent system
                    
                else:
                    logger.warning(f"Unknown message type from {client_id}: {message_type}")
                    
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from {client_id}: {data}")
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket client {client_id} disconnected normally")
        websocket_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        websocket_manager.disconnect(client_id)
