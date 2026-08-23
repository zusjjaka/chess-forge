import uuid

import pytest

from repositories.users import UserRepository


@pytest.mark.asyncio
async def test_create_user(session):
    repository = UserRepository(session)

    user = await repository.create(
        email=f'{uuid.uuid4()}@example.com',
        password_hash='hashed_password',
    )

    await session.commit()

    assert user.id is not None
    assert user.password_hash == 'hashed_password'


@pytest.mark.asyncio
async def test_get_user_by_email(session):
    repository = UserRepository(session)

    email = f'{uuid.uuid4()}@example.com'

    await repository.create(
        email=email,
        password_hash='hashed_password',
    )

    await session.commit()

    user = await repository.get_by_email(email)

    assert user is not None
    assert user.email == email


@pytest.mark.asyncio
async def test_get_user_by_id(session):
    repository = UserRepository(session)

    user = await repository.create(
        email=f'{uuid.uuid4()}@example.com',
        password_hash='hashed_password',
    )

    await session.commit()

    result = await repository.get_by_id(user.id)

    assert result is not None
    assert result.id == user.id


@pytest.mark.asyncio
async def test_get_nonexistent_user(session):
    repository = UserRepository(session)

    result = await repository.get_by_id(uuid.uuid4())

    assert result is None
