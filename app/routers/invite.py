from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, and_
from app.models import Member, Invite, User, Notification, Team
from ..schemas.invite import InviteRead, InviteCreate, InviteRespond
from app.database import get_session
from ..services.auth import get_current_user
from typing import Annotated
from ..utils.email_service import send_invite_email
from  ..config import ROLE_HIERARCHY
from ..services.manager import ws_connection_manager
from .notifications import get_unread_notifications_count



router = APIRouter(prefix="/invites", tags=["Invite"])
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


def check_duplicate_invite(invite: InviteCreate, session: Session):
    invite_statement = select(Invite).where(
        and_(Invite.email == invite.email, Invite.team_id == invite.team_id)
    )
    existing_invite = session.exec(invite_statement).first()
    if existing_invite:
        raise HTTPException(status_code=409, detail="The person is already invited to the team")


def check_existing_member(invite: InviteCreate, session: Session):
    team_member_statement = (
        select(Member)
        .join(User)
        .where(and_(
            Member.team_id == invite.team_id,
            User.email == invite.email
        ))
    )

    is_already_member = session.exec(team_member_statement).first()

    if is_already_member:
        raise HTTPException(status_code=400, detail="The person is already part of the team")


def check_invitation_permissions(membership:Member, invite: InviteCreate):
    # Viewer cannot invite anyone
    if membership.role == "viewer":
        raise HTTPException(status_code=409, detail="You are not allowed to invite")

    # Editors can’t invite someone with higher or equal role
    if ROLE_HIERARCHY[membership.role] <= ROLE_HIERARCHY[invite.role]:
        raise HTTPException(
            status_code=409,
            detail="You are not allowed to invite persons with this role"
        )


@router.post("/", response_model=InviteRead)
async def invite_by_email(current_user: user_dependency, invite: InviteCreate,
                          session: Session = db_session):
    """
    Invite a user by email to a team. If the user does not exist,
    an invitation email will be sent.
    """
    current_user_id = current_user.get("id")
    try:
        membership = validate_membership(current_user_id, invite.team_id, session)

        # Check if the member is allowed to invite
        check_invitation_permissions(membership, invite)

        # Check existing invite
        check_duplicate_invite(invite, session)

        # Check if the Member is already part of the team
        check_existing_member(invite, session)

        # Add new invite
        new_invite = Invite(**invite.model_dump(), invited_by=current_user_id)
        session.add(new_invite)
        session.flush()  # Ensure ID is available

        user = session.exec(select(User).where(User.email == invite.email)).first()
        if not user:
            send_invite_email(
                new_invite.email,
                f"http://localhost:5173/singup/{new_invite.token}"
            )
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            print("EMAIL SENT")
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        else:
            team = session.get(Team, new_invite.team_id)
            inviter = session.get(User, new_invite.invited_by)

            new_notification = Notification(
                user_id=user.id,
                sender_id=inviter.id,
                object_type="invitation",
                object_id=new_invite.id,
                message=(
                    f"You have an invite to {team.name} from "
                    f"{inviter.first_name} {inviter.last_name}. "
                    f"For questions, contact {inviter.email}."
                )
            )
            session.add(new_notification)
            notifications_count = get_unread_notifications_count(user.id, session)
            await ws_connection_manager.send_to_user(
                user_id=user.id,
                message={"type": "notifications", "count": notifications_count}
            )
        session.commit()
        session.refresh(new_invite)
        return new_invite

    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")



@router.post("/{invite_id}/respond", response_model=InviteRead)
async def notification_respond(
    current_user: Annotated[dict, Depends(get_current_user)],
    invite_id: str,
    respond: InviteRespond,
    session: Session = Depends(get_session)
):
    user_id = current_user.get("id")
    user_email = current_user.get("email")

    # 1. Verify the user has a notification for the invite
    notification_statement = select(Notification).where(
        (Notification.object_id == invite_id) & (Notification.user_id == user_id)
    )
    notification = session.exec(notification_statement).first()

    if not notification:
        raise HTTPException(status_code=400, detail="You're not allowed to accept invitation")

    # 2. Fetch and validate the invitation
    invite = session.get(Invite, invite_id)

    if not invite or invite.email != user_email:
        raise HTTPException(status_code=404, detail="Invitation not found or access denied")

    if invite.status in ("accepted", "declined"):
        raise HTTPException(status_code=400, detail="Invitation has already been responded to")

    # 3. Update the invite status
    invite.status = respond.status

    # 4. If accepted, add the user to the team as a member
    if respond.status == "accepted":
        new_member = Member(
            user_id=user_id,
            team_id=invite.team_id,
            role=invite.role
        )
        session.add(new_member)

    session.add(invite)

    # 5. Update the notification to reflect the invite status
    notification.is_read = True
    session.add(notification)

    # 6. Commit all changes
    session.commit()
    session.refresh(invite)

    return invite