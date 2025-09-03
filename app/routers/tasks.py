from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, and_, func
from app.models import BoardList, Task, TaskMemberLink, Member, Notification, User
from app.schemas.task import TaskRead, TaskCreate, TaskUpdate, TaskListFull, TaskFull, MoveTaskRequest
from app.database import get_session
from typing import Annotated
from .notifications import get_unread_notifications_count
from ..services.manager import ws_connection_manager
from ..schemas.member import AssignRequest
from ..schemas.user import UserPublic
from ..services.auth import get_current_user
from ..utils.time import get_time_stamp


router = APIRouter(prefix="/tasks", tags=["Tasks"])
db_session = Depends(get_session)
user_dependency = Annotated[dict, Depends(get_current_user)]

def validate_member(user_id:str, list_id:str, session: Session):
    board_list = session.get(BoardList, list_id)
    if not board_list:
        raise HTTPException(status_code=404, detail="List not found")
    statement = select(Member).where(and_(
        Member.user_id == user_id,
        Member.team_id == board_list.board.project.team_id
    ))
    membership = session.exec(statement).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied, user is not a member of the team.")
    return membership


def validate_membership(user_id:str, task_id:str, session: Session):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    statement = select(Member).where(and_(
        Member.user_id == user_id,
        Member.team_id == task.list.board.project.team_id
    ))
    membership = session.exec(statement).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied, user is not a member of the team.")
    return task


@router.post("/create", response_model=TaskRead)
async def create_task(current_user: user_dependency,
                      task: TaskCreate, session: Session = db_session):
    validate_member(current_user.get("id"), task.list_id, session)
    # statement = select(BoardList).where(BoardList.id == task.list_id)
    # existing_list = session.exec(statement).first()
    # if not existing_list:
    #     raise HTTPException(status_code=404, detail="BoardList not found")
    new_task = Task(**task.model_dump())
    session.add(new_task)
    session.commit()
    session.refresh(new_task)
    return new_task


@router.get("/{task_id}", response_model=TaskRead)
async def get_task(task_id: str, session: Session = db_session):
    task_to_get = session.get(Task, task_id)
    if not task_to_get:
        raise HTTPException(status_code=404, detail="Task not found")
    return task_to_get


@router.get("/list/{list_id}", response_model=TaskListFull)
async def get_list_tasks(
    current_user: user_dependency,
    list_id: str,
    limit: int = Query(5, ge=1),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("updated_at"),
    sort_order: str = Query("desc"),
    session: Session = db_session
):
    validate_member(current_user.get("id"), list_id, session)

    total = session.exec(
        select(func.count()).select_from(Task).where(Task.list_id == list_id)
    ).one()

    # Valid sort fields
    valid_sort_fields = {"updated_at", "due_date", "priority", "status", "title"}
    if sort_by not in valid_sort_fields:
        raise HTTPException(status_code=400, detail="Invalid sort_by field")

    # Determine main sort column
    column = getattr(Task, sort_by)
    if sort_order == "desc":
        column = column.desc()
    else:
        column = column.asc()

    # Stable sort: add Task.id as a tiebreaker
    tasks_query = (
        select(Task)
        .where(Task.list_id == list_id)
        .order_by(column, Task.id.asc())
        .offset(offset)
        .limit(limit)
    )

    tasks = session.exec(tasks_query).all()

    tasks_full = []
    for task in tasks:
        task_data = TaskFull(
            **task.model_dump(),
            members=[
                UserPublic.model_validate({**member.user.model_dump(), "membership": member})
                for member in task.members
            ]
        )
        tasks_full.append(task_data)

    return TaskListFull(
        tasks=[TaskFull.model_validate(task) for task in tasks_full],
        total=total
    )




@router.put("/update/{task_id}", response_model=TaskRead)
async def update_task(current_user: user_dependency,
                      task_id: str, task: TaskUpdate, session: Session = db_session):
    validate_member(current_user.get("id"), task.list_id, session)
    task_to_update = session.get(Task, task_id)
    if not task_to_update:
        raise HTTPException(status_code=404, detail="Task not found")
    statement = select(BoardList).where(BoardList.id == task.list_id)
    existing_list = session.exec(statement).first()
    if not existing_list:
        raise HTTPException(status_code=404, detail="BoardList not found")
    data_to_update = task.model_dump(exclude_unset=True)
    for key, value in data_to_update.items():
        setattr(task_to_update, key, value)
    session.add(task_to_update)
    session.commit()
    session.refresh(task_to_update)
    return  task_to_update


@router.delete("/delete/{task_id}", status_code=204)
async def delete_task(current_user: user_dependency,
                      task_id: str, session: Session = db_session):
    task_to_delete = validate_membership(current_user.get("id"), task_id, session)
    session.delete(task_to_delete)
    session.commit()
    return


