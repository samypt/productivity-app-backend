from datetime import datetime, timezone, timedelta
from sqlalchemy import (UniqueConstraint, CheckConstraint,
                        Column, String, Integer, ForeignKey, event)
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from uuid import uuid4
from .utils.time import get_time_stamp


class User(SQLModel, table=True):
    __tablename__ = 'users'
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True, max_length=255)
    first_name: str = Field(index=True, max_length=255)
    last_name: str = Field(index=True, max_length=255)
    hashed_password: str
    created_at: datetime = Field(default_factory=get_time_stamp)
    updated_at: datetime = Field(default_factory=get_time_stamp)
    role: str = Field(
        default="member",
        max_length=50,
        sa_column=Column(String(50), CheckConstraint("role IN ('admin', 'member')"))
    )
    avatar_url: Optional[str] = Field(default=None, index=True, unique=True)

    # New fields for Google Calendar integration

    google_access_token: Optional[str] = None
    google_refresh_token: Optional[str] = None
    google_token_expiry: Optional[str] = None  # ISO timestamp or datetime
    google_calendar_id: Optional[str] = Field(index=True, unique=True)
    google_calendar_html_link: Optional[str] = None

    # Relationships
    teams: List["Member"] = Relationship(back_populates='user', passive_deletes=True)
    events: List["Event"] = Relationship(back_populates='user', passive_deletes=True)
    invites_sent: List["Invite"] = Relationship(back_populates="inviter", passive_deletes=True)
    google_events: List["GoogleSyncedEvent"] = Relationship(back_populates="user", passive_deletes=True)




class Team(SQLModel, table=True):
    __tablename__ = 'teams'
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(unique=True,
                      max_length=255,
                      index=True,
                      sa_column_kwargs={"nullable": False})
    description: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=get_time_stamp)
    updated_at: datetime = Field(default_factory=get_time_stamp)

    # Relationships
    members: List["Member"] = Relationship(back_populates='team', passive_deletes=True)
    projects: List["Project"] = Relationship(back_populates='team', passive_deletes=True)
    invites_sent_by_members: List["Invite"] = Relationship(back_populates="team", passive_deletes=True)




class TaskMemberLink(SQLModel, table=True):
    __tablename__ = 'task_member_link'
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    task_id: str = Field(
        sa_column=Column(ForeignKey("tasks.id", ondelete="CASCADE"))
    )
    member_id: str = Field(
        sa_column=Column(ForeignKey("members.id", ondelete="CASCADE"))
    )
    # Defining the UNIQUE constraint on (task_id, member_id)
    __table_args__ = (
        UniqueConstraint("task_id", "member_id", name="unique_task_member"),
    )




class EventMemberLink(SQLModel, table=True):
    __tablename__ = 'event_member_link'
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    event_id: str = Field(
        sa_column=Column(ForeignKey("events.id", ondelete="CASCADE"))
    )
    member_id: str = Field(
        sa_column=Column(ForeignKey("members.id", ondelete="CASCADE"))
    )
    # Defining the UNIQUE constraint on (event_id, member_id)
    __table_args__ = (
        UniqueConstraint("event_id", "member_id", name="unique_event_member"),
    )




class Member(SQLModel, table=True):
    __tablename__ = 'members'
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    team_id: str = Field(
        sa_column=Column(ForeignKey("teams.id", ondelete="CASCADE"))
    )
    user_id: str = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"))
    )

    role: str = Field(
        default="editor",
        max_length=50,
        sa_column=Column(String(50), CheckConstraint("role IN ('owner', 'editor', 'viewer')"))
    )
    created_at: datetime = Field(default_factory=get_time_stamp)
    updated_at: datetime = Field(default_factory=get_time_stamp)

    # Defining the UNIQUE constraint on (team_id, user_id)
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="unique_team_user"),
    )

    # Relationships
    user: Optional["User"] = Relationship(back_populates='teams', passive_deletes=True)
    team: Optional["Team"] = Relationship(back_populates='members', passive_deletes=True)
    tasks: List["Task"] = Relationship(back_populates="members", link_model=TaskMemberLink,
                                       passive_deletes=True)
    events: List["Event"] = Relationship(back_populates="members", link_model=EventMemberLink,
                                       passive_deletes=True)



