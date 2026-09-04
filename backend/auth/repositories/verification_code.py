import uuid
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
    EmailChangeCode,
    EmailVerificationCode,
    PasswordResetCode,
)


class BaseVerificationCodeRepository[T: BaseVerificationCode]:
    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_valid_by_user_id(self,
                                   user_id: uuid.UUID,
                                   code_hash: bytes
                                   ) -> T | None:
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


class BaseVerificationCodeCreateRepository[T: BaseVerificationCode]:
    model: type[T]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self,
                     user_id: uuid.UUID,
                     code_hash: bytes,
                     expires_at: datetime
                     ) -> T:
        code = self.model(
            user_id=user_id,
            code_hash=code_hash,
            expires_at=expires_at,
        )

        self.session.add(code)
        await self.session.flush()

        return code


class EmailVerificationCodeRepository(
    BaseVerificationCodeRepository[EmailVerificationCode],
    BaseVerificationCodeCreateRepository[EmailVerificationCode],
):
    model = EmailVerificationCode


class PasswordResetCodeRepository(
    BaseVerificationCodeRepository[PasswordResetCode],
    BaseVerificationCodeCreateRepository[PasswordResetCode],
):
    model = PasswordResetCode


class EmailChangeCodeRepository(
    BaseVerificationCodeRepository[EmailChangeCode],
):
    model = EmailChangeCode

    async def create(self,
                     user_id: uuid.UUID,
                     new_email: str,
                     code_hash: bytes,
                     expires_at: datetime
                     ) -> EmailChangeCode:
        code = self.model(
            user_id=user_id,
            new_email=new_email,
            code_hash=code_hash,
            expires_at=expires_at
        )

        self.session.add(code)
        await self.session.flush()

        return code
