import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import VerificationCodeInvalidError
from repositories.refresh_token import RefreshTokenRepository
from repositories.user import UserRepository
from repositories.verification_code import (
    EmailVerificationCodeRepository,
    PasswordResetCodeRepository,
)
from utils.security import (
    hash_password,
    hash_secret,
)


class EmailVerificationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.codes = EmailVerificationCodeRepository(session=session)
        self.users = UserRepository(session=session)

    async def verify(self, user_id: uuid.UUID, code: str) -> None:
        code_hash = hash_secret(code)

        verification_code = await self.codes.get_valid_by_user_id(
            user_id=user_id, code_hash=code_hash
        )

        if verification_code is None:
            raise VerificationCodeInvalidError

        user = await self.users.get_by_id(user_id)

        if user is None:
            raise VerificationCodeInvalidError

        user.is_email_verified = True

        await self.codes.mark_as_used(verification_code.id)

        await self.session.commit()


class PasswordResetService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.codes = PasswordResetCodeRepository(session=session)
        self.users = UserRepository(session=session)
        self.refresh_tokens = RefreshTokenRepository(session=session)

    async def reset(self,
                    email: str,
                    code: str,
                    password: str
                    ) -> None:
        code_hash = hash_secret(code)

        user = await self.users.get_by_email(email)

        if user is None:
            raise VerificationCodeInvalidError

        reset_code = await self.codes.get_valid_by_user_id(
            user_id=user.id,
            code_hash=code_hash
        )

        if reset_code is None:
            raise VerificationCodeInvalidError

        user.password_hash = hash_password(password)

        await self.refresh_tokens.revoke_all_for_user(user.id)

        await self.codes.mark_as_used(reset_code.id)

        await self.session.commit()
