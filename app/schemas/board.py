from typing import Optional, List
from sqlmodel import SQLModel
from uuid import UUID
from .board_list import FullBoardList, BoardListRead


class BoardCreate(SQLModel):
    name: str
    project_id: str




class BoardRead(BoardCreate):
    id: UUID

    class Config:
        orm_mode = True




class BoardUpdate(SQLModel):
    name: Optional[str] = None




class FullBoard(BoardRead):
    lists: List[FullBoardList]

    class Config:
        orm_mode = True




class BoardLists(BoardRead):
    lists: List[BoardListRead]

    class Config:
        orm_mode = True



class AllBoardsLists(SQLModel):
    boards: List[BoardLists]
    total: int

    class Config:
        orm_mode = True
