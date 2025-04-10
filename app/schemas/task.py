from datetime import datetime
from typing import Optional, Literal
from sqlmodel import SQLModel
from uuid import UUID
from pydantic import field_validator


class TaskCreate(SQLModel):
    title: str
    description: Optional[str]
    list_id: str
    status: Optional[Literal["todo", "in_progress", "done"]] = "todo"
    priority: int
    due_date: datetime

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError('Priority must be between 1 and 5')
        return v




class TaskRead(TaskCreate):
    id: UUID
    created_at: Optional[datetime]

    class Config:
        orm_mode = True




class TaskUpdate(SQLModel):
    title: Optional[str]
    description: Optional[str]
    list_id: Optional[str]
    status: Optional[Literal["todo", "in_progress", "done"]] = "todo"
    priority: Optional[int]
    due_date: Optional[datetime]

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: int) -> int:
        if not 1 <= v <= 5:
            raise ValueError('Priority must be between 1 and 5')
        return v

