from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, and_
from app.models import  Board, BoardList, Member
from app.schemas.board_list import BoardListCreate, BoardListUpdate, BoardListRead
from app.database import get_session
from ..services.auth import get_current_user
from typing import Annotated

router = APIRouter(prefix="/lists", tags=["Lists"])
db_session = Depends(get_session)
user_dependency = Annotated[dict, Depends(get_current_user)]


def validate_membership(user_id:str, board_id:str, session: Session):
    board = session.get(Board, board_id)
    if not board:
        raise HTTPException(status_code=404, detail="Board not found")
    statement = select(Member).where(and_(
        Member.user_id == user_id,
        Member.team_id == board.project.team_id
    ))
    membership = session.exec(statement).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied, user is not a member of the team.")
    return membership


def validate_member(user_id:str, list_id:str, session: Session):
    board_list = session.get(BoardList, list_id)
    if not board_list:
        raise HTTPException(status_code=404, detail="BoardList not found")
    statement = select(Member).where(and_(
        Member.user_id == user_id,
        Member.team_id == board_list.board.project.team_id
    ))
    membership = session.exec(statement).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied, user is not a member of the team.")
    return board_list


@router.post("/create", response_model=BoardListRead)
async def create_list(current_user: user_dependency,
                       board_list: BoardListCreate, session: Session = db_session):
    validate_membership(current_user.get("id"), board_list.board_id, session)
    statement = select(BoardList).where(
        and_(
            BoardList.board_id == board_list.board_id,
            BoardList.name == board_list.name
        )
    )
    existing_board_list = session.exec(statement).first()
    if existing_board_list:
        raise HTTPException(status_code=409,
                            detail="Board with this name already exists"
                                   " in this project")
    new_board_list = BoardList(**board_list.model_dump())
    session.add(new_board_list)
    session.commit()
    session.refresh(new_board_list)
    return new_board_list


@router.get("/{board_list_id}", response_model=BoardListRead)
async def get_board(board_list_id: str, session: Session = db_session):
    board_to_get = session.get(BoardList, board_list_id)
    if not board_to_get:
        raise HTTPException(status_code=404, detail="BoardList not found")
    return board_to_get


@router.put("/update/{board_list_id}", response_model=BoardListRead)
async def update_board(current_user: user_dependency,
                       board_list_id: str, board_list: BoardListUpdate,
                       session: Session = db_session):
    validate_member(current_user.get("id"), board_list_id, session)
    board_list_to_update = session.get(BoardList, board_list_id)
    if not board_list_to_update:
        raise HTTPException(status_code=404, detail="BoardList not found")
    data_to_update = board_list.model_dump(exclude_unset=True)
    for key, value in data_to_update.items():
        setattr(board_list_to_update, key, value)
    session.add(board_list_to_update)
    session.commit()
    session.refresh(board_list_to_update)
    return board_list_to_update


@router.delete("/delete/{board_list_id}", status_code=204)
async def delete_board(current_user: user_dependency,
                       board_list_id: str, session: Session = db_session):
    board_list_to_delete = validate_member(current_user.get("id"),
                                           board_list_id, session)
    session.delete(board_list_to_delete)
    session.commit()
    return