from datetime import datetime
from app.schemas.teams import TeamRead
from typing import Optional, List
from sqlmodel import SQLModel
from uuid import UUID



class ProjectCreate(SQLModel):
    name: str
    description: Optional[str] = None
    team_id: str




class ProjectRead(ProjectCreate):
    id: UUID
    created_at: Optional[datetime]

    class Config:
        orm_mode = True




class ProjectUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None




class ProjectList(SQLModel):
    projects: List[ProjectRead]
    team: Optional[TeamRead]

    class Config:
        orm_mode = True
