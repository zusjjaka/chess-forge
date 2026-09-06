from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    String,
    Text,
    func,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from db.base import Base

if TYPE_CHECKING:
    from models.line import Line


class RepertoireSide(Enum):
    WHITE = 'white'
    BLACK = 'black'


class Repertoire(Base):
    __tablename__ = 'repertoires'

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
    name: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='',
    )
    side: Mapped[RepertoireSide] = mapped_column(
        SQLEnum(
            RepertoireSide,
            name='repertoire_side',
            values_callable=lambda enum_cls: [
                member.value for member in enum_cls
            ],
        ),
        nullable=False,
    )
    revision: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
    )
    analytic_version: Mapped[int] = mapped_column(
        nullable=False,
        default=1,
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

    lines: Mapped[list[Line]] = relationship(
        back_populates='repertoire',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )
