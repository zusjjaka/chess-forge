from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Index,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    JSONB,
    UUID,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from db.base import Base


class TrainingSessionStatus(StrEnum):
    ACTIVE = 'active'
    PASSED = 'passed'
    FAILED = 'failed'
    INVALIDATED = 'invalidated'


class TrainingSession(Base):
    __tablename__ = 'training_sessions'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    repertoire_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    start_line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    current_ply: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    repertoire_revision: Mapped[int] = mapped_column(
        nullable=False,
    )

    selected_moves: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        nullable=False,
    )

    selected_path: Mapped[list[dict[str, str | int]]] = mapped_column(
        JSONB,
        nullable=False,
    )

    status: Mapped[TrainingSessionStatus] = mapped_column(
        Enum(
            TrainingSessionStatus,
            name='training_session_status',
        ),
        nullable=False,
        default=TrainingSessionStatus.ACTIVE,
    )

    error_line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    error_line_analytic_version: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    error_ply: Mapped[int | None] = mapped_column(
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            'current_ply >= 0',
            name='training_sessions_current_ply_check',
        ),
        CheckConstraint(
            'repertoire_revision >= 0',
            name='training_sessions_repertoire_revision_check',
        ),
        CheckConstraint(
            'error_ply >= 0',
            name='training_sessions_error_ply_check',
        ),
        Index(
            'ix_training_sessions_user_created_at',
            'user_id',
            'created_at',
        ),
    )
