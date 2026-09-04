import uuid

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from repositories.user import UserRepository


@pytest.mark.asyncio
async def test_create_user(session: AsyncSession) -> None:
    repository = UserRepository(session)

    user = await repository.create(
        email='user@example.com',
        password_hash='hashed-password',
    )

    assert user.id is not None
    assert user.email == 'user@example.com'
    assert user.password_hash == 'hashed-password'


@pytest.mark.asyncio
async def test_get_user_by_id(session: AsyncSession) -> None:
    repository = UserRepository(session)

    user = await repository.create(
        email='user@example.com',
        password_hash='hashed-password',
    )

    await session.commit()

    result = await repository.get_by_id(user.id)

    assert result is not None
    assert result.id == user.id
    assert result.email == 'user@example.com'


@pytest.mark.asyncio
async def test_get_user_by_email(session: AsyncSession) -> None:
    repository = UserRepository(session)

    user = await repository.create(
        email='user@example.com',
        password_hash='hashed-password',
    )

    await session.commit()

    result = await repository.get_by_email('user@example.com')

    assert result is not None
    assert result.id == user.id


@pytest.mark.asyncio
async def test_get_user_by_id_returns_none_for_unknown_user(
    session: AsyncSession,
) -> None:
    repository = UserRepository(session)

    result = await repository.get_by_id(uuid.uuid4())

    assert result is None


@pytest.mark.asyncio
async def test_get_user_by_email_returns_none_for_unknown_email(
    session: AsyncSession,
) -> None:
    repository = UserRepository(session)

    result = await repository.get_by_email('unknown@example.com')

    assert result is None


@pytest.mark.asyncio
async def test_create_user_with_duplicate_email(
    session: AsyncSession,
) -> None:
    repository = UserRepository(session)

    await repository.create(
        email='user@example.com',
        password_hash='hashed-password',
    )
    await session.commit()

    with pytest.raises(IntegrityError):
        await repository.create(
            email='user@example.com',
            password_hash='another-password',
        )

    await session.rollback()


@pytest.mark.asyncio
async def test_create_user_defaults(session: AsyncSession) -> None:
    repository = UserRepository(session)

    user = await repository.create(
        email='user@example.com',
        password_hash='hashed-password',
    )

    await session.commit()

    assert user.is_email_verified is False
    assert user.created_at is not None


@pytest.mark.asyncio
async def test_update_user(session: AsyncSession) -> None:
    repository = UserRepository(session)

    user = await repository.create(
        email='user@example.com',
        password_hash='hashed-password',
    )

    await session.commit()

    data = {
        'display_name': 'Updated User',
        'country': 'KZ',
        'bio': 'Updated bio',
    }

    result = await repository.update(
        user=user,
        data=data,
    )

    await session.commit()

    assert result is user
    assert user.display_name == 'Updated User'
    assert user.country == 'KZ'
    assert user.bio == 'Updated bio'

    refreshed_user = await repository.get_by_id(user.id)

    assert refreshed_user is not None
    assert refreshed_user.display_name == 'Updated User'
    assert refreshed_user.country == 'KZ'
    assert refreshed_user.bio == 'Updated bio'
