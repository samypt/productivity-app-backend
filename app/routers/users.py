from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, or_
from app.models import User
from app.schemas import UserCreate, UserRead, UserLogin
from app.database import get_session
from app.utils.security import hash_password, verify_password
from pydantic import EmailStr

router = APIRouter(prefix="/users", tags=["Users"])


def validate_user(session: Session, email: EmailStr, username: str):
    """
    Validates that a new user's email and username are unique.

    Args:
        session: SQLModel database session
        email: Email address to check
        username: Username to check

    Raises:
        HTTPException: If email or username is already in use
    """
    # Check both email and username in a single database query
    statement = select(User).where(
        or_(
            User.email == email,
            User.username == username
        )
    )
    existing_user = session.exec(statement).first()

    # Provide specific error message based on which field caused the conflict
    if existing_user:
        if existing_user.email == email:
            raise HTTPException(status_code=400, detail="Email already registered")
        else:
            raise HTTPException(status_code=400, detail="Username already taken")


@router.post("/login")
async def login_user(user: UserLogin, session: Session = Depends(get_session)):
    statement = select(User).where(User.email == user.email)
    user_to_login = session.exec(statement).first()

    if (not user_to_login or
            not verify_password(user.password, user_to_login.hashed_password)):
        raise  HTTPException(status_code=401, detail="Invalid email or password")

    return {"message": "Login successful"}


@router.post("/", response_model=UserRead)
async def create_user(user: UserCreate, session: Session = Depends(get_session)):
    validate_user(session, user.email, user.username)

    hashed_password = hash_password(user.password)

    new_user = User(
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=user.role,
        hashed_password=hashed_password
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user
