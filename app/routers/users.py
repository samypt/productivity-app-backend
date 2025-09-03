from app.schemas.user import UserRead, UserUpdate, UserPublic
from app.models import Task
from app.database import get_session
from app.schemas.event import EventList, EventRead
from app.schemas.task import TaskList, TaskRead
from app.schemas.teams import TeamList, TeamFullInfo
from app.schemas.member import MemberRead
from app.models import Member, User, Event
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlmodel import Session, select, or_, and_
from typing import Annotated, List
from ..services.auth import get_current_user
from datetime import datetime
from ..utils.time import to_naive
import shutil
import os




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


@router.get("/me", response_model=UserRead)
async def get_user(current_user: user_dependency, session: Session = Depends(get_session)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication Failed")
    statement = select(User).where(User.username == current_user.get('username'))
    user_to_get = session.exec(statement).first()
    if not user_to_get:
        raise HTTPException(status_code=404, detail="User not found")
    return UserRead.model_validate(user_to_get)


# @router.get('/me/tasks', response_model=TaskList)
# async def get_user_tasks(
#         current_user: user_dependency,
#         limit: int = Query(5, ge=1),
#         offset: int = Query(0, ge=0),
#         sort_by: str = Query("updated_at"),
#         sort_order: str = Query("desc"),
#         session: Session = Depends(get_session)):
#     members_query = select(Member).where(Member.user_id == current_user.get("id"))
#     members = session.exec(members_query).all()
#
#     if not members:
#         raise HTTPException(status_code=404, detail="The user isn't a member of any team")
#
#     tasks = []
#     for member in members:
#         tasks.extend(member.tasks)
#
#     if not tasks:
#         raise HTTPException(status_code=404, detail="No Tasks found for user")
#
#     return TaskList(tasks=[TaskRead.model_validate(task) for task in tasks])



@router.get("/me/tasks", response_model=TaskList)
async def get_user_tasks(
    current_user: user_dependency,
    limit: int = Query(5, ge=1),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("updated_at"),
    sort_order: str = Query("desc"),
    session: Session = Depends(get_session),
):
    # Get all team memberships for this user
    members_query = select(Member).where(Member.user_id == current_user.get("id"))
    members = session.exec(members_query).all()

    if not members:
        raise HTTPException(status_code=404, detail="The user isn't a member of any team")

    # Collect all tasks from the member objects
    tasks = []
    for member in members:
        tasks.extend(member.tasks)

    if not tasks:
        raise HTTPException(status_code=404, detail="No Tasks found for user")

    # Sorting
    reverse = sort_order.lower() == "desc"
    if hasattr(Task, sort_by):
        tasks.sort(key=lambda t: getattr(t, sort_by), reverse=reverse)
    else:
        # fallback
        tasks.sort(key=lambda t: t.updated_at, reverse=True)

    # Pagination
    tasks = tasks[offset: offset + limit]

    return TaskList(tasks=[TaskRead.model_validate(task) for task in tasks])



@router.get('/me/teams', response_model=TeamList)
async def get_user_teams(
        current_user: user_dependency,
        session: Session = Depends(get_session)):
    members_query = select(Member).where(Member.user_id == current_user.get("id"))
    members = session.exec(members_query).all()

    if not members:
        raise HTTPException(status_code=404, detail="The user isn't a member of any team")

    teams = []
    for member in members:
        team_data = TeamFullInfo(
            id = member.team.id,
            name = member.team.name,
            description = member.team.description,
            created_at = member.team.created_at,
            membership = MemberRead.model_validate(member),
            members = [UserPublic.model_validate({**member.user.model_dump(), "membership": member})
                       for member in member.team.members]
        )
        teams.append(team_data)


    if not teams:
        raise HTTPException(status_code=404, detail="User does not belong to any team")

    return TeamList(teams=[TeamFullInfo.model_validate(team) for team in teams])






@router.get('/me/events', response_model=EventList)
async def get_user_events(current_user: user_dependency,
                          start_date: datetime = Query(None, description="Start datetime in ISO format"),
                          end_date: datetime = Query(None, description="End datetime in ISO format"),
                          session: Session = Depends(get_session)):
    start_date = to_naive(start_date)
    end_date = to_naive(end_date)

    members_query = select(Member).where(Member.user_id == current_user.get("id"))
    members = session.exec(members_query).all()

    # Query events created by the user directly in the date range
    events_query = select(Event).where(
        Event.created_by == current_user.get("id"),
        or_(
            and_(Event.start_time >= start_date, Event.start_time <= end_date),
            and_(Event.end_time >= start_date, Event.end_time <= end_date),
            and_(Event.start_time <= start_date, Event.end_time >= end_date),
        )
    )
    user_events = session.exec(events_query).all()

    # Collect all matching events
    events: List[Event] = []

    for member in members:
        events.extend([
            event for event in member.events
            if (
                    (start_date <= event.start_time <= end_date) or
                    (start_date <= event.end_time <= end_date) or
                    (event.start_time <= start_date and event.end_time >= end_date)
            )
        ])

    events.extend(user_events)

    if not events:
        # raise HTTPException(status_code=404, detail="User does not have any events")
        return  EventList(events=[])

    return EventList(events=[EventRead.model_validate(event) for event in events])



UPLOAD_DIR = "uploads/avatars"

@router.post("/upload-avatar")
async def upload_avatar(
        current_user: user_dependency,
        file: UploadFile = File(...),
        session: Session = Depends(get_session)
):
    user_id = current_user.get("id")
    user = session.get(User, user_id)

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp"):
        raise HTTPException(status_code=400, detail="Unsupported file type")

    # Delete previous avatar with any supported extension
    for old_ext in (".jpg", ".jpeg", ".png", ".webp"):
        old_path = os.path.join(UPLOAD_DIR, f"{user_id}{old_ext}")
        if os.path.exists(old_path):
            os.remove(old_path)

    print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
    print(os.path.splitext(file.filename))
    print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
    print(os.path.splitext(file.filename)[0].lower())
    print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
    print(os.path.splitext(file.filename)[1].lower())
    print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
    print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    filename = f"{user_id}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    avatar_url = f"/static/avatars/{filename}"
    user.avatar_url = avatar_url
    session.add(user)
    session.commit()

    return {"avatar_url": avatar_url}



# @router.get("/users/avatar/{user_id}")
# async def get_avatar(user_id: str, current_user: user_dependency):
#     if current_user["id"] != user_id:
#         raise HTTPException(status_code=403)
#
#     # Serve the image manually:
#     filepath = f"uploads/avatars/{user_id}.jpg"
#     if not os.path.exists(filepath):
#         raise HTTPException(status_code=404)
#     return FileResponse(filepath)