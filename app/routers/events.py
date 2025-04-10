from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.models import  Event, Project, User
from app.schemas.event import EventRead, EventCreate, EventUpdate
from app.database import get_session


router = APIRouter(prefix="/events", tags=["Events"])
db_session = Depends(get_session)


@router.post("/", response_model=EventRead)
async def create_event(event: EventCreate, session: Session = db_session):
    statement = select(User).where(User.id == event.created_by)
    existing_user = session.exec(statement).first()
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    statement = select(Project).where(Project.id == event.project_id)
    existing_project = session.exec(statement).first()
    if not existing_project:
        raise HTTPException(status_code=404, detail="Project not found")
    new_event = Event(**event.model_dump())
    session.add(new_event)
    session.commit()
    session.refresh(new_event)
    return new_event


@router.get("/{event_id}", response_model=EventRead)
async def get_event(event_id: str, session: Session = db_session):
    event_to_get = session.get(Event, event_id)
    if not event_to_get:
        raise HTTPException(status_code=404, detail="Event not found")
    return event_to_get


@router.put("/{event_id}", response_model=EventRead)
async def update_event(event_id: str, event: EventUpdate, session: Session = db_session):
    event_to_update = session.get(Event, event_id)
    if not event_to_update:
        raise HTTPException(status_code=404, detail="Event not found")
    data_to_update = event.model_dump(exclude_unset=True)
    for key, value in data_to_update.items():
        setattr(event_to_update, key, value)
    session.add(event_to_update)
    session.commit()
    session.refresh(event_to_update)
    return event_to_update


@router.delete("/{event_id}", status_code=204)
async def delete_event(event_id: str, session: Session = db_session):
    event_to_delete = session.get(Event, event_id)
    if not event_to_delete:
        raise HTTPException(status_code=404, detail="Event not found")
    session.delete(event_to_delete)
    session.commit()
    return
