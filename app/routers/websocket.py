from app.database import get_session
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlmodel import Session
from .notifications import get_unread_notifications_count
from ..services.manager import ws_connection_manager
import os


load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

router = APIRouter()
db_session = Depends(get_session)



@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket , session: Session = db_session):
    await ws_connection_manager.connect(websocket)

    try:
        while True:
            user_id = ws_connection_manager.socket_to_user.get(websocket)
            if user_id is None:
                raise ValueError("Invalid token payload")
            notifications_count = get_unread_notifications_count(user_id, session)
            await ws_connection_manager.send_to_user(
                user_id=user_id,
                message={"type": "notifications", "msg": "Hello!", "count" : notifications_count}
            )

            data = await websocket.receive_json()
            # Optional: handle incoming messages from client
            print("Received:", data)

    except WebSocketDisconnect:
        await ws_connection_manager.disconnect(websocket)
    except Exception as e:
        print("Error:", e)
        await ws_connection_manager.disconnect(websocket)