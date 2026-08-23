import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: uuid.UUID,
        token_hash: bytes,
        expires_at: datetime,
        family_id: uuid.UUID,
        ip_addr: str | None,
        user_agent: str | None,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            hashed_refresh_token=token_hash,
            expires_at=expires_at,
            family_id=family_id,
            ip_addr=ip_addr,
            user_agent=user_agent,
        )

        self.session.add(token)
        await self.session.flush()

        return token

    async def get_by_hash(
        self,
        token_hash: bytes,
    ) -> RefreshToken | None:
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.hashed_refresh_token == token_hash)
        )
        return result.scalar_one_or_none()

    async def revoke(
        self,
        token: RefreshToken,
        replaced_by: uuid.UUID | None = None,
    ) -> None:
        token.is_active = False
        token.revoked_at = datetime.now(UTC)
        token.replaced_by = replaced_by

    async def revoke_family(self, family_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id)
            .values(
                is_active=False,
                revoked_at=datetime.now(UTC),
            )
        )

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .values(
                is_active=False,
                revoked_at=datetime.now(UTC),
            )
        )
