from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, ReturnDocument
from datetime import datetime, timezone

from app.models.change_request import COLLECTION_NAME


class ChangeRequestRepository:
    def __init__(self, database: AsyncIOMotorDatabase[Any]) -> None:
        self.collection = database[COLLECTION_NAME]

    async def create(self, document: dict[str, Any]) -> dict[str, Any]:
        result = await self.collection.insert_one(document)
        return {**document, "_id": result.inserted_id}

    async def list_for_project(self, project_id: ObjectId) -> list[dict[str, Any]]:
        return await self.collection.find({"projectId": project_id}).sort(
            "createdAt", ASCENDING
        ).to_list(None)

    async def get_pending_for_version(
        self, project_id: ObjectId, version_id: ObjectId
    ) -> dict[str, Any] | None:
        return await self.collection.find_one(
            {
                "projectId": project_id,
                "toVersionId": version_id,
                "status": "pending",
            }
        )

    async def set_status(
        self, change_request_id: ObjectId, status: str
    ) -> dict[str, Any] | None:
        return await self.collection.find_one_and_update(
            {"_id": change_request_id},
            {
                "$set": {
                    "status": status,
                    "updatedAt": datetime.now(timezone.utc),
                }
            },
            return_document=ReturnDocument.AFTER,
        )

    async def delete_for_project(self, project_id: ObjectId) -> int:
        result = await self.collection.delete_many({"projectId": project_id})
        return result.deleted_count
