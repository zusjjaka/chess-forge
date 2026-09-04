import uuid
from datetime import (
    UTC,
    datetime,
)

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from exceptions import (
    EmailSameError,
    InvalidCredentialsError,
    PasswordInvalidError,
    RefreshTokenExpiredError,
    RefreshTokenInvalidError,
    RefreshTokenReuseError,
    UserAlreadyExistError,
)
from models.user import User
from publishers.email import EmailPublisher
from repositories.refresh_token import RefreshTokenRepository
from repositories.user import UserRepository
from repositories.verification_code import (
    EmailChangeCodeRepository,
    EmailVerificationCodeRepository,
    PasswordResetCodeRepository,
)
from utils.security import (
    hash_password,
    hash_secret,
    verify_password,
)
from utils.tokens import (
    create_access_token,
    generate_refresh_token,
    generate_verification_code,
)

settings = get_settings()


class AuthService:
    def __init__(self, session: AsyncSession, email_publisher: EmailPublisher) -> None:
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.email_codes = EmailVerificationCodeRepository(session=session)
        self.email_change_codes = EmailChangeCodeRepository(session=session)
        self.passw_codes = PasswordResetCodeRepository(session=session)
        self.email_publisher = email_publisher
        self.session = session

    async def register(self, email: str, password: str) -> User:
        password_hash = hash_password(password)
        code = generate_verification_code()
        now = datetime.now(UTC)

        existing_user = await self.users.get_by_email(email)

        if existing_user:
            if existing_user.is_email_verified:
                raise UserAlreadyExistError(email=email)

            existing_user.password_hash = password_hash
            user = existing_user

        else:
            user = await self.users.create(
                email=email,
                password_hash=password_hash,
            )

        verification_code = await self.email_codes.create(
            user_id=user.id,
            code_hash=hash_secret(code),
            expires_at=now + settings.verification_code_lifetime,
        )

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise UserAlreadyExistError(email=email) from None

        await self.email_publisher.publish_email_verification(
            email=user.email, code=code, message_id=verification_code.id
        )

        return user

    async def login(self,
                    email: str,
                    password: str,
                    ip_addr: str | None,
                    user_agent: str | None
                    ) -> tuple[str, str]:
        user = await self.users.get_by_email(email)

        if user is None or not verify_password(
            password=password, password_hash=user.password_hash
        ):
            raise InvalidCredentialsError

        access_token = create_access_token(user.id)
        refresh_token = generate_refresh_token()

        await self.refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_secret(refresh_token),
            expires_at=datetime.now(UTC) + settings.refresh_token_lifetime,
            family_id=uuid.uuid4(),
            ip_addr=ip_addr,
            user_agent=user_agent,
        )

        await self.session.commit()

        return access_token, refresh_token

    async def refresh(self,
                      refresh_token: str,
                      ip_addr: str | None,
                      user_agent: str | None
                      ) -> tuple[str, str]:
        token_hash = hash_secret(refresh_token)

        stored_token = await self.refresh_tokens.get_by_hash(token_hash)

        if stored_token is None:
            raise RefreshTokenInvalidError

        if not stored_token.is_active:
            await self.refresh_tokens.revoke_family(stored_token.family_id)
            await self.session.commit()

            raise RefreshTokenReuseError

        if stored_token.expires_at <= datetime.now(UTC):
            await self.refresh_tokens.revoke(stored_token)
            await self.session.commit()

            raise RefreshTokenExpiredError

        new_refresh_token = generate_refresh_token()

        new_token = await self.refresh_tokens.create(
            user_id=stored_token.user_id,
            token_hash=hash_secret(new_refresh_token),
            expires_at=datetime.now(UTC) + settings.refresh_token_lifetime,
            family_id=stored_token.family_id,
            ip_addr=ip_addr,
            user_agent=user_agent,
        )

        await self.refresh_tokens.revoke(
            stored_token,
            replaced_by=new_token.id,
        )

        access_token = create_access_token(stored_token.user_id)

        await self.session.commit()

        return access_token, new_refresh_token

    async def logout(self, refresh_token: str | None) -> None:
        if refresh_token is None:
            return

        token_hash = hash_secret(refresh_token)

        stored_token = await self.refresh_tokens.get_by_hash(token_hash)

        if stored_token is None:
            return

        await self.refresh_tokens.revoke(stored_token)
        await self.session.commit()

    async def logout_all(self, user_id: uuid.UUID) -> None:
        await self.refresh_tokens.revoke_all_for_user(user_id)
        await self.session.commit()

    async def request_password_reset(self,
                                     email: str
                                     ) -> None:
        user = await self.users.get_by_email(email)

        if user is None:
            return

        code = generate_verification_code()
        code_hash = hash_secret(code)
        now = datetime.now(UTC)

        reset_code = await self.passw_codes.create(
            user_id=user.id,
            code_hash=code_hash,
            expires_at=now + settings.verification_code_lifetime
        )

        await self.session.commit()

        await self.email_publisher.publish_password_reset(
            email=user.email,
            code=code,
            message_id=reset_code.id
        )

    async def change_user_password(self,
                                   user_id: uuid.UUID,
                                   current_password: str,
                                   new_password: str
                                   ) -> None:
        user = await self.users.get_by_id(user_id)

        if user is None:
            raise PasswordInvalidError

        if not verify_password(current_password, user.password_hash):
            raise PasswordInvalidError

        user.password_hash = hash_password(new_password)

        await self.session.commit()


    async def request_email_change(self,
                                user_id: uuid.UUID,
                                new_email: str,
                                password: str
                                ) -> None:
        user = await self.users.get_by_id(user_id)

        if user is None:
            raise PasswordInvalidError

        if not verify_password(password, user.password_hash):
            raise PasswordInvalidError

        if user.email == new_email:
            raise EmailSameError

        existing_user = await self.users.get_by_email(new_email)

        if existing_user is not None:
            raise UserAlreadyExistError(email=new_email)

        code = generate_verification_code()
        code_hash = hash_secret(code)
        now = datetime.now(UTC)

        email_change_code = await self.email_change_codes.create(
            user_id=user.id,
            new_email=new_email,
            code_hash=code_hash,
            expires_at=now + settings.verification_code_lifetime,
        )

        await self.session.commit()

        await self.email_publisher.publish_email_change(
            email=new_email,
            code=code,
            message_id=email_change_code.id,
        )
