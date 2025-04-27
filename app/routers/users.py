from app.schemas.user import UserRead, UserUpdate, UserGet
from app.database import get_session
from app.schemas.event import EventList, EventRead
from app.schemas.task import TaskList, TaskRead
from app.schemas.teams import TeamList, TeamRead
from app.models import Member, User
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Annotated
from ..services.auth import get_current_user


router = APIRouter(prefix="/users", tags=["Users"])
user_dependency = Annotated[dict, Depends(get_current_user)]


@router.put("/update", response_model=UserRead)
async def update_user(current_user: user_dependency, user: UserUpdate,
                      session: Session = Depends(get_session)):
    user_to_update = session.get(User, current_user.get('id'))
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")
    data_to_update = user.model_dump(exclude_unset=True)
    for key, value in data_to_update.items():
        setattr(user_to_update, key, value)
    session.add(user_to_update)
    session.commit()
    session.refresh(user_to_update)
    return  user_to_update


@router.delete("/delete", status_code=204)
async def delete_user(current_user: user_dependency, session: Session = Depends(get_session)):
    user_to_delete = session.get(User, current_user.get('id'))
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")
    session.delete(user_to_delete)
    session.commit()
    return


@router.get("/me", response_model=UserGet)
async def get_user(current_user: user_dependency, session: Session = Depends(get_session)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication Failed")
    statement = select(User).where(User.username == current_user.get('username'))
    user_to_get = session.exec(statement).first()
    if not user_to_get:
        raise HTTPException(status_code=404, detail="User not found")
    return user_to_get


@router.get('/me/tasks', response_model=TaskList)
async def get_user_tasks(current_user: user_dependency, session: Session = Depends(get_session)):
    members_query = select(Member).where(Member.user_id == current_user.get("id"))
    members = session.exec(members_query).all()

    if not members:
        raise HTTPException(status_code=404, detail="The user isn't a member of any team")

    tasks = []
    for member in members:
        tasks.extend(member.tasks)

    if not tasks:
        raise HTTPException(status_code=404, detail="No Tasks found for user")

    return TaskList(tasks=[TaskRead.model_validate(task) for task in tasks])


@router.get('/me/teams', response_model=TeamList)
async def get_user_teams(current_user: user_dependency, session: Session = Depends(get_session)):
    members_query = select(Member).where(Member.user_id == current_user.get("id"))
    members = session.exec(members_query).all()

    if not members:
        raise HTTPException(status_code=404, detail="The user isn't a member of any team")

    teams = []
    for member in members:
        teams.append(member.team)

    if not teams:
        raise HTTPException(status_code=404, detail="User does not belong to any team")

    return TeamList(teams=[TeamRead.model_validate(team) for team in teams])