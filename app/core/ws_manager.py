import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger("casaos-backup")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"[WebSocket] Cliente conectado. Total activos: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"[WebSocket] Cliente desconectado. Total activos: {len(self.active_connections)}")

    async def broadcast_progress(self, job_id: str, percentage: int, status_message: str):
        payload = {
            "job_id": job_id,
            "percentage": percentage,
            "message": status_message
        }
        
        connections = list(self.active_connections)
        for connection in connections:
            try:
                await connection.send_json(payload)
            except Exception as e:
                logger.warning(f"[WebSocket Error] Error emitiendo a cliente: {e}")
                self.disconnect(connection)

ws_manager = ConnectionManager()