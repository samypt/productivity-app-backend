from datetime import datetime
from typing import Literal, Optional, List
from sqlmodel import SQLModel
from pydantic import EmailStr, model_validator
from uuid import UUID
from .member import MemberRead


class UserCreate(SQLModel):
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    role: Optional[Literal["admin", "member"]] = "member"




class UserRead(SQLModel):
    id: UUID
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    created_at: datetime
    updated_at: Optional[datetime] = None
    role: str

    class Config:
        orm_mode = True




class UserLogin(SQLModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: str

    @model_validator(mode='after')
    def check_username_or_email(self):
        if not self.username and not self.email:
            raise ValueError("Either username or email must be provided.")
        return self




class UserUpdate(SQLModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[Literal["admin", "member"]] = None




class UserGet(SQLModel):
    first_name: str
    last_name: str
    role: Optional[Literal["admin", "member"]]




class UserPublic(SQLModel):
    id: UUID
    username: str
    first_name: str
    last_name: str
    email: EmailStr
    avatar_url: str
    membership: MemberRead
    avatar_url: Optional[str] = None
    updated_at: Optional[datetime] = None


    class Config:
        orm_mode = True




class UserList(SQLModel):
    users: List[UserPublic]

    class Config:
        orm_mode = True