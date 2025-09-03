from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel
from uuid import UUID
from enum import Enum




class NotificationType(str, Enum):
    task = "task"
    event = "event"
    invitation = "invitation"




class NotificationCreate(SQLModel):
    user_id: str
    sender_id: str
    object_type: NotificationType
    object_id: str
    message: Optional[str] = None




class NotificationRespond(SQLModel):
    is_read: bool




class NotificationRead(NotificationCreate):
    id: UUID
    is_read: bool
    created_at: datetime
    updated_at: datetime




class NotificationList(SQLModel):
    notifications: List[NotificationRead]




class NotificationCount(SQLModel):
    unread_count: int