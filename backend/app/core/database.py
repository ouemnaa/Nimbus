import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel
from pymongo.errors import PyMongoError

from app.core.config import Settings, get_settings


logger = logging.getLogger("nimbus-backend")


class DatabaseManager:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: AsyncIOMotorClient[Any] | None = None
        self._database: AsyncIOMotorDatabase[Any] | None = None

    @property
    def database(self) -> AsyncIOMotorDatabase[Any]:
        if self._database is None:
            raise RuntimeError("Database connection has not been initialized.")
        return self._database

    async def connect(self) -> None:
        if not self.settings.mongodb_uri:
            raise RuntimeError(
                "MONGODB_URI is required. Add it to backend/.env before startup."
            )

        self._client = AsyncIOMotorClient(
            self.settings.mongodb_uri,
            serverSelectionTimeoutMS=5_000,
            uuidRepresentation="standard",
        )
        self._database = self._client[self.settings.mongodb_db_name]

        try:
            await self._client.admin.command("ping")
            await self.create_indexes()
        except Exception:
            self._client.close()
            self._client = None
            self._database = None
            logger.exception(
                "Could not connect to MongoDB database %s.",
                self.settings.mongodb_db_name,
            )
            raise RuntimeError("Could not connect to MongoDB.") from None

        logger.info(
            "Connected to MongoDB database %s.", self.settings.mongodb_db_name
        )

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._database = None
            logger.info("MongoDB connection closed.")

    async def ping(self) -> bool:
        if self._client is None:
            return False
        try:
            await self._client.admin.command("ping")
            return True
        except PyMongoError:
            return False

    async def create_indexes(self) -> None:
        database = self.database
        await database.projects.create_indexes(
            [
                IndexModel([("slug", ASCENDING)], unique=True, name="slug_unique"),
                IndexModel([("userId", ASCENDING)], name="user_id"),
                IndexModel([("createdAt", DESCENDING)], name="created_at_desc"),
            ]
        )
        await database.architecture_versions.create_indexes(
            [
                IndexModel([("projectId", ASCENDING)], name="project_id"),
                IndexModel(
                    [("projectId", ASCENDING), ("version", ASCENDING)],
                    unique=True,
                    name="project_version_unique",
                ),
                IndexModel(
                    [("projectId", ASCENDING), ("createdAt", ASCENDING)],
                    name="project_created_at",
                ),
            ]
        )
        await database.chat_messages.create_indexes(
            [
                IndexModel(
                    [("projectId", ASCENDING), ("createdAt", ASCENDING)],
                    name="project_created_at",
                )
            ]
        )
        await database.change_requests.create_indexes(
            [
                IndexModel([("projectId", ASCENDING)], name="project_id"),
                IndexModel([("status", ASCENDING)], name="status"),
            ]
        )


database_manager = DatabaseManager()
