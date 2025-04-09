from datetime import datetime
from typing import Optional, Literal
from sqlmodel import SQLModel
from uuid import UUID




class MemberCreate(SQLModel):
    team_id: str
    user_id: str
    role: Optional[Literal["owner", "editor", "viewer"]] = "editor"




class MemberRead(MemberCreate):
    id: UUID

    class Config:
        orm_mode = True




class MemberUpdate(SQLModel):
    role: Optional[str]