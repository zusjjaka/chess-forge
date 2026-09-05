import uuid
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from models.repertoire import RepertoireSide


class RepertoireCreate(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=40,
    )
    description: str = ''
    side: RepertoireSide

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class RepertoireUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=40,
    )
    description: str | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class RepertoireResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str
    side: RepertoireSide
    version: int
    created_at: datetime
    updated_at: datetime


class RepertoireListResponse(BaseModel):
    items: list[RepertoireResponse]
    page: int
    pages: int
