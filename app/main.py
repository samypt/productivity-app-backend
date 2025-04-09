from fastapi import FastAPI
from app.routers.users import router as user_router
from app.routers.teams import router as team_router
from app.routers.projects import router as project_router

app = FastAPI()

app.include_router(user_router, prefix="/api")
app.include_router(team_router, prefix="/api")
app.include_router(project_router, prefix="/api")

