import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from exceptions import VerificationCodeInvalidError
from repositories.user import UserRepository
from repositories.verification_code import EmailVerificationCodeRepository
from utils.security import hash_secret


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
