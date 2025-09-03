from fastapi import WebSocket, status
from typing import List, Dict, Set
import json
import os
from jose import JWTError, jwt
from dotenv import load_dotenv
import logging

# Logger
logger = logging.getLogger(__name__)

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

def verify_jwt_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# class ConnectionManager:
#     def __init__(self):
#         self.active_connections: List[WebSocket] = []
#
#     async def connect(self, websocket: WebSocket):
#         await websocket.accept()
#         self.active_connections.append(websocket)
#
#     def disconnect(self, websocket: WebSocket):
#         self.active_connections.remove(websocket)
#
#     async def broadcast(self, message: str):
#         for connection in self.active_connections:
#             await connection.send_text(message)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.socket_to_user: Dict[WebSocket, str] = {}

    def _get_token_from_headers(self, websocket: WebSocket):
        subprotocols = websocket.headers.get("sec-websocket-protocol")
        if subprotocols:
            return subprotocols.split(",")[0].strip()
        return None

    async def connect(self, websocket: WebSocket):
        token = self._get_token_from_headers(websocket)

        try:
            payload = verify_jwt_token(token)
            user_id = payload.get("id")
            if not user_id:
                raise ValueError("Invalid token payload")
        except Exception as e:
            logger.warning(f"WebSocket auth failed: {e}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Add connection
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        self.socket_to_user[websocket] = user_id

        await websocket.accept(subprotocol=token)
        logger.info(f"User {user_id} connected.")

    async def disconnect(self, websocket: WebSocket):
        user_id = self.socket_to_user.get(websocket)

        if user_id:
            conns = self.active_connections.get(user_id, set())
            if websocket in conns:
                try:
                    await websocket.close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket: {e}")
                conns.remove(websocket)
                if not conns:
                    del self.active_connections[user_id]
            del self.socket_to_user[websocket]

            logger.info(f"User {user_id} disconnected.")

    async def send_to_user(self, user_id: str, message: dict):
        conns = self.active_connections.get(user_id, set())
        for conn in list(conns):  # Make a copy to avoid mutation issues
            try:
                await conn.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send message to {user_id}: {e}")
                await self.disconnect(conn)

    async def broadcast(self, message: dict):
        for user_id in list(self.active_connections):
            await self.send_to_user(user_id, message)

ws_connection_manager = ConnectionManager()