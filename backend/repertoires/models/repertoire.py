import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from core.constants import (
    LINES_MOVES_CHECK_CONSTRAINT,
    LINES_REPERTOIRE_PARENT_FK,
    UNIQUE_ROOT_CONSTRAINT,
)
from db.base import Base


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
    version: Mapped[int] = mapped_column(
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

    lines: Mapped[list['Line']] = relationship(
        back_populates='repertoire',
        cascade='all, delete-orphan',
        passive_deletes=True,
    )


class Line(Base):
    __tablename__ = 'lines'

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    repertoire_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            'repertoires.id',
            ondelete='CASCADE',
        ),
        nullable=False,
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    tag: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    moves: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
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

    repertoire: Mapped[Repertoire] = relationship(
        back_populates='lines',
    )
    parent: Mapped['Line | None'] = relationship(
        back_populates='children',
        remote_side=lambda: [Line.id],
        foreign_keys=lambda: [Line.parent_id],
    )
    children: Mapped[list['Line']] = relationship(
        back_populates='parent',
        foreign_keys=lambda: [Line.parent_id],
        cascade='all, delete-orphan',
        passive_deletes=True,
    )

    __table_args__ = (
        UniqueConstraint(
            'repertoire_id',
            'id',
            name='uq_lines_repertoire_id',
        ),
        ForeignKeyConstraint(
            ['repertoire_id', 'parent_id'],
            ['lines.repertoire_id', 'lines.id'],
            name=LINES_REPERTOIRE_PARENT_FK,
            ondelete='CASCADE',
        ),
        Index(
            UNIQUE_ROOT_CONSTRAINT,
            'repertoire_id',
            unique=True,
            postgresql_where=parent_id.is_(None),
        ),
        CheckConstraint(
            'cardinality(moves) > 0',
            name=LINES_MOVES_CHECK_CONSTRAINT,
        ),
    )
