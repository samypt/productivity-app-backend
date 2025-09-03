from datetime import datetime
from typing import Optional, Literal, List
from .user import UserPublic
from sqlmodel import SQLModel
from uuid import UUID
from pydantic import model_validator
from enum import Enum




class Status(str, Enum):
    todo = "todo"
    in_progress = "in_progress"
    done = "done"



class TaskCreate(SQLModel):
    title: str
    description: Optional[str] = None
    list_id: str
    status: Optional["Status"] = "todo"
    priority: int
    due_date: datetime

    @model_validator(mode='after')
    def validate_priority(self):
        if not 1 <= self.priority <= 5:
            raise ValueError('Priority must be between 1 and 5')
        return self




class TaskRead(TaskCreate):
    id: UUID
    created_at: Optional[datetime]

    class Config:
        orm_mode = True




class TaskUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    list_id: Optional[str] = None
    status: Optional[Literal["todo", "in_progress", "done"]] = None
    priority: Optional[int] = None
    due_date: Optional[datetime] = None

    @model_validator(mode='after')
    def validate_priority(self):
        if self.priority and not 1 <= self.priority <= 5:
            raise ValueError('Priority must be between 1 and 5')
        return self




class TaskList(SQLModel):
    tasks: List[TaskRead]
    total: Optional[int] = 0

    class Config:
        orm_mode = True



class TaskFull(TaskRead):
    members: List[UserPublic]

    class Config:
        orm_mode = True


class TaskListFull(SQLModel):
    tasks: List[TaskFull]
    total: Optional[int] = 0

    class Config:
        orm_mode = True





class MoveTaskRequest(SQLModel):
    list_id: str