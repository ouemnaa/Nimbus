from bson import ObjectId

from app.core.errors import InvalidObjectIdError


def parse_object_id(value: str, field_name: str = "id") -> ObjectId:
    if not ObjectId.is_valid(value):
        raise InvalidObjectIdError(field_name)
    return ObjectId(value)


def stringify_object_id(value: ObjectId | None) -> str | None:
    return str(value) if value is not None else None
