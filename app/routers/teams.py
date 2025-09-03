from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, and_
from app.models import Member, Team
from app.schemas.teams import TeamCreate, TeamRead, TeamUpdate
from app.schemas.project import ProjectList, ProjectRead
from app.database import get_session
from typing import Annotated
from ..schemas.user import UserPublic, UserList
from ..services.auth import get_current_user


router = APIRouter(prefix="/team", tags=["Team"])
user_dependency = Annotated[dict, Depends(get_current_user)]


def validate_membership(user_id:str, team_id:str, session: Session):
    statement = select(Member).where(and_(
        Member.user_id == user_id,
        Member.team_id == team_id
    ))
    membership = session.exec(statement).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied, user is not a member of the team.")
    return membership


@router.post("/create", response_model=TeamRead)
async def create_team(current_user: user_dependency, team: TeamCreate, session: Session = Depends(get_session)):
    statement = select(Team).where(Team.name == team.name)
    existing_team = session.exec(statement).first()
    if existing_team:
        raise HTTPException(status_code=409, detail="Team with this name already exists")
    new_team = Team(**team.model_dump())
    team_owner = Member(team_id = new_team.id, user_id = current_user.get("id"), role ="owner")
    session.add(new_team)
    session.add(team_owner)
    session.commit()
    session.refresh(team_owner)
    session.refresh(new_team)
    return new_team


@router.put("/update/{team_id}", response_model=TeamRead)
async def update_team(current_user: user_dependency, team_id: str, team: TeamUpdate,
                       session: Session = Depends(get_session)):
    member = validate_membership(current_user.get("id"), team_id, session)
    if member.role != "owner":
        raise HTTPException(
            status_code=403,
            detail="You are not authorized to modify team data. Only the owner can perform this action."
        )
    team_to_update = session.get(Team, team_id)
    if not team_to_update:
        raise HTTPException(status_code=404, detail="Team not found")
    data_to_update = team.model_dump(exclude_unset=True)
    for key, value in data_to_update.items():
        setattr(team_to_update, key, value)
    session.add(team_to_update)
    session.commit()
    session.refresh(team_to_update)
    return team_to_update


@router.delete("/delete/{team_id}", status_code=204)
async def delete_team(current_user: user_dependency, team_id: str,
                      session: Session = Depends(get_session)):
    member = validate_membership(current_user.get("id"), team_id, session)
    if member.role == "owner":
        team_to_delete = session.get(Team, team_id)
        if not team_to_delete:
            raise HTTPException(status_code=404, detail="Team not found")
        session.delete(team_to_delete)
        session.commit()
    else:
        session.delete(member)
        session.commit()
    return


@router.get("/{team_id}", response_model=ProjectList)
async def get_team(current_user: user_dependency,
                   team_id: str,
                   session: Session = Depends(get_session)):
    validate_membership(current_user.get("id"), team_id, session)
    team = session.get(Team, team_id)
    return ProjectList(projects=[ProjectRead.model_validate(project) for project in team.projects],
                       team=TeamRead.model_validate(team))


@router.get("/members/{team_id}", response_model=UserList)
async def get_team_members(current_user: user_dependency,
                           team_id: str,
                           limit: int = Query(5, ge=1),
                           offset: int = Query(0, ge=0),
                   session: Session = Depends(get_session)):
    validate_membership(current_user.get("id"), team_id, session)
    statement = select(Member).where(Member.team_id == team_id).offset(offset).limit(limit)
    members = session.exec(statement).all()




    # team = session.get(Team, team_id)
    return UserList(
        users=[
            UserPublic.model_validate({**member.user.model_dump(), "membership": member})
            for member in members
        ]
    )
# not ready!!!!!!!!!!!!!!!!!!!!!!!!!!!!