from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.models import  Task, BoardList
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