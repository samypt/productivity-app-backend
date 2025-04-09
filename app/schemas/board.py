from typing import Optional
from sqlmodel import SQLModel
from uuid import UUID


class BoardCreate(SQLModel):
    name: str
    project_id: str




class BoardRead(BoardCreate):
    id: UUID

    class Config:
        orm_mode = True




class BoardUpdate(SQLModel):
    name: Optional[str]