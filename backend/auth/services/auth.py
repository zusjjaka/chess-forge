import uuid
from datetime import (
    UTC,
    datetime,
    timedelta,
)

from fastapi import (
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from models.user import User
from repositories.refresh_tokens import RefreshTokenRepository
from repositories.users import UserRepository
from utils.security import (
    hash_password,
    verify_password,
)
from utils.tokens import (
    create_access_token,
    generate_refresh_token,
    hash_refresh_token,
)

settings = get_settings()


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)
        self.session = session

    async def register(
        self,
        email: str,
        password: str,
    ) -> User:
        existing_user = await self.users.get_by_email(email)

        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='User already exists',
            )

        user = await self.users.create(
            email=email,
            password_hash=hash_password(password),
        )

        await self.session.commit()

        return user

    async def login(
        self,
        email: str,
        password: str,
        ip_addr: str | None,
        user_agent: str | None,
    ) -> tuple[str, str]:
        user = await self.users.get_by_email(email)

        if user is None or not verify_password(
            password,
            user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid credentials',
            )

        access_token = create_access_token(user.id)

        refresh_token = generate_refresh_token()

        expires_at = datetime.now(UTC) + timedelta(
            seconds=settings.refresh_token_expire_seconds
        )

        await self.refresh_tokens.create(
            user_id=user.id,
            token_hash=hash_refresh_token(refresh_token),
            expires_at=expires_at,
            family_id=uuid.uuid4(),
            ip_addr=ip_addr,
            user_agent=user_agent,
        )

        await self.session.commit()

        return access_token, refresh_token

    async def refresh(
        self,
        refresh_token: str,
        ip_addr: str | None,
        user_agent: str | None,
    ) -> tuple[str, str]:
        token_hash = hash_refresh_token(refresh_token)

        stored_token = await self.refresh_tokens.get_by_hash(token_hash)

        if stored_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Invalid refresh token',
            )

        if not stored_token.is_active:
            await self.refresh_tokens.revoke_family(stored_token.family_id)
            await self.session.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Refresh token reuse detected',
            )

        if stored_token.expires_at <= datetime.now(UTC):
            await self.refresh_tokens.revoke(stored_token)
            await self.session.commit()

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail='Refresh token expired',
            )

        new_refresh_token = generate_refresh_token()

        new_token = await self.refresh_tokens.create(
            user_id=stored_token.user_id,
            token_hash=hash_refresh_token(new_refresh_token),
            expires_at=datetime.now(UTC)
            + timedelta(seconds=settings.refresh_token_expire_seconds),
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
