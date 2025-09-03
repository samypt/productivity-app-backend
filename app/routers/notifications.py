from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, not_
from app.models import Notification
from app.database import get_session
from ..schemas.notification import NotificationList, NotificationRead, NotificationRespond
from ..services.auth import get_current_user
from typing import Annotated

router = APIRouter(prefix="/notifications", tags=["Notification"])
# db_session = Depends(get_session)
# user_dependency = Annotated[dict, Depends(get_current_user)]


def get_unread_notifications_count( user_id: str,
        session: Session = Depends(get_session))-> int:
    notifications_statement = select(Notification).where(
        (Notification.user_id == user_id) & not_(Notification.is_read)
    )
    notifications = session.exec(notifications_statement).all()
    return len(notifications)


@router.get("/", response_model=NotificationList)
async def get_notifications(
        current_user: Annotated[dict, Depends(get_current_user)],
        limit: int = Query(5, ge=1),
        offset: int = Query(0, ge=0),
        session: Session = Depends(get_session)
):
    user_id = current_user.get("id")
    if user_id is None:
        raise HTTPException(status_code=400, detail="Invalid user")

    notifications_statement = (select(Notification).where(
        Notification.user_id == user_id,
         Notification.is_read == False
    ).order_by(Notification.updated_at.desc(), Notification.id.asc())
                               .offset(offset)
                               .limit(limit))
    notifications = session.exec(notifications_statement).all()

    return NotificationList(
        notifications=[NotificationRead.model_validate(notification) for notification in notifications]
    )


@router.post("/{notification_id}/respond", response_model=NotificationRead)
async def notification_respond(
    current_user: Annotated[dict, Depends(get_current_user)],
    notification_id: str,
    notification: NotificationRespond,
    session: Session = Depends(get_session)
):
    user_id = current_user.get("id")

    # Fetch and validate the notification
    statement = select(Notification).where(
        (Notification.id == notification_id) & (Notification.user_id == user_id)
    )
    exist_notification: Notification = session.exec(statement).first()

    if not exist_notification:
        raise HTTPException(status_code=404, detail="Notification not found or access denied")

    exist_notification.is_read = notification.is_read
    session.add(exist_notification)
    session.commit()
    session.refresh(exist_notification)
    return exist_notification




# @router.post("/count", response_model=NotificationCount)
# async def get_unread_count(
#         current_user: Annotated[dict, Depends(get_current_user)],
#         session: Session = Depends(get_session)
# ):
#     user_id = current_user.get("id")
#     if user_id is None:
#         raise HTTPException(status_code=400, detail="Invalid user")
#
#     notifications_statement = select(Notification).where(
#         (Notification.user_id == user_id)
#     )
#     notifications = session.exec(notifications_statement).all()
#     unread_count = NotificationCount(unread_count=len(notifications))
#
#     await manager.send_to_user(user_id, unread_count.model_dump_json())
#
#     return unread_count



# @router.post("/{notification_id}/respond", response_model=NotificationRead)
# async def notification_respond(
#     current_user: Annotated[dict, Depends(get_current_user)],
#     notification_id: str,
#     notification: NotificationRespond,
#     session: Session = Depends(get_session)
# ):
#     user_id = current_user.get("id")
#
#     # Fetch and validate the notification
#     statement = select(Notification).where(
#         (Notification.id == notification_id) & (Notification.user_id == user_id)
#     )
#     exist_notification: Notification = session.exec(statement).first()
#
#     if not exist_notification:
#         raise HTTPException(status_code=404, detail="Notification not found or access denied")
#
#     if exist_notification.status in ("accepted", "declined"):
#         raise HTTPException(status_code=400, detail="Notification has already been responded to")
#
#     # Handle invitation-type notification
#     if exist_notification.object_type == "invitation":
#         invite = session.get(Invite, exist_notification.object_id)
#         if not invite:
#             raise HTTPException(status_code=404, detail="Associated invite not found")
#
#         invite.status = notification.status
#
#         if notification.status == "accepted":
#             new_member = Member(
#                 user_id=user_id,
#                 team_id=invite.team_id,
#                 role=invite.role
#             )
#             session.add(new_member)
#
#         session.add(invite)
#
#     # Update the notification status
#     exist_notification.status = notification.status
#     session.add(exist_notification)
#     session.commit()
#     session.refresh(exist_notification)
#
#     return exist_notification

    # def handle_invitation_response(invite: Invite, status: str, user_id: int, session: Session):
    #     invite.status = status
    #     if status == "accepted":
    #         new_member = Member(user_id=user_id, team_id=invite.team_id, role=invite.role)
    #         session.add(new_member)
    #     session.add(invite)

