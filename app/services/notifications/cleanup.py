from sqlmodel import select, Session
from datetime import timedelta
from app.models import Notification
from app.utils.time import get_time_stamp
from app.database import engine

def delete_old_notifications(days: int = 30):
    with Session(engine) as session:
        cutoff = get_time_stamp() - timedelta(days=days)

        statement = select(Notification).where(
            Notification.is_read == True,
            Notification.created_at < cutoff
        )
        old_notifications = session.exec(statement).all()

        for notification in old_notifications:
            session.delete(notification)

        session.commit()
    print("0000000000000000000000000000000000000000000000000000000000000000000000000000000000000")