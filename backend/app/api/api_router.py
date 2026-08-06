from fastapi import APIRouter

from app.api.routes import messages, projects, versions


api_router = APIRouter(prefix="/api")
api_router.include_router(projects.router)
api_router.include_router(versions.router)
api_router.include_router(messages.router)
