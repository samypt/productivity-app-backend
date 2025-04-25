from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.users import router as user_router
from app.routers.teams import router as team_router
from app.routers.projects import router as project_router
from app.routers.members import router as member_router
from app.routers.boards import router as board_router
from app.routers.board_lists import router as board_list_router
from app.routers.tasks import router as task_router
from app.routers.events import router as event_router
from app.routers.auth import router as auth_router

app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 👈 React frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(team_router, prefix="/api")
app.include_router(project_router, prefix="/api")
app.include_router(member_router, prefix="/api")
app.include_router(board_router, prefix="/api")
app.include_router(board_list_router, prefix="/api")
app.include_router(task_router, prefix="/api")
app.include_router(event_router, prefix="/api")