class Project(SQLModel, table=True):
    __tablename__ = 'projects'
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(max_length=255, index=True, sa_column_kwargs={"nullable": False})
    description: Optional[str] = Field(default=None)
    team_id: str = Field(
        sa_column=Column(ForeignKey("teams.id", ondelete="CASCADE"))
    )
    created_at: datetime = Field(default_factory=get_time_stamp)
    updated_at: datetime = Field(default_factory=get_time_stamp)

    # Relationships
    team: Optional["Team"] = Relationship(back_populates='projects', passive_deletes=True)
    boards: List["Board"] = Relationship(back_populates='project', passive_deletes=True)
    events: List["Event"] = Relationship(back_populates='project', passive_deletes=True)




class Board(SQLModel, table=True):
    __tablename__ = 'boards'
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(max_length=255, index=True, sa_column_kwargs={"nullable": False})
    project_id: str = Field(
        sa_column=Column(ForeignKey("projects.id", ondelete="CASCADE"))
    )
    created_at: datetime = Field(default_factory=get_time_stamp)
    updated_at: datetime = Field(default_factory=get_time_stamp)

    # Relationships
    project: Optional["Project"] = Relationship(back_populates='boards', passive_deletes=True)
    lists: List["BoardList"] = Relationship(back_populates='board', passive_deletes=True)



class BoardList(SQLModel, table=True):
    __tablename__ = 'board_lists'
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    name: str = Field(max_length=255, index=True, sa_column_kwargs={"nullable": False})
    board_id: str = Field(
        sa_column=Column(ForeignKey("boards.id", ondelete="CASCADE"))
    )
    position: int = Field(index=True, sa_column_kwargs={"nullable": False})
    created_at: datetime = Field(default_factory=get_time_stamp)
    updated_at: datetime = Field(default_factory=get_time_stamp)

    # Relationships
    board: Optional["Board"] = Relationship(back_populates='lists', passive_deletes=True)
    tasks: List["Task"] = Relationship(back_populates='list', passive_deletes=True)



class Task(SQLModel, table=True):
    __tablename__ = 'tasks'
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    list_id: str = Field(
        sa_column=Column(ForeignKey("board_lists.id", ondelete="CASCADE"))
    )
    title: str = Field(max_length=255, index=True, sa_column_kwargs={"nullable": False})
    description: Optional[str] = Field(default=None)
    status: str = Field(
        default="todo",
        max_length=50,
        sa_column=Column(String(50), CheckConstraint("status IN ('todo', 'in_progress', 'done')"))
    )
    priority: int = Field(
        default=5,
        sa_column=Column(Integer, CheckConstraint("priority BETWEEN 1 AND 5"))
    )

    due_date: datetime = Field(index=True, sa_column_kwargs={"nullable": False})
    created_at: datetime = Field(default_factory=get_time_stamp)
    updated_at: datetime = Field(default_factory=get_time_stamp)

    # Relationships
    list: Optional["BoardList"] = Relationship(back_populates='tasks', passive_deletes=True)
    members: List["Member"] = Relationship(back_populates='tasks', link_model=TaskMemberLink,
                                           passive_deletes=True)




