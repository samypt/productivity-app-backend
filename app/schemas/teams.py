from datetime import datetime
from typing import Optional, List
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




class TeamList(SQLModel):
    teams: List[TeamRead]

    class Config:
        orm_mode = True