@router.post("/move/{task_id}", response_model=TaskRead)
async def move_task(
    current_user: user_dependency,
    task_id: str,
    data: MoveTaskRequest,
    session: Session = Depends(get_session),
):
    list_id = data.list_id
    # Validate that the task belongs to the user
    task = validate_membership(current_user.get("id"), task_id, session)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Validate that the user has access to the target list
    validate_member(current_user.get("id"), list_id, session)

    # Check if target list exists
    board_list = session.get(BoardList, list_id)
    if not board_list:
        raise HTTPException(status_code=404, detail="List not found")

    # Ensure task stays within the same board
    if task.list.board_id != board_list.board_id:
        raise HTTPException(status_code=400, detail="Task cannot be moved to another board")

    # Update task with transaction safety
    try:
        task.list_id = list_id
        session.add(task)
        session.commit()
    except Exception:
        session.rollback()
        raise

    return task


def validate_assignment(session: Session, task_id: str, member_id: str):
    """
    Validates that both the task and member exist before creating a new assignment.

    Args:
        session (Session): The database session.
        task_id (str): ID of the task to validate.
        member_id (str): ID of the member to validate.

    Raises:
        HTTPException: If either the task or the member does not exist.
    """

    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if task.list.board.project.team_id != member.team_id:
        raise HTTPException(status_code=400, detail="Task and Member must belong to the same team")

    statement = select(TaskMemberLink).where(
        and_(
            TaskMemberLink.member_id == member_id,
            TaskMemberLink.task_id == task_id
        )
    )

    link = session.exec(statement).first()
    if link:
        raise HTTPException(status_code=400, detail="Member is already assigned")


def validate_unassignment(session: Session, task_id: str, member_id: str):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    member = session.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    if task.list.board.project.team_id != member.team_id:
        raise HTTPException(status_code=400, detail="Task and Member must belong to the same team")

    statement = select(TaskMemberLink).where(
        TaskMemberLink.member_id == member_id,
        TaskMemberLink.task_id == task_id
    )
    link = session.exec(statement).first()
    if not link:
        raise HTTPException(status_code=400, detail="Member is not assigned to this task")


def get_task_and_assignee(session: Session, task_id: str, member_id: str):
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    assignee_statement = select(Member).where(
        Member.id == member_id,
        Member.team_id == task.list.board.project.team_id
    )
    assignee: Member = session.exec(assignee_statement).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="Assignee not found in the team")

    return task, assignee


def notify_if_needed(session: Session, *, task: Task, inviter: User, assignee: Member, action: str):
    if inviter.id == assignee.user_id:
        return

    action_phrases = {
        "assigned": "assigned to",
        "unassigned": "unassigned from",
    }

    phrase = action_phrases.get(action, f"{action} from")

    message = (
        f"You've been {phrase} task '{task.title}' by "
        f"{inviter.first_name} {inviter.last_name}. "
        f"For questions, contact {inviter.email}."
    )

    notification_statement = select(Notification).where(
        Notification.user_id == assignee.user_id,
        Notification.sender_id == inviter.id,
        Notification.object_type == "task",
        Notification.object_id == task.id,
        Notification.message == message
    )
    existing = session.exec(notification_statement).first()

    if not existing:
        session.add(Notification(
            user_id=assignee.user_id,
            sender_id=inviter.id,
            object_type="task",
            object_id=task.id,
            message=message
        ))

    else:
        existing.updated_at = get_time_stamp()
        session.add(existing)

    session.commit()



@router.post("/assign/{task_id}", response_model=TaskMemberLink)
async def assign_task_to_member(
    current_user: user_dependency,
    task_id: str,
    body: AssignRequest,
    session: Session = db_session
):
    inviter = session.get(User, current_user.get("id"))
    member_id = body.member_id

    validate_assignment(session, task_id, member_id)

    task, assignee = get_task_and_assignee(session, task_id, member_id)

    new_link = TaskMemberLink(task_id=task.id, member_id=member_id)
    session.add(new_link)

    notify_if_needed(session, task=task, inviter=inviter, assignee=assignee, action="assigned")

    session.commit()

    notifications_count = get_unread_notifications_count(assignee.user_id, session)
    await ws_connection_manager.send_to_user(
        user_id=assignee.user_id,
        message={"type": "task", "msg": "assign", "count": notifications_count}
    )

    session.refresh(new_link)
    return new_link


@router.post("/unassign/{task_id}", status_code=204)
async def unassign_task_from_member(
    current_user: user_dependency,
    task_id: str,
    body: AssignRequest,
    session: Session = db_session
):
    inviter = session.get(User, current_user.get("id"))
    member_id = body.member_id

    validate_unassignment(session, task_id, member_id)

    statement = select(TaskMemberLink).where(
        TaskMemberLink.member_id == member_id,
        TaskMemberLink.task_id == task_id
    )
    link_to_delete = session.exec(statement).first()
    if not link_to_delete:
        raise HTTPException(status_code=404, detail="Assignment not found")

    task , assignee = get_task_and_assignee(session, task_id, member_id)

    session.delete(link_to_delete)
    notify_if_needed(session, task=task, inviter=inviter, assignee=assignee, action="unassigned")

    session.commit()
    notifications_count = get_unread_notifications_count(assignee.user_id, session)
    await ws_connection_manager.send_to_user(
        user_id=assignee.user_id,
        message={"type": "task", "msg": "unassign", "count": notifications_count}
    )
    return
