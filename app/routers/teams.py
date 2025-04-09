from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, or_
from app.models import Team
from app.schemas.teams import TeamCreate, TeamRead
from app.database import get_session


router = APIRouter(prefix="/team", tags=["Team"])


@router.post("/team", response_model=TeamRead)
async  def create_team(team: TeamCreate, session: Session = Depends(get_session)):
    statement = select(Team).where(Team.name == team.name)
    team_exists = session.exec(statement).first()
    if team_exists:
        raise HTTPException(status_code=409, detail="Team with this name already exists")
    new_team = Team(
        name=team.name,
        description=team.description
    )
    session.add(new_team)
    session.commit()
    session.refresh(new_team)
    return new_team