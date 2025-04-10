from datetime import datetime
from typing import Literal, Optional
from sqlmodel import SQLModel
from pydantic import EmailStr, model_validator
from uuid import UUID


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
    role: str




class UserLogin(SQLModel):
    username: Optional[str]
    email: Optional[EmailStr]
    password: str

    @model_validator(mode='after')
    def check_username_or_email(self):
        if not self.username and not self.email:
            raise ValueError("Either username or email must be provided.")
        return self




class UserUpdate(SQLModel):
    first_name: Optional[str]
    last_name: Optional[str]
    role: Optional[Literal["admin", "member"]]




class UserGet(SQLModel):
    first_name: str
    last_name: str
    role: Optional[Literal["admin", "member"]]
