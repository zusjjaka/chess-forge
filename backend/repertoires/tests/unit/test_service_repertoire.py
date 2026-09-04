import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from exceptions import RepertoireNotFoundError
from models.repertoire import (
    Repertoire,
    RepertoireSide,
)
from schemas.repertoire import (
    RepertoireCreate,
    RepertoireUpdate,
)
from services.repertoire import (
    PAGE_SIZE,
    RepertoireService,
)


@pytest.fixture
def session() -> MagicMock:
    session = MagicMock()

    transaction = MagicMock()
    transaction.__aenter__ = AsyncMock()
    transaction.__aexit__ = AsyncMock(return_value=False)

    session.begin.return_value = transaction
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.flush = AsyncMock()
    session.delete = AsyncMock()

    return session


@pytest.fixture
def service(
        session: MagicMock,
        ) -> RepertoireService:
    service = RepertoireService(session)

    service.repertoire_repository.create = AsyncMock(
        side_effect=lambda repertoire: repertoire,
    )
    service.repertoire_repository.delete = AsyncMock()
    service.repertoire_repository.get_by_id = AsyncMock()
    service.repertoire_repository.get_by_id_for_user = AsyncMock()
    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock()
    service.repertoire_repository.get_page_for_user = AsyncMock()
    service.repertoire_repository.update_version = AsyncMock(
        return_value=True,
    )

    service.line_repository.create = AsyncMock(
        side_effect=lambda line: line,
    )

    return service


@pytest.mark.asyncio
async def test_create_creates_repertoire_and_root(
        service: RepertoireService,
        ) -> None:
    user_id = uuid.uuid4()

    data = RepertoireCreate(
        name='Italian Game',
        description='King pawn opening',
        side=RepertoireSide.WHITE,
        root_moves=['e2e4'],
    )

    result = await service.create(
        user_id,
        data,
    )

    assert result.user_id == user_id
    assert result.name == 'Italian Game'
    assert result.description == 'King pawn opening'
    assert result.side == RepertoireSide.WHITE
    assert result.version == 1

    service.repertoire_repository.create.assert_awaited_once()

    repertoire = (
        service.repertoire_repository.create
        .await_args
        .args[0]
    )

    assert repertoire.user_id == user_id
    assert repertoire.name == 'Italian Game'
    assert repertoire.description == 'King pawn opening'
    assert repertoire.side == RepertoireSide.WHITE
    assert repertoire.version == 1

    service.line_repository.create.assert_awaited_once()

    root = (
        service.line_repository.create
        .await_args
        .args[0]
    )

    assert root.repertoire_id == repertoire.id
    assert root.parent_id is None
    assert root.moves == ['e2e4']


@pytest.mark.asyncio
async def test_create_uses_default_description(
        service: RepertoireService,
        ) -> None:
    data = RepertoireCreate(
        name='Sicilian Defense',
        side=RepertoireSide.BLACK,
        root_moves=['e2e4', 'c7c5'],
    )

    result = await service.create(
        uuid.uuid4(),
        data,
    )

    assert result.description == ''


@pytest.mark.asyncio
async def test_get_returns_users_repertoire(
        service: RepertoireService,
        ) -> None:
    repertoire = Repertoire(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name='Italian Game',
        description='',
        side=RepertoireSide.WHITE,
        version=1,
    )

    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )

    result = await service.get(
        repertoire.id,
        repertoire.user_id,
    )

    assert result is repertoire

    service.repertoire_repository.get_by_id_for_user.assert_awaited_once_with(
        repertoire.id,
        repertoire.user_id,
    )


@pytest.mark.asyncio
async def test_get_raises_when_repertoire_does_not_exist(
        service: RepertoireService,
        ) -> None:
    repertoire_id = uuid.uuid4()
    user_id = uuid.uuid4()

    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=None,
    )

    with pytest.raises(RepertoireNotFoundError):
        await service.get(
            repertoire_id,
            user_id,
        )


@pytest.mark.asyncio
async def test_list_returns_items_and_pagination(
        service: RepertoireService,
        ) -> None:
    user_id = uuid.uuid4()

    items = [
        Repertoire(
            id=uuid.uuid4(),
            user_id=user_id,
            name='First',
            description='',
            side=RepertoireSide.WHITE,
            version=1,
        ),
        Repertoire(
            id=uuid.uuid4(),
            user_id=user_id,
            name='Second',
            description='',
            side=RepertoireSide.BLACK,
            version=1,
        ),
    ]

    service.repertoire_repository.get_page_for_user = AsyncMock(
        return_value=(items, 42),
    )

    result = await service.list(
        user_id,
        page=2,
    )

    assert result == (
        items,
        2,
        3,
    )

    service.repertoire_repository.get_page_for_user.assert_awaited_once_with(
        user_id,
        PAGE_SIZE,
        PAGE_SIZE,
    )


@pytest.mark.asyncio
async def test_list_calculates_single_page_for_empty_result(
        service: RepertoireService,
        ) -> None:
    user_id = uuid.uuid4()

    service.repertoire_repository.get_page_for_user = AsyncMock(
        return_value=([], 0),
    )

    result = await service.list(
        user_id,
        page=1,
    )

    assert result == (
        [],
        1,
        1,
    )


