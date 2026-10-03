from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from db.base import Base


class LineTrainingStats(Base):
    __tablename__ = 'line_training_stats'

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

    line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
    )

    line_analytic_version: Mapped[int] = mapped_column(
        nullable=False,
    )

    attempts: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    fails: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    consecutive_successes: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    consecutive_failures: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    target_interval: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
    )

    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        UniqueConstraint(
            'user_id',
            'line_id',
            'line_analytic_version',
            name='uq_line_training_stats_user_line_version',
        ),
        CheckConstraint(
            'line_analytic_version >= 1',
            name='line_training_stats_version_check',
        ),
        CheckConstraint(
            'attempts >= 0',
            name='line_training_stats_attempts_check',
        ),
        CheckConstraint(
            'fails >= 0',
            name='line_training_stats_fails_check',
        ),
        CheckConstraint(
            'fails <= attempts',
            name='line_training_stats_fails_attempts_check',
        ),
        CheckConstraint(
            'consecutive_successes >= 0',
            name='line_training_stats_success_streak_check',
        ),
        CheckConstraint(
            'consecutive_failures >= 0',
            name='line_training_stats_failure_streak_check',
        ),
        CheckConstraint(
            'target_interval > 0',
            name='line_training_stats_target_interval_check',
        ),
    )
