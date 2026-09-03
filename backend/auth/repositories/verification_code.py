import uuid
from abc import ABC, abstractmethod
from datetime import (
    UTC,
    datetime,
)

from sqlalchemy import (
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from models.verification_code import (
    BaseVerificationCode,
    EmailVerificationCode,
)


class BaseVerificationCodeRepository(ABC):
    model: type[BaseVerificationCode]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @abstractmethod
    async def create(self,
                     user_id: uuid.UUID,
                     code_hash: bytes,
                     expires_at: datetime
                     ) -> BaseVerificationCode:
        raise NotImplementedError

    async def get_valid_by_user_id(self,
                                   user_id: uuid.UUID,
                                   code_hash: bytes
                                   ) -> BaseVerificationCode | None:
        result = await self.session.execute(
            select(self.model).where(
                self.model.user_id == user_id,
                self.model.code_hash == code_hash,
                self.model.used_at.is_(None),
                self.model.expires_at > datetime.now(UTC),
            )
        )

        return result.scalar_one_or_none()

    async def mark_as_used(self, code_id: uuid.UUID) -> None:
        await self.session.execute(
            update(self.model)
            .where(
                self.model.id == code_id,
                self.model.used_at.is_(None),
            )
            .values(
                used_at=datetime.now(UTC),
            )
        )
        await self.session.flush()


class EmailVerificationCodeRepository(BaseVerificationCodeRepository):
    model = EmailVerificationCode

    async def create(self,
                     user_id: uuid.UUID,
                     code_hash: bytes,
                     expires_at: datetime
                     ) -> EmailVerificationCode:
        verification_code = self.model(
            user_id=user_id,
            code_hash=code_hash,
            expires_at=expires_at,
        )

        self.session.add(verification_code)
        await self.session.flush()

        return verification_code
