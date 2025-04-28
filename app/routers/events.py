from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, and_
from app.models import  Event, Project, User, Member, EvenMemberLink
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


def validate_assignment(session: Session, event_id: str, member_id: str):
    """
    Validates that both the event and member exist before creating a new assignment.

    Args:
        session (Session): The database session.
        event_id (str): ID of the event to validate.
        member_id (str): ID of the member to validate.

    Raises:
        HTTPException: If either the event or the member does not exist.
    """

    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if event.project.team_id != member.team_id:
        raise HTTPException(status_code=400, detail="Event and Member must belong to the same team")

    statement = select(EvenMemberLink).where(
        and_(
            EvenMemberLink.member_id == member_id,
            EvenMemberLink.event_id == event_id
        )
    )

    link = session.exec(statement).first()
    if link:
        raise HTTPException(status_code=400, detail="EventMemberLink already exists")



@router.post("/{event_id}", response_model=EvenMemberLink)
async def assign_event_to_member(event_id: str, member_id: str, session: Session = db_session):
    validate_assignment(session, event_id, member_id)
    new_link = EvenMemberLink(event_id = event_id,
                              member_id = member_id
    )
    session.add(new_link)
    session.commit()
    session.refresh(new_link)
    return new_link
