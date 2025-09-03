from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel
from uuid import UUID
from enum import Enum
from pydantic import EmailStr


class Role(str, Enum):
    owner = "owner"
    editor = "editor"
    viewer = "viewer"


class InviteStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"




class InviteCreate(SQLModel):
    team_id: str
    role: Optional["Role"] = Role.editor
    email: EmailStr




class InviteRead(InviteCreate):
    id: UUID
    invited_by: UUID
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    status: Optional["InviteStatus"]




class InviteRespond(SQLModel):
    status: InviteStatus