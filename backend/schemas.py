import uuid
from datetime import datetime

from fastapi_users import schemas as fa_schemas
from pydantic import BaseModel, ConfigDict


class UserRead(fa_schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(fa_schemas.BaseUserCreate):
    pass


class UserUpdate(fa_schemas.BaseUserUpdate):
    pass


class PostResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    caption: str | None
    url: str
    file_type: str
    file_name: str
    created_at: datetime
