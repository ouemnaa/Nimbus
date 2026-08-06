import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.api_router import api_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings
from app.core.database import DatabaseManager, database_manager
from app.core.errors import AppError


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("nimbus-backend")


def create_app(manager: DatabaseManager | Any = database_manager) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await manager.connect()
        try:
            yield
        finally:
            await manager.close()

    settings = get_settings()
    application = FastAPI(
        title="Nimbus Backend",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.state.database_manager = manager

    allowed_origins = list(
        dict.fromkeys(
            [
                settings.frontend_url.rstrip("/"),
                "http://localhost:3000",
                "http://localhost:5173",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
            ]
        )
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.exception_handler(AppError)
    async def handle_app_error(_: Request, error: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={"detail": {"code": error.code, "message": error.message}},
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(_: Request, error: Exception) -> JSONResponse:
        logger.exception("Unhandled request error: %s", type(error).__name__)
        return JSONResponse(
            status_code=500,
            content={
                "detail": {
                    "code": "internal_error",
                    "message": "An internal error occurred.",
                }
            },
        )

    application.include_router(health_router)
    application.include_router(api_router)
    return application


app = create_app()
