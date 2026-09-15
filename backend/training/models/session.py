from datetime import datetime
from enum import StrEnum
from uuid import (
    UUID,
    uuid4,
)

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import (
    ARRAY,
    JSONB,
)
from sqlalchemy.dialects.postgresql import (
    UUID as PG_UUID,
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

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    repertoire_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    start_line_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
    )

    current_ply: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    repertoire_revision: Mapped[int] = mapped_column(
        Integer,
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
            native_enum=True,
        ),
        nullable=False,
        default=TrainingSessionStatus.ACTIVE,
    )

    error_line_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=True,
    )

    error_line_analytic_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    error_ply: Mapped[int | None] = mapped_column(
        Integer,
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
            name='ck_training_sessions_current_ply_non_negative',
        ),
        CheckConstraint(
            'repertoire_revision >= 0',
            name='ck_training_sessions_revision_non_negative',
        ),
        CheckConstraint(
            'error_ply >= 0',
            name='ck_training_sessions_error_ply_non_negative',
        ),
    )
