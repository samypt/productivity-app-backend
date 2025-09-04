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
from app.routers.invite import router as invite_router
from app.routers.notifications import router as notification_router
from app.routers.websocket import router as websocket_router
from app.routers.google_sync import router as google_sync_router

from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from fastapi.staticfiles import StaticFiles
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from .services.notifications.cleanup import delete_old_notifications
from contextlib import asynccontextmanager
import subprocess
import os

# Logger
logger = logging.getLogger("uvicorn.error")

# APScheduler instance
scheduler = BackgroundScheduler()

# Lifespan context
# Delete old read notifications
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     # On startup
#     scheduler.add_job(delete_old_notifications, "cron", hour=2)
#     scheduler.start()
#     logger.info("Scheduler started")
#
#     yield  # App runs here
#
#     # On shutdown
#     scheduler.shutdown()
#     logger.info("Scheduler stopped")

@asynccontextmanager
async def scheduler_lifespan(app: FastAPI):
    """Start/stop background scheduler."""
    scheduler.add_job(delete_old_notifications, "cron", hour=2)
    scheduler.start()
    logger.info("Scheduler started")

    yield

    scheduler.shutdown()
    logger.info("Scheduler stopped")


@asynccontextmanager
async def migration_lifespan(app: FastAPI):
    """Run Alembic migrations if enabled via env var."""
    if os.getenv("RUN_MIGRATIONS", "false").lower() == "true":
        try:
            logger.info("Generating new Alembic migration...")
            subprocess.run(["alembic", "revision", "--autogenerate", "-m", "auto-generated"], check=True)
        except subprocess.CalledProcessError as e:
            logger.warning(f"No new migration generated or error: {e}")
        try:
            print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
            logger.info("Running Alembic migrations...")
            subprocess.run(["alembic", "upgrade", "head"], check=True)
            logger.info("Alembic migrations applied successfully.")
            print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
        except Exception as e:
            logger.error(f"Error running migrations: {e}")

    yield


# Combine lifespans into one
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with migration_lifespan(app):
        async with scheduler_lifespan(app):
            yield


# App instance
app = FastAPI(lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom HTTP exception handler
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    logger.error(f"HTTPException on {request.url}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# API routers
prefix = "/api"

app.include_router(auth_router, prefix=prefix)
app.include_router(user_router, prefix=prefix)
app.include_router(team_router, prefix=prefix)
app.include_router(project_router, prefix=prefix)
app.include_router(member_router, prefix=prefix)
app.include_router(board_router, prefix=prefix)
app.include_router(board_list_router, prefix=prefix)
app.include_router(task_router, prefix=prefix)
app.include_router(event_router, prefix=prefix)
app.include_router(invite_router, prefix=prefix)
app.include_router(notification_router, prefix=prefix)
app.include_router(websocket_router)
app.include_router(google_sync_router, prefix=prefix)

# avatar access
app.mount("/static/avatars", StaticFiles(directory="uploads/avatars"), name="avatars")

# app = FastAPI()
# logger = logging.getLogger("uvicorn.error")
#
# origins = [
#     "http://localhost:5174",
# ]
#
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # React frontend origin
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )
#
#
#
# @app.exception_handler(HTTPException)
# async def custom_http_exception_handler(request: Request, exc: HTTPException):
#     logger.error(f"HTTPException on {request.url}: {exc.detail}")
#     return JSONResponse(
#         status_code=exc.status_code,
#         content={"detail": exc.detail},
#     )
#
# prefix = "/api"
#
# app.include_router(auth_router, prefix=prefix)
# app.include_router(user_router, prefix=prefix)
# app.include_router(team_router, prefix=prefix)
# app.include_router(project_router, prefix=prefix)
# app.include_router(member_router, prefix=prefix)
# app.include_router(board_router, prefix=prefix)
# app.include_router(board_list_router, prefix=prefix)
# app.include_router(task_router, prefix=prefix)
# app.include_router(event_router, prefix=prefix)
# app.include_router(invite_router, prefix=prefix)
# app.include_router(notification_router, prefix=prefix)
# app.include_router(websocket_router)
