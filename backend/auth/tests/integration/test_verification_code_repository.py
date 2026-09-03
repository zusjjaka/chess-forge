import uuid
from datetime import (
    UTC,
    datetime,
    timedelta,
)

import pytest

from models.user import User
from models.verification_code import EmailVerificationCode
from repositories.verification_code import EmailVerificationCodeRepository


@pytest.fixture
def repository(session) -> EmailVerificationCodeRepository:
    return EmailVerificationCodeRepository(session=session)


@pytest.fixture
async def user(session) -> User:
    user = User(
        email=f'{uuid.uuid4()}@example.com',
        password_hash='password-hash',
    )

    session.add(user)
    await session.flush()

    return user


@pytest.mark.asyncio
async def test_create(
    repository: EmailVerificationCodeRepository,
    user: User,
) -> None:
    code_hash = b'a' * 32
    expires_at = datetime.now(UTC) + timedelta(minutes=15)

    verification_code = await repository.create(
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    assert verification_code.id is not None
    assert verification_code.user_id == user.id
    assert verification_code.code_hash == code_hash
    assert verification_code.expires_at == expires_at
    assert verification_code.used_at is None


@pytest.mark.asyncio
async def test_get_valid_by_user_id_returns_valid_code(
    repository: EmailVerificationCodeRepository,
    user: User,
) -> None:
    code_hash = b'a' * 32
    expires_at = datetime.now(UTC) + timedelta(minutes=15)

    verification_code = await repository.create(
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    result = await repository.get_valid_by_user_id(
        user_id=user.id,
        code_hash=code_hash,
    )

    assert result is verification_code


@pytest.mark.asyncio
async def test_get_valid_by_user_id_returns_none_for_wrong_user(
    repository: EmailVerificationCodeRepository,
    user: User,
) -> None:
    code_hash = b'a' * 32
    expires_at = datetime.now(UTC) + timedelta(minutes=15)

    verification_code = await repository.create(
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    result = await repository.get_valid_by_user_id(
        user_id=uuid.uuid4(),
        code_hash=code_hash,
    )

    assert result is None
    assert verification_code.user_id == user.id


@pytest.mark.asyncio
async def test_get_valid_by_user_id_returns_none_for_wrong_code(
    repository: EmailVerificationCodeRepository,
    user: User,
) -> None:
    code_hash = b'a' * 32
    wrong_code_hash = b'b' * 32
    expires_at = datetime.now(UTC) + timedelta(minutes=15)

    await repository.create(
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    result = await repository.get_valid_by_user_id(
        user_id=user.id,
        code_hash=wrong_code_hash,
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_valid_by_user_id_returns_none_for_expired_code(
    repository: EmailVerificationCodeRepository,
    user: User,
) -> None:
    code_hash = b'a' * 32
    expires_at = datetime.now(UTC) - timedelta(minutes=1)

    await repository.create(
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    result = await repository.get_valid_by_user_id(
        user_id=user.id,
        code_hash=code_hash,
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_valid_by_user_id_returns_none_for_used_code(
    repository: EmailVerificationCodeRepository,
    user: User,
) -> None:
    code_hash = b'a' * 32
    expires_at = datetime.now(UTC) + timedelta(minutes=15)

    verification_code = await repository.create(
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    verification_code.used_at = datetime.now(UTC)
    await repository.session.flush()

    result = await repository.get_valid_by_user_id(
        user_id=user.id,
        code_hash=code_hash,
    )

    assert result is None


@pytest.mark.asyncio
async def test_mark_as_used(
    repository: EmailVerificationCodeRepository,
    user: User,
) -> None:
    code_hash = b'a' * 32
    expires_at = datetime.now(UTC) + timedelta(minutes=15)

    verification_code = await repository.create(
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    assert verification_code.used_at is None

    await repository.mark_as_used(verification_code.id)

    await repository.session.refresh(verification_code)

    assert verification_code.used_at is not None


@pytest.mark.asyncio
async def test_mark_as_used_does_not_overwrite_used_code(
    repository: EmailVerificationCodeRepository,
    user: User,
) -> None:
    code_hash = b'a' * 32
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    original_used_at = datetime.now(UTC) - timedelta(minutes=5)

    verification_code = await repository.create(
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    verification_code.used_at = original_used_at
    await repository.session.flush()

    await repository.mark_as_used(verification_code.id)

    await repository.session.refresh(verification_code)

    assert verification_code.used_at == original_used_at
