from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, or_
from app.models import User
from app.schemas.user import UserCreate, UserRead, UserLogin, UserUpdate, UserGet
from app.schemas.token import Token
from app.database import get_session
from app.utils.security import hash_password, verify_password
from app.services.auth import create_access_token
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


@router.post("/login",response_model=Token)
async def login_user(user: UserLogin, session: Session = Depends(get_session)):
    statement = select(User).where(User.email == user.email)
    user_to_login = session.exec(statement).first()

    if (not user_to_login or
            not verify_password(user.password, user_to_login.hashed_password)):
        raise  HTTPException(status_code=401, detail="Invalid email or password")

    access_token = create_access_token(data={"sub": str(user_to_login.id)})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/", response_model=UserRead)
async def create_user(user: UserCreate,
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


@router.put("/update/{user_id}", response_model=UserRead)
async def update_user(user_id: str, user: UserUpdate,
                      session: Session = Depends(get_session)):
    user_to_update = session.get(User, user_id)
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")
    data_to_update = user.model_dump(exclude_unset=True)
    for key, value in data_to_update.items():
        setattr(user_to_update, key, value)
    session.add(user_to_update)
    session.commit()
    session.refresh(user_to_update)
    return  user_to_update


@router.delete("/delete/{user_id}", status_code=204)
async def delete_user(user_id: str, session: Session = Depends(get_session)):
    user_to_delete = session.get(User, user_id)
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")
    session.delete(user_to_delete)
    session.commit()
    return


@router.get("/{username}", response_model=UserGet)
async def get_user(username: str, session: Session = Depends(get_session)):
    statement = select(User).where(User.username == username)
    user_to_get = session.exec(statement).first()
    if not user_to_get:
        raise HTTPException(status_code=404, detail="User not found")
    return user_to_get
