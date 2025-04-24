from __future__ import annotations
from app.database import get_session
from app.models import User
from app.schemas.token import Token
from app.schemas.user import UserCreate, UserRead
from app.services.auth import create_access_token
from app.utils.security import hash_password, verify_password
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import EmailStr
from sqlmodel import Session, select, or_
from starlette import status
from typing import Annotated


router = APIRouter(prefix="", tags=["Authenticator"])


def authenticate_user(identifier: str, password: str, session) -> User | None:
    # Try username first
    statement = select(User).where(User.username == identifier)
    user = session.exec(statement).first()
    if user and verify_password(password, user.hashed_password):
        return user

    # Try email only if username fails
    statement = select(User).where(User.email == identifier)
    user = session.exec(statement).first()
    if user and verify_password(password, user.hashed_password):
        return user

    return None


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


@router.post("/", response_model=UserRead)
async def signup(user: UserCreate,
                      session: Session = Depends(get_session)):
    validate_user(session, user.email, user.username)

    hashed_password = hash_password(user.password)

    new_user = User(
        **user.model_dump(exclude={"password"}),
        hashed_password=hashed_password
    )

    session.add(new_user)
    session.commit()
    session.refresh(new_user)
    return new_user


@router.post("/login",response_model=Token)
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[Session, Depends(get_session)]  # example session dependency
):
    user = authenticate_user(form_data.username, form_data.password, session)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Could not validate user")

    access_token = create_access_token(data={"sub": str(user.username),
                                             "id": str(user.id)
                                             },
                                       expires_delta=timedelta(minutes=20))
    return {"access_token": access_token, "token_type": "bearer"}

