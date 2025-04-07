from datetime import datetime
from typing import Literal, Optional
from sqlmodel import SQLModel


class UserCreate(SQLModel):
    username: str
    first_name: str
    last_name: str
    email: str
    password: str
    role: Optional[Literal["admin", "member"]] = "member"




class UserRead(SQLModel):
    id: str
    username: str
    first_name: str
    last_name: str
    email: str
    created_at: datetime
    role: str
