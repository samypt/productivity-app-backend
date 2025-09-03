from datetime import datetime
from typing import Optional, List
from sqlmodel import SQLModel
from uuid import UUID
from .member import MemberRead
from .user import UserPublic


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




class TeamFullInfo(TeamRead):
    membership: MemberRead
    members: List[UserPublic]

    class Config:
        orm_mode = True




class TeamList(SQLModel):
    teams: List[TeamFullInfo]

    class Config:
        orm_mode = True