@pytest.mark.asyncio
async def test_list_calculates_pages_with_remainder(
        service: RepertoireService,
        ) -> None:
    user_id = uuid.uuid4()

    service.repertoire_repository.get_page_for_user = AsyncMock(
        return_value=([], 21),
    )

    result = await service.list(
        user_id,
        page=2,
    )

    assert result == (
        [],
        2,
        2,
    )


@pytest.mark.asyncio
async def test_update_changes_name(
        service: RepertoireService,
        ) -> None:
    repertoire = Repertoire(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name='Old name',
        description='Description',
        side=RepertoireSide.WHITE,
        version=1,
    )

    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )

    data = RepertoireUpdate(
        name='New name',
    )

    result = await service.update(
        repertoire.id,
        repertoire.user_id,
        data,
    )

    assert result is repertoire
    assert repertoire.name == 'New name'
    assert repertoire.description == 'Description'


@pytest.mark.asyncio
async def test_update_changes_description(
        service: RepertoireService,
        ) -> None:
    repertoire = Repertoire(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name='Name',
        description='Old description',
        side=RepertoireSide.WHITE,
        version=1,
    )

    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )

    data = RepertoireUpdate(
        description='New description',
    )

    result = await service.update(
        repertoire.id,
        repertoire.user_id,
        data,
    )

    assert result is repertoire
    assert repertoire.description == 'New description'


@pytest.mark.asyncio
async def test_update_changes_all_provided_fields(
        service: RepertoireService,
        ) -> None:
    repertoire = Repertoire(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name='Old name',
        description='Old description',
        side=RepertoireSide.WHITE,
        version=1,
    )

    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )

    data = RepertoireUpdate(
        name='New name',
        description='New description',
    )

    await service.update(
        repertoire.id,
        repertoire.user_id,
        data,
    )

    assert repertoire.name == 'New name'
    assert repertoire.description == 'New description'


@pytest.mark.asyncio
async def test_update_does_not_change_unset_fields(
        service: RepertoireService,
        ) -> None:
    repertoire = Repertoire(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name='Original name',
        description='Original description',
        side=RepertoireSide.WHITE,
        version=1,
    )

    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )

    data = RepertoireUpdate()

    await service.update(
        repertoire.id,
        repertoire.user_id,
        data,
    )

    assert repertoire.name == 'Original name'
    assert repertoire.description == 'Original description'


@pytest.mark.asyncio
async def test_update_allows_explicit_null_description(
        service: RepertoireService,
        ) -> None:
    repertoire = Repertoire(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name='Name',
        description='Description',
        side=RepertoireSide.WHITE,
        version=1,
    )

    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )

    data = RepertoireUpdate(
        description=None,
    )

    await service.update(
        repertoire.id,
        repertoire.user_id,
        data,
    )

    assert repertoire.description is None


@pytest.mark.asyncio
async def test_update_raises_when_repertoire_does_not_exist(
        service: RepertoireService,
        ) -> None:
    repertoire_id = uuid.uuid4()
    user_id = uuid.uuid4()

    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=None,
    )

    data = RepertoireUpdate(
        name='New name',
    )

    with pytest.raises(RepertoireNotFoundError):
        await service.update(
            repertoire_id,
            user_id,
            data,
        )

    service.session.refresh.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_refreshes_repertoire(
        service: RepertoireService,
        session: MagicMock,
        ) -> None:
    repertoire = Repertoire(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name='Old',
        description='',
        side=RepertoireSide.WHITE,
        version=1,
    )

    service.repertoire_repository.get_by_id_for_user = AsyncMock(
        return_value=repertoire,
    )

    data = RepertoireUpdate(
        name='New',
    )

    await service.update(
        repertoire.id,
        repertoire.user_id,
        data,
    )

    session.refresh.assert_awaited_once_with(repertoire)


@pytest.mark.asyncio
async def test_delete_deletes_existing_repertoire(
        service: RepertoireService,
        ) -> None:
    repertoire = Repertoire(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name='Test',
        description='',
        side=RepertoireSide.WHITE,
        version=1,
    )

    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=repertoire,
    )

    await service.delete(
        repertoire.id,
        repertoire.user_id,
    )

    service.repertoire_repository.get_by_id_for_user_for_update.assert_awaited_once_with(
        repertoire.id,
        repertoire.user_id,
    )
    service.repertoire_repository.delete.assert_awaited_once_with(
        repertoire,
    )


@pytest.mark.asyncio
async def test_delete_raises_when_repertoire_does_not_exist(
        service: RepertoireService,
        ) -> None:
    repertoire_id = uuid.uuid4()
    user_id = uuid.uuid4()

    service.repertoire_repository.get_by_id_for_user_for_update = AsyncMock(
        return_value=None,
    )

    with pytest.raises(RepertoireNotFoundError):
        await service.delete(
            repertoire_id,
            user_id,
        )

    service.repertoire_repository.delete.assert_not_awaited()
