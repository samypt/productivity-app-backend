from typing import Optional
from sqlmodel import SQLModel
from uuid import UUID
from .task import TaskList


class BoardListCreate(SQLModel):
    name: str
    board_id: str
    position: int




class BoardListRead(BoardListCreate):
    id: UUID

    class Config:
        orm_mode = True




class BoardListUpdate(SQLModel):
    name: Optional[str] = None
    position: Optional[int] = None



class FullBoardList(BoardListRead):
    tasks: TaskList

    class Config:
        orm_mode = True