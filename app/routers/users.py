from fastapi import APIRouter, Depends
from sqlmodel import Session
from app.models import User
from app.schemas import UserCreate, UserRead
from app.database import get_session

router = APIRouter()

@router.post("/users", response_model=UserRead)
def create_user(user: UserCreate, session: Session = Depends(get_session)):
    db_user = User(
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=user.role,
        hashed_password=user.password
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user