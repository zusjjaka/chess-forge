from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest

import api.dependencies as dependencies
from exceptions import InvalidAccessTokenError


def test_get_current_user_id(monkeypatch):
    user_id = uuid4()

    monkeypatch.setattr(
        dependencies,
        'decode_access_token',
        lambda token: {'sub': str(user_id)},
    )

    result = dependencies.get_current_user_id(
        dependencies.HTTPAuthorizationCredentials(
            scheme='Bearer',
            credentials='token',
        ),
    )

    assert result == user_id


@pytest.mark.parametrize(
    'payload',
    [
        {},
        {'sub': 'not-a-uuid'},
    ],
)
def test_get_current_user_id_invalid_payload(
    monkeypatch,
    payload,
):
    monkeypatch.setattr(
        dependencies,
        'decode_access_token',
        lambda token: payload,
    )

    credentials = dependencies.HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='token',
    )

    with pytest.raises(InvalidAccessTokenError):
        dependencies.get_current_user_id(credentials)


@pytest.mark.parametrize(
    'exception',
    [
        ValueError(),
        KeyError('sub'),
        jwt.InvalidTokenError(),
    ],
)
def test_get_current_user_id_invalid_token(
    monkeypatch,
    exception,
):
    def decode(_):
        raise exception

    monkeypatch.setattr(
        dependencies,
        'decode_access_token',
        decode,
    )

    credentials = dependencies.HTTPAuthorizationCredentials(
        scheme='Bearer',
        credentials='token',
    )

    with pytest.raises(InvalidAccessTokenError):
        dependencies.get_current_user_id(credentials)


def test_get_repertoire_client():
    client = object()

    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(
                repertoire_client=client,
            ),
        ),
    )

    assert (
        dependencies.get_repertoire_client(request)
        is client
    )


def test_get_training_service():
    session = object()
    repertoire_client = object()

    service = dependencies.get_training_service(
        session=session,
        repertoire_client=repertoire_client,
    )

    assert service._session is session
    assert service._repertoire_client is repertoire_client
