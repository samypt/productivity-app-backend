from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel
from uuid import UUID


class TeamCreate(SQLModel):
    name: str
    description: Optional[str] = None



class TeamRead(TeamCreate):
    id: UUID
    created_at: Optional[datetime]

    class Config:
        orm_mode = True

class TeamUpdate(SQLModel):
    description: Optional[str] = None
