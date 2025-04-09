from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, or_
from app.models import Project
from app.schemas.project import ProjectRead, ProjectUpdate, ProjectCreate
from app.database import get_session


router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("/", response_model=ProjectRead)
async def create_project(project: ProjectCreate, session: Session = Depends(get_session)):
    statement = select(Project).where(
        or_(
            Project.name == project.name,
            Project.team_id == project.team_id
        )
    )
    existing_project = session.exec(statement).first()
    if existing_project:
        raise HTTPException(status_code=409,
                            detail="Project with this name already exists")
    new_project = Project(**project.model_dump())
    session.add(new_project)
    session.commit()
    session.refresh(new_project)
    return new_project


@router.get("/{project_name}", response_model=ProjectRead)
async def get_project(project_name: str, session: Session = Depends(get_session)):
    statement = select(Project).where(Project.name == project_name)
    project_to_get = session.exec(statement).first()
    if not project_to_get:
        raise HTTPException(status_code=404, detail="Project not found")
    return project_to_get


@router.delete("/delete/{project_id}", status_code=204)
async def delete_project(project_id, session: Session = Depends(get_session))
    project_to_delete = session.get(Project, project_id)
    if not project_to_delete:
        raise HTTPException(status_code=404, detail="User not found")
    session.delete(project_to_delete)
    session.commit()
    return