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

    async def broadcast(self, message: dict):
        """Envía un mensaje JSON a todos los clientes WebSocket conectados."""
        disconnected = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error enviando mensaje WebSocket: {e}")
                disconnected.append(connection)

        for conn in disconnected:
            self.disconnect(conn)

# Instancia singleton
ws_manager = ConnectionManager()