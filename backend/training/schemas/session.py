from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from models.session import TrainingSessionStatus


class TrainingSessionCreate(BaseModel):
    repertoire_id: UUID
    line_id: UUID | None = None


class TrainingMoveRequest(BaseModel):
    move: str


class TrainingSessionListItem(BaseModel):
    id: UUID
    status: TrainingSessionStatus
    created_at: datetime


class TrainingSessionListResponse(BaseModel):
    items: list[TrainingSessionListItem]
    page: int
    limit: int
    total: int


class TrainingSessionResponse(BaseModel):
    id: UUID
    repertoire_id: UUID
    line_id: UUID
    status: TrainingSessionStatus
    repertoire_version: int
    current_ply: int
    created_at: datetime
    ended_at: datetime | None
    error_line_id: UUID | None
    error_ply: int | None


class TrainingMoveResponse(BaseModel):
    correct: bool
    current_ply: int
    status: TrainingSessionStatus
