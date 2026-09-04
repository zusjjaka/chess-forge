import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.refresh_token import RefreshToken
from models.user import User
from repositories.refresh_token import RefreshTokenRepository
from repositories.user import UserRepository


@pytest.mark.asyncio
async def test_create_refresh_token(
    session: AsyncSession,
) -> None:
    users = UserRepository(session)
    refresh_tokens = RefreshTokenRepository(session)

    user = await users.create(
        email='user@example.com',
        password_hash='hashed-password',
    )

    token_hash = b'a' * 32
    expires_at = datetime.now(UTC) + timedelta(days=7)
    family_id = uuid.uuid4()

    token = await refresh_tokens.create(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        family_id=family_id,
        ip_addr='127.0.0.1',
        user_agent='pytest',
    )

    assert token.id is not None
    assert token.user_id == user.id
    assert token.hashed_refresh_token == token_hash
    assert token.expires_at == expires_at
    assert token.family_id == family_id
    assert token.ip_addr == '127.0.0.1'
    assert token.user_agent == 'pytest'
    assert token.is_active is True
    assert token.revoked_at is None
    assert token.replaced_by is None


@pytest.mark.asyncio
async def test_get_by_hash(
    session: AsyncSession,
) -> None:
    users = UserRepository(session)
    refresh_tokens = RefreshTokenRepository(session)

    user = await users.create(
        email='user@example.com',
        password_hash='hashed-password',
    )

    token_hash = b'b' * 32

    token = await refresh_tokens.create(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        family_id=uuid.uuid4(),
        ip_addr=None,
        user_agent=None,
    )

    await session.commit()

    result = await refresh_tokens.get_by_hash(token_hash)

    assert result is not None
    assert result.id == token.id
    assert result.user_id == user.id
    assert result.hashed_refresh_token == token_hash


@pytest.mark.asyncio
async def test_get_by_hash_returns_none_for_unknown_hash(
    session: AsyncSession,
) -> None:
    refresh_tokens = RefreshTokenRepository(session)

    result = await refresh_tokens.get_by_hash(b'c' * 32)

    assert result is None


@pytest.mark.asyncio
async def test_revoke_refresh_token(
    session: AsyncSession,
) -> None:
    users = UserRepository(session)
    refresh_tokens = RefreshTokenRepository(session)

    user = await users.create(
        email='user@example.com',
        password_hash='hashed-password',
    )

    token = await refresh_tokens.create(
        user_id=user.id,
        token_hash=b'd' * 32,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        family_id=uuid.uuid4(),
        ip_addr=None,
        user_agent=None,
    )

    await refresh_tokens.revoke(token)

    assert token.is_active is False
    assert token.revoked_at is not None
    assert token.replaced_by is None


@pytest.mark.asyncio
async def test_revoke_refresh_token_with_replacement(
    session: AsyncSession,
) -> None:
    users = UserRepository(session)
    refresh_tokens = RefreshTokenRepository(session)

    user = await users.create(
        email='user@example.com',
        password_hash='hashed-password',
    )

    token = await refresh_tokens.create(
        user_id=user.id,
        token_hash=b'e' * 32,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        family_id=uuid.uuid4(),
        ip_addr=None,
        user_agent=None,
    )

    replacement_id = uuid.uuid4()

    await refresh_tokens.revoke(
        token,
        replaced_by=replacement_id,
    )

    assert token.is_active is False
    assert token.revoked_at is not None
    assert token.replaced_by == replacement_id


@pytest.mark.asyncio
async def test_revoke_family(
    session: AsyncSession,
) -> None:
    users = UserRepository(session)
    refresh_tokens = RefreshTokenRepository(session)

    user = await users.create(
        email='user@example.com',
        password_hash='hashed-password',
    )

    family_id = uuid.uuid4()

    token_1 = await refresh_tokens.create(
        user_id=user.id,
        token_hash=b'f' * 32,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        family_id=family_id,
        ip_addr=None,
        user_agent=None,
    )

    token_2 = await refresh_tokens.create(
        user_id=user.id,
        token_hash=b'g' * 32,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        family_id=family_id,
        ip_addr=None,
        user_agent=None,
    )

    other_token = await refresh_tokens.create(
        user_id=user.id,
        token_hash=b'h' * 32,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        family_id=uuid.uuid4(),
        ip_addr=None,
        user_agent=None,
    )

    await refresh_tokens.revoke_family(family_id)

    await session.commit()

    assert token_1.is_active is False
    assert token_2.is_active is False
    assert other_token.is_active is True


@pytest.mark.asyncio
async def test_revoke_all_for_user(
    session: AsyncSession,
) -> None:
    first_user = User(
        email='first@example.com',
        password_hash='hashed-password',
    )

    second_user = User(
        email='second@example.com',
        password_hash='hashed-password',
    )

    session.add_all([first_user, second_user])
    await session.flush()

    first_token = RefreshToken(
        user_id=first_user.id,
        hashed_refresh_token=b'a' * 32,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        family_id=uuid.uuid4(),
    )

    second_token = RefreshToken(
        user_id=first_user.id,
        hashed_refresh_token=b'b' * 32,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        family_id=uuid.uuid4(),
    )

    other_user_token = RefreshToken(
        user_id=second_user.id,
        hashed_refresh_token=b'c' * 32,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        family_id=uuid.uuid4(),
    )

    session.add_all([
        first_token,
        second_token,
        other_user_token,
    ])

    await session.commit()

    repository = RefreshTokenRepository(session)

    await repository.revoke_all_for_user(first_user.id)

    await session.refresh(first_token)
    await session.refresh(second_token)
    await session.refresh(other_user_token)

    assert first_token.is_active is False
    assert second_token.is_active is False
    assert other_user_token.is_active is True
