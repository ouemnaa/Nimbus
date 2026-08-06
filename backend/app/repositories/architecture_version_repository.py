from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, ReturnDocument

from app.models.architecture_version import COLLECTION_NAME


class ArchitectureVersionRepository:
    def __init__(self, database: AsyncIOMotorDatabase[Any]) -> None:
        self.collection = database[COLLECTION_NAME]

    async def create(self, document: dict[str, Any]) -> dict[str, Any]:
        result = await self.collection.insert_one(document)
        return {**document, "_id": result.inserted_id}

    async def get_by_id(self, version_id: ObjectId) -> dict[str, Any] | None:
        return await self.collection.find_one({"_id": version_id})

    async def list_for_project(self, project_id: ObjectId) -> list[dict[str, Any]]:
        return await self.collection.find({"projectId": project_id}).sort(
            "createdAt", ASCENDING
        ).to_list(None)

    async def delete_for_project(self, project_id: ObjectId) -> int:
        result = await self.collection.delete_many({"projectId": project_id})
        return result.deleted_count

    async def set_status(
        self, version_id: ObjectId, status: str
    ) -> dict[str, Any] | None:
        return await self.collection.find_one_and_update(
            {"_id": version_id},
            {"$set": {"status": status}},
            return_document=ReturnDocument.AFTER,
        )
