from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel
from uuid import UUID


class ProjectCreate(SQLModel):
    name: str
    description: Optional[str]
    team_id: str




class ProjectRead(ProjectCreate):
    id: UUID
    created_at: Optional[datetime]

    class Config:
        orm_mode = True




class ProjectUpdate(SQLModel):
    description: Optional[str]
