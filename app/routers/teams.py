from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from app.models import Team
from app.schemas.teams import TeamCreate, TeamRead, TeamUpdate
from app.database import get_session


router = APIRouter(prefix="/team", tags=["Team"])


@router.post("/create", response_model=TeamRead)
async  def create_team(team: TeamCreate, session: Session = Depends(get_session)):
    statement = select(Team).where(Team.name == team.name)
    existing_team = session.exec(statement).first()
    if existing_team:
        raise HTTPException(status_code=409, detail="Team with this name already exists")
    new_team = Team(**team.model_dump())
    session.add(new_team)
    session.commit()
    session.refresh(new_team)
    return new_team


@router.put("/update/{team_id}", response_model=TeamRead)
async  def update_team(team_id: str, team: TeamUpdate,
                       session: Session = Depends(get_session)):
    statement = select(Team).where(Team.id == team_id)
    team_to_update = session.exec(statement).first()
    if not team_to_update:
        raise HTTPException(status_code=404, detail="Team not found")
    data_to_update = team.model_dump(exclude_unset=True)
    for key, value in data_to_update.items():
        setattr(team_to_update, key, value)
    session.add(team_to_update)
    session.commit()
    session.refresh(team_to_update)
    return team_to_update


@router.delete("/delete{team_id}", status_code=204)
async def delete_team(team_id: str, session: Session = Depends(get_session)):
    statement = select(Team).where(Team.id == team_id)
    team_to_delete = session.exec(statement).first()
    if not team_to_delete:
        raise HTTPException(status_code=404, detail="Team not found")
    session.delete(team_to_delete)
    session.commit()
    return