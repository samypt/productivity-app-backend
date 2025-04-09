from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel
from uuid import UUID


class TeamCreate(SQLModel):
    name: str
    description: Optional[str]



class TeamRead(SQLModel):
    id: UUID
    name: str
    description: Optional[str]
    created_at: Optional[datetime]



class TeamUpdate(SQLModel):
    description: Optional[str]
