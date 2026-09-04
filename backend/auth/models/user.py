import enum
import uuid
from datetime import (
    date,
    datetime,
)

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from db.base import Base


class Gender(enum.Enum):
    MALE = 'M'
    FEMALE = 'F'


class User(Base):
    """User model."""

    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(254),
        unique=True,
        index=True,
        nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    display_name: Mapped[str] = mapped_column(
        String(25),
        nullable=True
    )
    gender: Mapped[Gender | None] = mapped_column(
        Enum(
            Gender,
            name='gender',
            values_callable=lambda enum: [item.value for item in enum],
        ),
        nullable=True,
    )
    country: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True,
    )
    birth_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )
    bio: Mapped[str | None] = mapped_column(
        String(75),
        nullable=True,
    )
    telegram_alias: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
