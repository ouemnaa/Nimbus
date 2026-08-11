from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING

from app.models.terraform_generation import COLLECTION_NAME


class TerraformGenerationRepository:
    def __init__(self, database: AsyncIOMotorDatabase[Any]) -> None:
        self.collection = database[COLLECTION_NAME]

    async def create(self, document: dict[str, Any]) -> dict[str, Any]:
        result = await self.collection.insert_one(document)
        return {**document, "_id": result.inserted_id}

    async def latest_for_project(
        self, project_id: ObjectId
    ) -> dict[str, Any] | None:
        return await self.collection.find_one(
            {"projectId": project_id},
            sort=[("createdAt", DESCENDING)],
        )

    async def delete_for_project(self, project_id: ObjectId) -> int:
        result = await self.collection.delete_many({"projectId": project_id})
        return result.deleted_count
