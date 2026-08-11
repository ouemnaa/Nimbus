from fastapi import APIRouter, Request

from app.core.errors import DatabaseUnavailableError


router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "nimbus-backend"}


@router.get("/health/db")
async def database_health(request: Request) -> dict[str, str]:
    if not await request.app.state.database_manager.ping():
        raise DatabaseUnavailableError()
    return {"status": "ok", "database": "connected"}
