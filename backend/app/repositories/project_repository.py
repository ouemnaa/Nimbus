from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING, ReturnDocument

from app.models.project import COLLECTION_NAME, set_current_version_update


class ProjectRepository:
    def __init__(self, database: AsyncIOMotorDatabase[Any]) -> None:
        self.collection = database[COLLECTION_NAME]

    async def list_all(self) -> list[dict[str, Any]]:
        return await self.collection.find().sort("updatedAt", DESCENDING).to_list(None)

    async def get_by_id(self, project_id: ObjectId) -> dict[str, Any] | None:
        return await self.collection.find_one({"_id": project_id})

    async def get_by_slug(self, slug: str) -> dict[str, Any] | None:
        return await self.collection.find_one({"slug": slug})

    async def create(self, document: dict[str, Any]) -> dict[str, Any]:
        result = await self.collection.insert_one(document)
        return {**document, "_id": result.inserted_id}

    async def set_current_version(
        self, project_id: ObjectId, version_id: ObjectId, status: str
    ) -> dict[str, Any] | None:
        return await self.collection.find_one_and_update(
            {"_id": project_id},
            set_current_version_update(version_id, status),
            return_document=ReturnDocument.AFTER,
        )

    async def delete(self, project_id: ObjectId) -> bool:
        result = await self.collection.delete_one({"_id": project_id})
        return result.deleted_count == 1
