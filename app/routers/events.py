from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, and_, or_
from app.models import Event, Project, User, Member, EventMemberLink, Team, Notification, GoogleSyncedEvent
from app.schemas.event import EventRead, EventCreate, EventUpdate, EventList, EventFull
from app.database import get_session
from .notifications import get_unread_notifications_count
from ..schemas.member import AssignRequest
from ..schemas.user import UserPublic
from ..services.auth import get_current_user
from datetime import datetime
from ..services.manager import ws_connection_manager
from ..services.test_google_service import GoogleCalendarService
from ..utils.time import to_naive, get_time_stamp
from typing import Annotated, List


router = APIRouter(prefix="/events", tags=["Events"])
db_session = Depends(get_session)
user_dependency = Annotated[dict, Depends(get_current_user)]



def validate_member(user_id: str, project_id: str, session: Session):

    # change!!!!!


    """
    Validates that both the event and member exist before creating a new assignment.

    Args:
        session (Session): The database session.
        event_id (str): ID of the event to validate.
        member_id (str): ID of the member to validate.

    Raises:
        HTTPException: If either the event or the member does not exist.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    member_query = select(Member).where(
        Member.user_id == user_id,
        Member.team_id == project.team_id
    )
    member = session.exec(member_query).first()
    if not member:
        raise HTTPException(status_code=403, detail="You don't have access")


def validate_membership(user_id:str, event_id:str, session: Session):
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    statement = select(Member).where(and_(
        Member.user_id == user_id,
        Member.team_id == event.project.team_id
    ))
    membership = session.exec(statement).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied, user is not a member of the team.")
    return event


def create_google_event( user_id: str, event: Event, session: Session):
    user = session.get(User, user_id)

    # Optionally sync with Google Calendar if user has connected it
    if user and user.google_calendar_id:
        service = GoogleCalendarService()
        google_event_id = service.create_event(user.google_calendar_id, event)

        if google_event_id:
            google_event = GoogleSyncedEvent(
                event_id=event.id,
                user_id=user_id,
                google_event_id=google_event_id,
                google_calendar_id=user.google_calendar_id
            )
            session.add(google_event)
            session.commit()
        else:
            print(f"[Warning] Could not create Google Calendar event for user {user_id}")
    else:
        print(f"[Info] Skipping Google sync: No calendar ID for user {user_id}")


def delete_google_event(event: Event, session: Session):
    if not event.google_events:
        return

    service = GoogleCalendarService()
    failed_events = []

    for google_event in event.google_events:
        try:
            service.delete_event(google_event)
        except Exception as e:
            print(f"[Warning] Failed to delete Google event {google_event.google_event_id}: {e}")
            failed_events.append(google_event)
            continue

        session.delete(google_event)

    session.commit()

    if failed_events:
        print(f"[Info] {len(failed_events)} Google event(s) could not be deleted.")


@router.post("/create", response_model=EventRead)
async def create_event(current_user: user_dependency,
                       event: EventCreate,
                       session: Session = db_session
                       ):
    user_id = current_user.get("id")
    validate_member(user_id, event.project_id, session)

    statement = select(Project).where(Project.id == event.project_id)
    existing_project = session.exec(statement).first()
    if not existing_project:
        raise HTTPException(status_code=404, detail="Project not found")
    new_event = Event(**event.model_dump(), created_by = user_id)

    # Add and persist the new event
    session.add(new_event)
    session.commit()
    session.refresh(new_event)  # ensure relationships are available

    create_google_event(user_id, new_event, session)

    return new_event


@router.put("/update/{event_id}", response_model=EventRead)
async def update_event(current_user: user_dependency,
                       event_id: str,
                       event: EventUpdate,
                       session: Session = db_session):
    user_id = current_user.get("id")
    validate_membership(user_id, event_id, session)
    event_to_update = session.get(Event, event_id)
    if not event_to_update:
        raise HTTPException(status_code=404, detail="Event not found")
    statement = select(Project).where(Project.id == event.project_id)
    existing_project = session.exec(statement).first()
    if not existing_project:
        raise HTTPException(status_code=404, detail="Project not found")
    data_to_update = event.model_dump(exclude_unset=True)
    for key, value in data_to_update.items():
        setattr(event_to_update, key, value)
    session.add(event_to_update)
    session.commit()
    session.refresh(event_to_update)  # ensure relationships are loaded

    if event_to_update.google_events:
        service = GoogleCalendarService()
        for google_event in event_to_update.google_events:
            try:
                service.update_event(google_event, event_to_update)
            except Exception as e:
                print(f"[Warning] Failed to update Google event {google_event.google_event_id}: {e}")
    else:
        print(f"[Info] No linked Google events to update for event {event_to_update.id}")

    return event_to_update


@router.delete("/delete/{event_id}", status_code=204)
async def delete_event(current_user: user_dependency,
                       event_id: str,
                       session: Session = db_session):
    user_id = current_user.get("id")
    validate_membership(user_id, event_id, session)
    event_to_delete = session.get(Event, event_id)
    if not event_to_delete:
        raise HTTPException(status_code=404, detail="Event not found")

    delete_google_event(event_to_delete, session)

    session.delete(event_to_delete)
    session.commit()

    return


@router.get('/me', response_model=EventList)
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

    events_map: dict[str, EventFull] = {}

    # Collect events from team members
    for member in members:
        for event in member.events:
            if (
                    (start_date <= event.start_time <= end_date) or
                    (start_date <= event.end_time <= end_date) or
                    (event.start_time <= start_date and event.end_time >= end_date)
            ):
                if event.id not in events_map:
                    events_map[event.id] = EventFull.model_validate({
                        **event.model_dump(),
                        "team": event.project.team,
                        "project": event.project,
                        "members": [
                            UserPublic.model_validate({
                                **member.user.model_dump(),
                                "membership": member
                            })
                            for member in event.members
                        ]
                    })

    # Add user's personal events
    for event in user_events:
        if event.id not in events_map:
            events_map[event.id] = EventFull.model_validate({
                **event.model_dump(),
                "team": event.project.team,
                "project": event.project,
                "members": [
                    UserPublic.model_validate({
                        **member.user.model_dump(),
                        "membership": member
                    })
                    for member in event.members
                ]
            })

    # Final list
    events = list(events_map.values())

    if not events:
        return EventList(events=[])

    return EventList(events=events)


@router.get('/project/{project_id}', response_model=EventList)
async def get_events(current_user: user_dependency,
                     project_id: str,
                     start_date: datetime = Query(None, description="Start datetime in ISO format"),
                     end_date: datetime = Query(None, description="End datetime in ISO format"),
                     session: Session = Depends(get_session)):
    start_date = to_naive(start_date)
    end_date = to_naive(end_date)

    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    member_query = select(Member).where(
        Member.user_id == current_user.get("id"),
        Member.team_id == project.team_id
    )
    member = session.exec(member_query).first()
    if not member:
        raise HTTPException(status_code=403, detail="You don't have access")

        # Query events created by the user directly in the date range
    events_query = select(Event).where(
        Event.project_id == project_id,
        or_(
            and_(Event.start_time >= start_date, Event.start_time <= end_date),
            and_(Event.end_time >= start_date, Event.end_time <= end_date),
            and_(Event.start_time <= start_date, Event.end_time >= end_date),
        )
    ).order_by(Event.start_time)
    events = session.exec(events_query).all()

    if not events:
        # raise HTTPException(status_code=404, detail="User does not have any events")
        return  EventList(events=[])

    return EventList(events=[EventFull.model_validate({
                **event.model_dump(),
                "team": event.project.team,
                "project": event.project,
                "members": [
                    UserPublic.model_validate({**member.user.model_dump(), "membership": member})
                    for member in event.members
                ]
            }) for event in events
    ])


@router.get('/calendar', response_model=EventList )
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

    events_map: dict[str, EventFull] = {}

    # Collect events from memberships
    for member in members:
        for event in member.events:
            if (
                    (start_date <= event.start_time <= end_date) or
                    (start_date <= event.end_time <= end_date) or
                    (event.start_time <= start_date and event.end_time >= end_date)
            ):
                if event.id not in events_map:
                    events_map[event.id] = EventFull.model_validate({
                        **event.model_dump(),
                        # "team" : TeamRead.model_validate(**event.project.team.model_dump()),
                        # "project": ProjectRead.model_validate(**event.project.model_dump())
                        "team": event.project.team,
                        "project": event.project,
                        "members": [
                            UserPublic.model_validate({
                                **member.user.model_dump(),
                                "membership": member
                            })
                            for member in event.members
                        ]

                    })

    # Add user's personal events
    for event in user_events:
        if event.id not in events_map:
            events_map[event.id] = EventFull.model_validate({
                **event.model_dump(),
                # "team": Team.model_validate(**event.project.team.model_dump()),
                "team": event.project.team,
                "project": event.project,
                "members": [
                    UserPublic.model_validate({
                        **member.user.model_dump(),
                        "membership": member
                    })
                    for member in event.members
                ]
            })

    # Final list
    events = list(events_map.values())

    if not events:
        return EventList(events=[])

    return EventList(events=events)



# @router.post("/{event_id}", response_model=EventMemberLink)
# async def assign_event_to_member(event_id: str, member_id: str, session: Session = db_session):
#     validate_assignment(session, event_id, member_id)
#     new_link = EventMemberLink(event_id = event_id,
#                               member_id = member_id
#     )
#     session.add(new_link)
#     session.commit()
#     session.refresh(new_link)
#     return new_link

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

    statement = select(EventMemberLink).where(
        and_(
            EventMemberLink.member_id == member_id,
            EventMemberLink.event_id == event_id
        )
    )

    link = session.exec(statement).first()
    if link:
        raise HTTPException(status_code=400, detail="EventMemberLink already exists")


def validate_unassignment(session: Session, event_id: str, member_id: str):
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if event.project.team_id != member.team_id:
        raise HTTPException(status_code=400, detail="Event and Member must belong to the same team")

    statement = select(EventMemberLink).where(
        EventMemberLink.member_id == member_id,
        EventMemberLink.event_id == event_id
    )
    link = session.exec(statement).first()
    if not link:
        raise HTTPException(status_code=400, detail="Member is not assigned to this event")


def get_event_and_assignee(session: Session, event_id: str, member_id: str):
    event = session.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    assignee_statement = select(Member).where(
        Member.id == member_id,
        Member.team_id == event.project.team_id
    )
    assignee: Member = session.exec(assignee_statement).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found in the team")

    return event, assignee


def notify_if_needed(session: Session, *, event: Event, inviter: User, assignee: Member, action: str):
    if inviter.id == assignee.user_id:
        return

    action_phrases = {
        "assigned": "assigned to",
        "unassigned": "unassigned from",
    }

    phrase = action_phrases.get(action, f"{action} from")

    message = (
        f"You've been {phrase} event '{event.title}' by "
        f"{inviter.first_name} {inviter.last_name}. "
        f"For questions, contact {inviter.email}."
    )

    notification_statement = select(Notification).where(
        Notification.user_id == assignee.user_id,
        Notification.sender_id == inviter.id,
        Notification.object_type == "event",
        Notification.object_id == event.id,
        Notification.message == message
    )
    existing = session.exec(notification_statement).first()

    if not existing:
        session.add(Notification(
            user_id=assignee.user_id,
            sender_id=inviter.id,
            object_type="event",
            object_id=event.id,
            message=message
        ))

    else:
        existing.updated_at = get_time_stamp()
        session.add(existing)

    session.commit()


@router.post("/assign/{event_id}", response_model=EventMemberLink)
async def assign_event_to_member(
    current_user: user_dependency,
    event_id: str,
    body: AssignRequest,
    session: Session = db_session
):
    inviter = session.get(User, current_user.get("id"))
    member_id = body.member_id

    validate_assignment(session, event_id, member_id)

    event, assignee = get_event_and_assignee(session, event_id, member_id)

    new_link = EventMemberLink(event_id=event_id, member_id=member_id)
    session.add(new_link)

    notify_if_needed(session, event=event, inviter=inviter, assignee=assignee, action="assigned")

    session.commit()

    create_google_event(assignee.user_id, event, session)

    notifications_count = get_unread_notifications_count(assignee.user_id, session)
    await ws_connection_manager.send_to_user(
        user_id=assignee.user_id,
        message={"type": "event", "msg": "assign", "count": notifications_count}
    )

    session.refresh(new_link)

    return new_link


@router.post("/unassign/{event_id}", status_code=204)
async def unassign_event_from_member(
    current_user: user_dependency,
    event_id: str,
    body: AssignRequest,
    session: Session = db_session
):
    inviter = session.get(User, current_user.get("id"))
    member_id = body.member_id

    validate_unassignment(session, event_id, member_id)

    statement = select(EventMemberLink).where(
        EventMemberLink.member_id == member_id,
        EventMemberLink.event_id == event_id
    )
    link_to_delete = session.exec(statement).first()
    if not link_to_delete:
        raise HTTPException(status_code=404, detail="Assignment not found")

    event , assignee = get_event_and_assignee(session, event_id, member_id)

    session.delete(link_to_delete)
    notify_if_needed(session, event=event, inviter=inviter, assignee=assignee, action="unassigned")

    session.commit()

    delete_google_event(event, session)

    notifications_count = get_unread_notifications_count(assignee.user_id, session)
    await ws_connection_manager.send_to_user(
        user_id=assignee.user_id,
        message={"type": "event", "msg": "unassign", "count": notifications_count}
    )

    return
