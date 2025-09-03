from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, and_, func
from app.models import Project, Team, Member, Board
from app.schemas.project import ProjectRead, ProjectUpdate, ProjectCreate
from app.database import get_session
from ..services.auth import get_current_user
from typing import Annotated
from app.schemas.board import BoardLists, AllBoardsLists
from ..schemas.board_list import BoardListRead


router = APIRouter(prefix="/project", tags=["Projects"])
db_session = Depends(get_session)
user_dependency = Annotated[dict, Depends(get_current_user)]


def validate_membership(user_id:str, team_id:str, session: Session):
    statement = select(Member).where(and_(
        Member.user_id == user_id,
        Member.team_id == team_id
    ))
    membership = session.exec(statement).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied, user is not a member of the team.")
    return membership


def validate_member(user_id:str, project_id:str, session: Session):
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


@router.post("/create", response_model=ProjectRead)
async def create_project(current_user: user_dependency,
                         project: ProjectCreate, session: Session = db_session):
    validate_membership(current_user.get("id"), project.team_id, session)
    statement = select(Project).where(
        and_(
            Project.name == project.name,
            Project.team_id == project.team_id
        )
    )
    existing_project = session.exec(statement).first()
    if existing_project:
        raise HTTPException(status_code=409,
                            detail="Project with this name already exists"
                                   " in this team")
    existing_team = session.get(Team, project.team_id)
    if not existing_team:
        raise HTTPException(status_code=404, detail="Project not found")
    new_project = Project(**project.model_dump())
    session.add(new_project)
    session.commit()
    session.refresh(new_project)
    return new_project


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(current_user: user_dependency, project_id: str, session: Session = db_session):
    validate_member(current_user.get("id"), project_id, session)
    project_to_get = session.get(Project, project_id)
    if not project_to_get:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_to_get


@router.delete("/delete/{project_id}", status_code=204)
async def delete_project(current_user: user_dependency, project_id, session: Session = db_session):
    validate_member(current_user.get("id"), project_id, session)
    project_to_delete = session.get(Project, project_id)
    if not project_to_delete:
        raise HTTPException(status_code=404, detail="Project not found")
    session.delete(project_to_delete)
    session.commit()
    return


@router.put("/update/{project_id}", response_model=ProjectRead)
async def update_project(current_user: user_dependency, project_id: str, project: ProjectUpdate,
                         session: Session = db_session):
    validate_member(current_user.get("id"), project_id, session)
    project_to_update = session.get(Project, project_id)
    if not project_to_update:
        raise HTTPException(status_code=404, detail="Project not found")
    data_to_update = project.model_dump()
    for key, value in data_to_update.items():
        setattr(project_to_update, key, value)
    session.add(project_to_update)
    session.commit()
    session.refresh(project_to_update)
    return project_to_update


@router.get("/{project_id}/boards", response_model=AllBoardsLists)
async def get_full_project( current_user: user_dependency,
                            project_id: str,
                            limit: int = Query(5, ge=1),
                            offset: int = Query(0, ge=0),
                            session: Session = db_session):
    validate_member(current_user.get("id"), project_id, session)
    total = session.exec(
        select(func.count()).select_from(Board).where(Board.project_id == project_id)
    ).one()
    boards_query = select(Board).where(Board.project_id == project_id).offset(offset).limit(limit)
    boards = session.exec(boards_query).all()
    board_lists = []
    for board in boards:
        board_data = BoardLists(
            **board.model_dump(),
            lists = [BoardListRead.model_validate(list_in_board) for list_in_board in board.lists]
        )
        board_lists.append(board_data)

    return AllBoardsLists(boards=[BoardLists.model_validate(board) for board in board_lists], total=total)