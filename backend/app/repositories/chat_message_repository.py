from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING

from app.models.chat_message import COLLECTION_NAME


class ChatMessageRepository:
    def __init__(self, database: AsyncIOMotorDatabase[Any]) -> None:
        self.collection = database[COLLECTION_NAME]

    async def create(self, document: dict[str, Any]) -> dict[str, Any]:
        result = await self.collection.insert_one(document)
        return {**document, "_id": result.inserted_id}

    async def list_for_project(self, project_id: ObjectId) -> list[dict[str, Any]]:
        return await self.collection.find({"projectId": project_id}).sort(
            "createdAt", ASCENDING
        ).to_list(None)

    async def list_recent_for_project(
        self, project_id: ObjectId, limit: int
    ) -> list[dict[str, Any]]:
        documents = await self.collection.find({"projectId": project_id}).sort(
            "createdAt", DESCENDING
        ).to_list(limit)
        return list(reversed(documents))

    async def delete_for_project(self, project_id: ObjectId) -> int:
        result = await self.collection.delete_many({"projectId": project_id})
        return result.deleted_count
