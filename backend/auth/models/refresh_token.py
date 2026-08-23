import uuid
from datetime import datetime

from db.base import Base
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    LargeBinary,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)


class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )

    hashed_refresh_token: Mapped[bytes] = mapped_column(
        LargeBinary(32),
        nullable=False,
        unique=True,
    )

    ip_addr: Mapped[str | None] = mapped_column(
        String(39),
        nullable=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    replaced_by: Mapped[uuid.UUID | None] = mapped_column(
        nullable=True,
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        nullable=False,
        index=True,
    )
