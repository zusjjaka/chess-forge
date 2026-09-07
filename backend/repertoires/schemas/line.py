import uuid
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

UCIMove = Annotated[
    str,
    Field(
        pattern=r'^[a-h][1-8][a-h][1-8][qrbn]?$',
    ),
]


class LineCreate(BaseModel):
    tag: str | None = Field(
        default=None,
        max_length=100,
    )
    moves: list[UCIMove] = Field(
        min_length=1,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class LineUpdate(BaseModel):
    tag: str | None = Field(
        default=None,
        max_length=100,
    )
    moves: list[UCIMove] | None = Field(
        default=None,
        min_length=1,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class LineBatchCreate(BaseModel):
    line_id: uuid.UUID
    parent_id: uuid.UUID | None = None
    tag: str | None = Field(
        default=None,
        max_length=100,
    )
    moves: list[UCIMove] = Field(
        min_length=1,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class LineBatchUpdate(BaseModel):
    line_id: uuid.UUID
    tag: str | None = Field(
        default=None,
        max_length=100,
    )
    moves: list[UCIMove] | None = Field(
        default=None,
        min_length=1,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class LinePatchRequest(BaseModel):
    revision: int = Field(
        ge=1,
    )
    create: list[LineBatchCreate] = Field(
        default_factory=list,
    )
    update: list[LineBatchUpdate] = Field(
        default_factory=list,
    )
    delete: list[uuid.UUID] = Field(
        default_factory=list,
    )

    @model_validator(mode='after')
    def validate_operations(self) -> 'LinePatchRequest':
        if not self.create and not self.update and not self.delete:
            raise ValueError(
                'At least one line operation is required.',
            )

        return self


class LinePatchResponse(BaseModel):
    revision: int


class LineResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    tag: str | None
    moves: list[UCIMove]
    analytic_version: int
    children: list['LineResponse']


LineResponse.model_rebuild()
