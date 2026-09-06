import uuid
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
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


class LineTreeReplace(BaseModel):
    tag: str | None = Field(
        default=None,
        max_length=100,
    )
    moves: list[UCIMove] = Field(
        min_length=1,
    )
    children: list['LineTreeReplace'] = Field(
        default_factory=list,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


class LineResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
    )

    id: uuid.UUID
    tag: str | None
    moves: list[UCIMove]
    analytic_version: int
    children: list['LineResponse']


class LineTreeReplaceRequest(BaseModel):
    revision: int = Field(
        ge=1,
    )
    tree: LineTreeReplace


LineTreeReplace.model_rebuild()
LineResponse.model_rebuild()
