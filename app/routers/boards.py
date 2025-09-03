from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, and_
from app.models import Project, Board, Member
from app.schemas.board import BoardRead, BoardUpdate, BoardCreate
from app.database import get_session
from ..services.auth import get_current_user
from typing import Annotated


router = APIRouter(prefix="/boards", tags=["Boards"])
db_session = Depends(get_session)
user_dependency = Annotated[dict, Depends(get_current_user)]


def validate_membership(user_id:str, project_id:str, session: Session):
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    statement = select(Member).where(and_(
        Member.user_id == user_id,
        Member.team_id == project.team_id
    ))
    membership = session.exec(statement).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied, user is not a member of the team.")
    return membership


@router.post("/create", response_model=BoardRead)
async def create_board(current_user: user_dependency,
                       board: BoardCreate, session: Session = db_session):
    validate_membership(current_user.get("id"), board.project_id, session)
    statement = select(Board).where(
        and_(
            Board.project_id == board.project_id,
            Board.name == board.name
        )
    )
    existing_board = session.exec(statement).first()
    if existing_board:
        raise HTTPException(status_code=409,
                            detail="Board with this name already exists"
                                   " in this project")

    new_board = Board(**board.model_dump())
    session.add(new_board)
    session.commit()
    session.refresh(new_board)
    return new_board


@router.get("/{board_id}", response_model=BoardRead)
async def get_board(board_id: str, session: Session = db_session):
    board_to_get = session.get(Board, board_id)
    if not board_to_get:
        raise HTTPException(status_code=404, detail="Board not found")
    return board_to_get


@router.put("/update/{board_id}", response_model=BoardRead)
async def update_board(current_user: user_dependency,
                       board_id: str, board: BoardUpdate,
                       session: Session = db_session):
    board_to_update = session.get(Board, board_id)
    if not board_to_update:
        raise HTTPException(status_code=404, detail="Board not found")
    validate_membership(current_user.get("id"), board_to_update.project_id, session)
    data_to_update = board.model_dump(exclude_unset=True)
    for key, value in data_to_update.items():
        setattr(board_to_update, key, value)
    session.add(board_to_update)
    session.commit()
    session.refresh(board_to_update)
    return board_to_update


@router.delete("/delete/{board_id}", status_code=204)
async def delete_board(current_user: user_dependency,
                       board_id: str, session: Session = db_session):
    board_to_delete = session.get(Board, board_id)
    if not board_to_delete:
        raise HTTPException(status_code=404, detail="Board not found")
    validate_membership(current_user.get("id"), board_to_delete.project_id, session)
    session.delete(board_to_delete)
    session.commit()