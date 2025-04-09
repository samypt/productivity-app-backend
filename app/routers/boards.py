from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, and_
from app.models import Project, Board
from app.schemas.board import BoardRead, BoardUpdate, BoardCreate
from app.database import get_session


router = APIRouter(prefix="/boards", tags=["Boards"])
db_session = Depends(get_session)


@router.post("/", response_model=BoardRead)
async def create_board(board: BoardCreate, session: Session = db_session):
    project = session.get(Project, board.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
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
async def update_board(board_id: str, board: BoardUpdate,
                       session: Session = db_session):
    board_to_update = session.get(Board, board_id)
    if not board_to_update:
        raise HTTPException(status_code=404, detail="Board not found")
    data_to_update = board.model_dump(exclude_unset=True)
    for key, value in data_to_update.items():
        setattr(board_to_update, key, value)
    session.add(board_to_update)
    session.commit()
    session.refresh(board_to_update)
    return board_to_update


@router.delete("/delete/{board_id}", status_code=204)
async def delete_board(board_id: str, session: Session = db_session):
    board_to_delete = session.get(Board, board_id)
    if not board_to_delete:
        raise HTTPException(status_code=404, detail="Board not found")
    session.delete(board_to_delete)
    session.commit()