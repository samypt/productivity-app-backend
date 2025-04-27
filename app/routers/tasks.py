from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, and_
from app.models import BoardList, Task, TaskMemberLink, Member
from app.schemas.task import TaskRead, TaskCreate, TaskUpdate
from app.database import get_session


router = APIRouter(prefix="/tasks", tags=["Tasks"])
db_session = Depends(get_session)


@router.post("/", response_model=TaskRead)
async def create_task(task: TaskCreate, session: Session = db_session):
    statement = select(BoardList).where(BoardList.id == task.list_id)
    existing_list = session.exec(statement).first()
    if not existing_list:
        raise HTTPException(status_code=404, detail="BoardList not found")
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


@router.put("/{task_id}", response_model=TaskRead)
async def update_task(task_id: str, task: TaskUpdate, session: Session = db_session):
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


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, session: Session = db_session):
    task_to_delete = session.get(Task, task_id)
    if not task_to_delete:
        raise HTTPException(status_code=404, detail="Task not found")
    session.delete(task_to_delete)
    session.commit()
    return


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
        raise HTTPException(status_code=400, detail="TaskMemberLink already exists")



@router.post("/{task_id}", response_model=TaskMemberLink)
async def assign_task_to_member(task_id: str, member_id: str, session: Session = db_session):
    validate_assignment(session, task_id, member_id)
    new_link = TaskMemberLink(task_id = task_id,
                              member_id = member_id
    )
    session.add(new_link)
    session.commit()
    session.refresh(new_link)
    return new_link
