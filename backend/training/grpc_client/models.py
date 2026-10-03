from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class TrainingLine:
    id: UUID
    parent_id: UUID | None
    tag: str | None
    moves: list[str]
    analytic_version: int


@dataclass(slots=True)
class TrainingTree:
    repertoire_revision: int
    lines: list[TrainingLine]
