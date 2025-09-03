from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, and_
from app.models import Team, Member, User
from app.schemas.member import MemberCreate, MemberRead, MemberUpdate
from app.database import get_session


router = APIRouter(prefix="/members", tags=["Members"])
db_session = Depends(get_session)


def validate_member(user_id: str, team_id: str, session: Session):
    """
    Validates that a new member's user_id and team_id exist.

    Args:
        session: SQLModel database session
        user_id: User ID to check
        team_id: Team ID to check

    Raises:
        HTTPException: If user_id or team_id not exist
    """
    user = session.get(User, user_id)
    team = session.get(Team, team_id)
    statement = select(Member).where(
        and_(
            Member.user_id == user_id,
            Member.team_id == team_id
        )
    )
    member = session.exec(statement).first()

    # Provide specific error message based on which field caused the conflict
    if not user:
        raise HTTPException(status_code=400, detail="User doesn't exist")

    if not team:
        raise HTTPException(status_code=400, detail="Team doesn't exist")

    if member:
        raise HTTPException(status_code=400, detail="User is already a member of the team")


@router.post("/", response_model=MemberRead)
async def create_member(member: MemberCreate, session: Session = db_session):
    validate_member(member.user_id, member.team_id, session)
    new_member = Member(**member.model_dump())
    session.add(new_member)
    session.commit()
    session.refresh(new_member)
    return new_member


@router.get("/{member_id}", response_model=MemberRead)
async def get_member(member_id, session: Session = db_session):
    member_to_get = session.get(Member, member_id)
    if not member_to_get:
        raise HTTPException(status_code=404, detail="Member not found")
    return member_to_get


@router.put("/update/{member_id}", response_model=MemberRead)
async def update_member(member_id: str, member: MemberUpdate, session: Session = db_session):
    member_to_update = session.get(Member, member_id)
    if not member_to_update:
        raise HTTPException(status_code=404, detail="Member not found")
    data_to_update = member.model_dump(exclude_unset=True)
    for key, value in data_to_update.items():
        setattr(member_to_update, key, value)
    session.add(member_to_update)
    session.commit()
    session.refresh(member_to_update)
    return member_to_update


@router.delete("/delete/{member_id}", status_code=204)
async def delete_member(member_id: str, session: Session = db_session):
    member_to_delete = session.get(Member, member_id)
    if not member_to_delete:
        raise HTTPException(status_code=404, detail="Member not found")
    session.delete(member_to_delete)
    session.commit()
    return
