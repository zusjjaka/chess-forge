from uuid import uuid4

import pytest
from sqlalchemy import select

from models.session import (
    TrainingSession,
    TrainingSessionStatus,
)


@pytest.mark.asyncio
async def test_create_session(
    api_client,
    user_id,
    repertoire_id,
):
    response = await api_client.post(
        '/api/v1/training/sessions',
        json={
            'repertoire_id': str(repertoire_id),
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data['repertoire_id'] == str(
        repertoire_id
    )
    assert data['status'] == 'active'
    assert data['current_ply'] == 0
    assert data['line_id'] is not None


@pytest.mark.asyncio
async def test_create_session_with_start_line(
    api_client,
    user_id,
    repertoire_id,
    root_line_id,
):
    response = await api_client.post(
        '/api/v1/training/sessions',
        json={
            'repertoire_id': str(repertoire_id),
            'line_id': str(root_line_id),
        },
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_create_session_invalid_payload(
    api_client,
):
    response = await api_client.post(
        '/api/v1/training/sessions',
        json={
            'repertoire_id': 'not-a-uuid',
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_sessions_empty(
    api_client,
):
    response = await api_client.get(
        '/api/v1/training/sessions',
    )

    assert response.status_code == 200

    data = response.json()

    assert data['items'] == []
    assert data['page'] == 1
    assert data['limit'] == 20
    assert data['total'] == 0


@pytest.mark.asyncio
async def test_list_sessions(
    api_client,
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
):
    first = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[],
    )

    second = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[],
        status=TrainingSessionStatus.PASSED,
    )

    session.add_all([first, second])
    await session.commit()

    response = await api_client.get(
        '/api/v1/training/sessions',
    )

    assert response.status_code == 200

    data = response.json()

    assert data['total'] == 2
    assert len(data['items']) == 2


@pytest.mark.asyncio
async def test_list_sessions_status_filter(
    api_client,
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
):
    active = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[],
        status=TrainingSessionStatus.ACTIVE,
    )

    passed = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[],
        status=TrainingSessionStatus.PASSED,
    )

    session.add_all([active, passed])
    await session.commit()

    response = await api_client.get(
        '/api/v1/training/sessions',
        params={'status': 'passed'},
    )

    assert response.status_code == 200

    data = response.json()

    assert data['total'] == 1
    assert data['items'][0]['status'] == 'passed'


@pytest.mark.asyncio
async def test_list_sessions_page_validation(
    api_client,
):
    response = await api_client.get(
        '/api/v1/training/sessions',
        params={'page': 0},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_session(
    api_client,
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
):
    training_session = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[],
    )

    session.add(training_session)
    await session.commit()

    response = await api_client.get(
        f'/api/v1/training/sessions/'
        f'{training_session.id}',
    )

    assert response.status_code == 200

    data = response.json()

    assert data['id'] == str(training_session.id)
    assert data['repertoire_id'] == str(
        repertoire_id
    )
    assert data['line_id'] == str(
        root_line_id
    )
    assert data['status'] == 'active'


@pytest.mark.asyncio
async def test_get_session_not_found(
    api_client,
):
    response = await api_client.get(
        f'/api/v1/training/sessions/{uuid4()}',
    )

    assert response.status_code == 404
    assert response.json() == {
        'detail': 'Training session not found',
    }


@pytest.mark.asyncio
async def test_get_session_other_user(
    api_client,
    session,
    repertoire_id,
    root_line_id,
    make_training_session,
):
    training_session = make_training_session(
        user_id=uuid4(),
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[],
    )

    session.add(training_session)
    await session.commit()

    response = await api_client.get(
        f'/api/v1/training/sessions/'
        f'{training_session.id}',
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_make_correct_move(
    api_client,
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
):
    training_session = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[
            {
                'line_id': str(root_line_id),
                'moves_count': 1,
                'analytic_version': 1,
            },
        ],
    )

    session.add(training_session)
    await session.commit()

    response = await api_client.post(
        f'/api/v1/training/sessions/'
        f'{training_session.id}/moves',
        json={'move': 'e2e4'},
    )

    assert response.status_code == 200
    assert response.json() == {
        'correct': True,
        'current_ply': 1,
        'status': 'passed',
    }


@pytest.mark.asyncio
async def test_make_wrong_move(
    api_client,
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
):
    training_session = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[
            {
                'line_id': str(root_line_id),
                'moves_count': 1,
                'analytic_version': 1,
            },
        ],
    )

    session.add(training_session)
    await session.commit()

    response = await api_client.post(
        f'/api/v1/training/sessions/'
        f'{training_session.id}/moves',
        json={'move': 'd2d4'},
    )

    assert response.status_code == 200
    assert response.json() == {
        'correct': False,
        'current_ply': 0,
        'status': 'failed',
    }


@pytest.mark.asyncio
async def test_make_move_invalid_payload(
    api_client,
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
):
    training_session = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[
            {
                'line_id': str(root_line_id),
                'moves_count': 1,
                'analytic_version': 1,
            },
        ],
    )

    session.add(training_session)
    await session.commit()

    response = await api_client.post(
        f'/api/v1/training/sessions/'
        f'{training_session.id}/moves',
        json={},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_make_move_not_active(
    api_client,
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
):
    training_session = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[],
        status=TrainingSessionStatus.PASSED,
    )

    session.add(training_session)
    await session.commit()

    response = await api_client.post(
        f'/api/v1/training/sessions/'
        f'{training_session.id}/moves',
        json={'move': 'e2e4'},
    )

    assert response.status_code == 409
    assert response.json() == {
        'detail': 'Training session is not active',
    }


@pytest.mark.asyncio
async def test_make_move_not_found(
    api_client,
):
    response = await api_client.post(
        f'/api/v1/training/sessions/'
        f'{uuid4()}/moves',
        json={'move': 'e2e4'},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_make_move_invalidates_when_revision_changed(
    api_client,
    session,
    user_id,
    repertoire_id,
    root_line_id,
    make_training_session,
    fake_repertoire_client,
):
    training_session = make_training_session(
        user_id=user_id,
        repertoire_id=repertoire_id,
        start_line_id=root_line_id,
        selected_moves=['e2e4'],
        selected_path=[
            {
                'line_id': str(root_line_id),
                'moves_count': 1,
                'analytic_version': 1,
            },
        ],
        repertoire_revision=1,
    )

    session.add(training_session)
    await session.commit()

    fake_repertoire_client.revision = 2

    response = await api_client.post(
        f'/api/v1/training/sessions/'
        f'{training_session.id}/moves',
        json={'move': 'e2e4'},
    )

    assert response.status_code == 409
    assert response.json() == {
        'detail': 'Training session was invalidated',
    }

    await session.refresh(training_session)

    assert training_session.status == (
        TrainingSessionStatus.INVALIDATED
    )
