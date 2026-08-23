import uuid
from datetime import UTC, datetime, timedelta

import pytest

from repositories.refresh_tokens import RefreshTokenRepository


@pytest.mark.asyncio
async def test_create_refresh_token(session):
    user_id = uuid.uuid4()
    repository = RefreshTokenRepository(session)

    token_hash = uuid.uuid4().bytes
    family_id = uuid.uuid4()
    expires_at = datetime.now(UTC) + timedelta(days=30)

    token = await repository.create(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
        family_id=family_id,
        ip_addr='127.0.0.1',
        user_agent='pytest',
    )

    await session.commit()

    assert token.id is not None
    assert token.user_id == user_id
    assert token.hashed_refresh_token == token_hash
    assert token.is_active is True


@pytest.mark.asyncio
async def test_get_refresh_token_by_hash(session):
    repository = RefreshTokenRepository(session)

    token_hash = uuid.uuid4().bytes

    token = await repository.create(
        user_id=uuid.uuid4(),
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=30),
        family_id=uuid.uuid4(),
        ip_addr=None,
        user_agent=None,
    )

    await session.commit()

    result = await repository.get_by_hash(token_hash)

    assert result is not None
    assert result.id == token.id


@pytest.mark.asyncio
async def test_revoke_refresh_token(session):
    repository = RefreshTokenRepository(session)

    token = await repository.create(
        user_id=uuid.uuid4(),
        token_hash=uuid.uuid4().bytes,
        expires_at=datetime.now(UTC) + timedelta(days=30),
        family_id=uuid.uuid4(),
        ip_addr=None,
        user_agent=None,
    )

    await session.commit()

    replacement_id = uuid.uuid4()

    await repository.revoke(
        token,
        replaced_by=replacement_id,
    )

    await session.commit()

    assert token.is_active is False
    assert token.revoked_at is not None
    assert token.replaced_by == replacement_id


@pytest.mark.asyncio
async def test_revoke_refresh_token_family(session):
    repository = RefreshTokenRepository(session)

    family_id = uuid.uuid4()

    token_1 = await repository.create(
        user_id=uuid.uuid4(),
        token_hash=uuid.uuid4().bytes,
        expires_at=datetime.now(UTC) + timedelta(days=30),
        family_id=family_id,
        ip_addr=None,
        user_agent=None,
    )

    token_2 = await repository.create(
        user_id=uuid.uuid4(),
        token_hash=uuid.uuid4().bytes,
        expires_at=datetime.now(UTC) + timedelta(days=30),
        family_id=family_id,
        ip_addr=None,
        user_agent=None,
    )

    await session.commit()

    await repository.revoke_family(family_id)

    await session.commit()

    await session.refresh(token_1)
    await session.refresh(token_2)

    assert token_1.is_active is False
    assert token_2.is_active is False
    assert token_1.revoked_at is not None
    assert token_2.revoked_at is not None
