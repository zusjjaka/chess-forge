from datetime import (
    datetime,
    timedelta,
)
from uuid import (
    UUID,
)

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Integer,
    Interval,
)
from sqlalchemy.dialects.postgresql import (
    UUID as PG_UUID,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from db.base import Base


class LineTrainingStats(Base):
    __tablename__ = 'line_training_stats'

    line_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )

    line_analytic_version: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    fails: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    last_attempt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    consecutive_successes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    consecutive_failures: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    target_interval: Mapped[timedelta] = mapped_column(
        Interval,
        nullable=False,
        default=timedelta(days=1),
    )

    __table_args__ = (
        CheckConstraint(
            'line_analytic_version >= 1',
            name='ck_line_training_stats_analytic_version_positive',
        ),
        CheckConstraint(
            'attempts >= 0',
            name='ck_line_training_stats_attempts_non_negative',
        ),
        CheckConstraint(
            'fails >= 0',
            name='ck_line_training_stats_fails_non_negative',
        ),
        CheckConstraint(
            'fails <= attempts',
            name='ck_line_training_stats_fails_lte_attempts',
        ),
        CheckConstraint(
            'consecutive_successes >= 0',
            name='ck_line_training_stats_success_streak_non_negative',
        ),
        CheckConstraint(
            'consecutive_failures >= 0',
            name='ck_line_training_stats_failure_streak_non_negative',
        ),
        CheckConstraint(
            'target_interval > INTERVAL \'0 seconds\'',
            name='ck_line_training_stats_target_interval_positive',
        ),
    )
