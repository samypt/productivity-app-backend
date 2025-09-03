from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.database import get_session
from ..services.auth import get_current_user
from ..models import User, Member, Event
from typing import Annotated
from pydantic import BaseModel
from ..services.test_google_service import GoogleCalendarService
import base64
from urllib.parse import quote

def base64_encode_email(email: str) -> str:
    # Encode email as bytes, then base64 encode, then decode to ascii string (no newlines)
    encoded_bytes = base64.urlsafe_b64encode(email.encode("utf-8"))
    return encoded_bytes.decode("ascii").rstrip("=")  # remove trailing '=' padding for URL compactness



router = APIRouter(prefix="/google", tags=["Google Calendar"])
db_session = Depends(get_session)
user_dependency = Annotated[dict, Depends(get_current_user)]

class GoogleSyncRequest(BaseModel):
    accessToken: str



@router.post("/sync")
async def sync_google_calendar(
    current_user: user_dependency,
    data: GoogleSyncRequest,
    session: Session = db_session,
):
    access_token = data.accessToken
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token missing")

    user_id = current_user.get("id")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.google_access_token = access_token
    service = GoogleCalendarService()
    email = service.get_email_from_access_token(access_token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired access token")

    if not user.google_calendar_id:
        summary = f"Personal Teamly Calendar for {user.first_name} {user.last_name}"
        calendar_data = service.create_calendar(summary)
        if not calendar_data or not calendar_data["id"]:
            raise HTTPException(status_code=500, detail="Failed to create Google Calendar")

        calendar_id = calendar_data["id"]
        calendar_link = calendar_data["htmlLink"]

        user.google_calendar_id = calendar_id
        user.google_calendar_html_link = calendar_link

        session.add(user)
        session.commit()
        session.refresh(user)


    # get all the events
    members_query = select(Member).where(Member.user_id == user_id)
    members = session.exec(members_query).all()
    events_query = select(Event).where(Event.created_by == current_user.get("id"))
    user_events = session.exec(events_query).all()

    events_map: dict[str, Event] = {}

    # Collect events from memberships
    for member in members:
        for event in member.events:
            if event.id not in events_map:
                events_map[event.id] = event

    # Add user's personal events

    for event in user_events:
        if event.id not in events_map:
            events_map[event.id] = event

    events = list(events_map.values())

    service.sync_events_to_google_calendar(user_id, user.google_calendar_id, events, session)
    service.share_calendar_to_user(email, user.google_calendar_id)

    # Build subscribe URL with ctok = user email
    encoded_email = base64_encode_email(email)

    subscribe_url = (
        f"https://calendar.google.com/calendar/r?"
        f"cid={quote(user.google_calendar_id)}&"
        f"ctok={encoded_email}&"
        f"es=4"
    )

    return {
        "message": "Google Calendar connected!",
        "calendarId": user.google_calendar_id,
        "calendarHtmlLink": user.google_calendar_html_link,
        "subscribeUrl": subscribe_url,
        "userEmail": email,
    }





@router.post("/delete_calendar")
async def sync_google_calendar(
    current_user: user_dependency,
    data: GoogleSyncRequest,
    session: Session = db_session,
):
    access_token = data.accessToken
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token missing")

    user_id = current_user.get("id")
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    service = GoogleCalendarService()


    service.delete_calendar(user.google_calendar_id)
    user.google_calendar_id = None

    session.add(user)
    session.commit()
    session.refresh(user)



    return {
        "message": "Google Calendar connected!",
    }



# @router.put("/event/{event_id}")
# def update_event(
#     event_id: str,
#     updated_event_data: EventUpdateSchema,
#     current_user: User = Depends(get_current_user),
#     session: Session = Depends(get_session),
# ):
#     event = session.get(Event, event_id)
#     if not event:
#         raise HTTPException(status_code=404, detail="Event not found")
#
#     # Update event fields...
#     for key, value in updated_event_data.dict(exclude_unset=True).items():
#         setattr(event, key, value)
#     session.commit()
#
#     access_token = ensure_valid_access_token(current_user, session)
#     if not access_token:
#         raise HTTPException(status_code=401, detail="Could not refresh token")
#
#     if event.google_event_id:
#         update_google_event(access_token, current_user.google_calendar_id, event.google_event_id, event)
#
#     return {"status": "updated"}


# @router.put("/event/{event_id}")
# def update_event(event_id: str, update_data: EventUpdateSchema, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
#     event = session.get(Event, event_id)
#     if not event:
#         raise HTTPException(status_code=404, detail="Event not found")
#
#     for key, value in update_data.dict(exclude_unset=True).items():
#         setattr(event, key, value)
#     session.commit()
#
#     if event.google_event_id:
#         calendar = GoogleCalendarService(user, session)
#         calendar.update_event(event.google_event_id, event)
#
#     return {"status": "updated"}