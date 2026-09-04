import uuid
from datetime import (
    UTC,
    datetime,
    timedelta,
)

import pytest

from models.user import User
from models.verification_code import (
    EmailChangeCode,
    EmailVerificationCode,
    PasswordResetCode,
)
from repositories.verification_code import (
    EmailChangeCodeRepository,
    EmailVerificationCodeRepository,
    PasswordResetCodeRepository,
)


@pytest.fixture
def email_change_repository(session) -> EmailChangeCodeRepository:
    return EmailChangeCodeRepository(session=session)


@pytest.fixture
def password_reset_repository(session) -> PasswordResetCodeRepository:
    return PasswordResetCodeRepository(session=session)


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


@pytest.mark.asyncio
async def test_password_reset_repository(
    password_reset_repository: PasswordResetCodeRepository,
    user: User,
) -> None:
    code_hash = b'a' * 32
    expires_at = datetime.now(UTC) + timedelta(minutes=15)

    reset_code = await password_reset_repository.create(
        user_id=user.id,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    assert isinstance(reset_code, PasswordResetCode)
    assert reset_code.user_id == user.id
    assert reset_code.code_hash == code_hash
    assert reset_code.expires_at == expires_at
    assert reset_code.used_at is None

    result = await password_reset_repository.get_valid_by_user_id(
        user_id=user.id,
        code_hash=code_hash,
    )

    assert result is reset_code

    await password_reset_repository.mark_as_used(
        reset_code.id,
    )

    await password_reset_repository.session.refresh(reset_code)

    assert reset_code.used_at is not None


@pytest.mark.asyncio
async def test_email_change_repository_create(
    email_change_repository: EmailChangeCodeRepository,
    user: User,
) -> None:
    code_hash = b'a' * 32
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    new_email = f'{uuid.uuid4()}@example.com'

    email_change_code = await email_change_repository.create(
        user_id=user.id,
        new_email=new_email,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    assert isinstance(email_change_code, EmailChangeCode)
    assert email_change_code.id is not None
    assert email_change_code.user_id == user.id
    assert email_change_code.new_email == new_email
    assert email_change_code.code_hash == code_hash
    assert email_change_code.expires_at == expires_at
    assert email_change_code.used_at is None


@pytest.mark.asyncio
async def test_email_change_repository_get_valid_by_user_id(
    email_change_repository: EmailChangeCodeRepository,
    user: User,
) -> None:
    code_hash = b'a' * 32
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    new_email = f'{uuid.uuid4()}@example.com'

    email_change_code = await email_change_repository.create(
        user_id=user.id,
        new_email=new_email,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    result = await email_change_repository.get_valid_by_user_id(
        user_id=user.id,
        code_hash=code_hash,
    )

    assert result is email_change_code
    assert result.new_email == new_email


@pytest.mark.asyncio
async def test_email_change_repository_mark_as_used(
    email_change_repository: EmailChangeCodeRepository,
    user: User,
) -> None:
    code_hash = b'a' * 32
    expires_at = datetime.now(UTC) + timedelta(minutes=15)
    new_email = f'{uuid.uuid4()}@example.com'

    email_change_code = await email_change_repository.create(
        user_id=user.id,
        new_email=new_email,
        code_hash=code_hash,
        expires_at=expires_at,
    )

    assert email_change_code.used_at is None

    await email_change_repository.mark_as_used(
        email_change_code.id,
    )

    await email_change_repository.session.refresh(email_change_code)

    assert email_change_code.used_at is not None
