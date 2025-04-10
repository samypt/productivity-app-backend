from datetime import datetime
from typing import Optional, Literal
from sqlmodel import SQLModel
from uuid import UUID
from pydantic import model_validator


class EventCreate(SQLModel):
    title: str
    description: Optional[str]
    project_id: str
    start_time: datetime
    end_time: datetime
    created_by: str

    @model_validator(mode='after')
    def check_end_time(self):
        if self.start_time >= self.end_time:
            raise ValueError("End Time must be later than Start Time")
        return self




class EventRead(EventCreate):
    id: UUID
    created_at: Optional[datetime]

    class Config:
        orm_mode = True




class EventUpdate(SQLModel):
    title: Optional[str]
    description: Optional[str]
    start_time: Optional[datetime]
    end_time: Optional[datetime]

    @model_validator(mode='after')
    def check_end_time(self):
        if (self.start_time and self.end_time
                and self.start_time >= self.end_time):
            raise ValueError("End Time must be later than Start Time")
        return self