class Event(SQLModel, table=True):
    __tablename__ = 'events'
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    title: str = Field(max_length=255, index=True, sa_column_kwargs={"nullable": False})
    project_id: str = Field(
        sa_column=Column(ForeignKey("projects.id", ondelete="CASCADE"))
    )
    description: Optional[str] = Field(default=None)
    start_time: datetime = Field(index=True, sa_column_kwargs={"nullable": False})
    end_time: datetime = Field(index=True, sa_column_kwargs={"nullable": False})
    created_by: str = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"))
    )
    created_at: datetime = Field(default_factory=get_time_stamp)
    updated_at: datetime = Field(default_factory=get_time_stamp)

    # Relationships
    project: Optional["Project"] = Relationship(back_populates="events", passive_deletes=True)
    user: Optional["User"] = Relationship(back_populates="events", passive_deletes=True)
    members: List["Member"] = Relationship(back_populates='events', link_model=EventMemberLink,
                                           passive_deletes=True)
    google_events: List["GoogleSyncedEvent"] = Relationship(back_populates="event", passive_deletes=True)




class GoogleSyncedEvent(SQLModel, table=True):
    __tablename__ = 'google_events'
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    event_id: str = Field(
        sa_column=Column(ForeignKey("events.id", ondelete="CASCADE"))
    )
    user_id:  str = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"))
    )
    google_event_id: str
    google_calendar_id: Optional[str] = Field(index=True)
    updated_at: datetime = Field(default_factory=get_time_stamp)

    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="unique_event_user"),
        )

    # Relationships
    user: Optional["User"] = Relationship(back_populates="google_events", passive_deletes=True)
    event: Optional["Event"] = Relationship(back_populates="google_events", passive_deletes=True)




class Invite(SQLModel, table=True):
    __tablename__ = 'invites'
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    team_id : str = Field(
        sa_column=Column(ForeignKey("teams.id", ondelete="CASCADE"))
    )
    role: str = Field(
        default="editor",
        max_length=50,
        sa_column=Column(String(50), CheckConstraint("role IN ('owner', 'editor', 'viewer')"))
    )
    email: str = Field(index=True, max_length=255, nullable=False)
    token: str = Field(default_factory=lambda: uuid4().hex, index=True)
    invited_by: str = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"))
    )
    created_at: datetime = Field(default_factory=get_time_stamp)
    updated_at: datetime = Field(default_factory=get_time_stamp)
    expires_at: datetime = Field(default_factory=lambda: get_time_stamp() + timedelta(days=7))
    status: str = Field(
        default="pending",
        max_length=50,
        sa_column=Column(String(50), CheckConstraint("type IN ('pending', 'accepted', 'declined')"))
    )
    registered: bool = Field(default=False)

    # Defining the UNIQUE constraint on (team_id, email)
    __table_args__ = (
        UniqueConstraint("team_id", "email", name="unique_team_email_invite"),
    )

    def __repr__(self):
        return f"<Invite id={self.id} email={self.email} team_id={self.team_id}>"

    @property
    def is_expired(self) -> bool:
        return get_time_stamp() > self.expires_at.replace(tzinfo=timezone.utc)

    # Relationships
    inviter: Optional["User"] = Relationship(back_populates="invites_sent", passive_deletes=True)
    team: Optional["Team"] = Relationship(back_populates="invites_sent_by_members", passive_deletes=True)



class Notification(SQLModel, table=True):
    __tablename__ = 'notifications'
    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    user_id: str = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"))
    )
    sender_id: str = Field(
        sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"))
    )
    object_type: str = Field(
        max_length=50,
        sa_column=Column(String(50), CheckConstraint("type IN ('task', 'event', 'invitation')"))
    )
    object_id: str = Field(index=True, max_length=255, nullable=False)
    # status: str = Field(
    #     default="pending",
    #     max_length=50,
    #     sa_column=Column(String(50), CheckConstraint("type IN ('pending', 'accepted', 'declined')"))
    # )
    message: Optional[str] = Field(default=None)
    is_read: bool = Field(default=False)

    created_at: datetime = Field(default_factory=get_time_stamp)
    updated_at: datetime = Field(default_factory=get_time_stamp)




@event.listens_for(SQLModel, "before_update", propagate=True)
def auto_update_timestamp(_, __, target):
    if hasattr(target, "updated_at"):
        target.updated_at = get_time_stamp()