from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.models import User
from app.schemas import UserCreate, UserRead
from app.database import get_session
from app.utils.security import hash_password

router = APIRouter()

@router.post("/users", response_model=UserRead)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
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