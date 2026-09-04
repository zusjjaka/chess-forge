import jwt
import pytest

from utils import security


def test_decode_access_token_returns_payload(
        monkeypatch: pytest.MonkeyPatch,
        ) -> None:
    private_key = 'test-private-key-for-hs256-warning-free'
    public_key = 'test-public-key'

    monkeypatch.setattr(
        security,
        'PUBLIC_KEY',
        public_key,
    )

    token = jwt.encode(
        {'sub': '12345678-1234-5678-1234-567812345678'},
        private_key,
        algorithm='HS256',
    )

    monkeypatch.setattr(
        jwt,
        'decode',
        lambda token, key, algorithms: {
            'sub': '12345678-1234-5678-1234-567812345678',
        },
    )

    payload = security.decode_access_token(token)

    assert payload == {
        'sub': '12345678-1234-5678-1234-567812345678',
    }


def test_decode_access_token_uses_public_key(
        monkeypatch: pytest.MonkeyPatch,
        ) -> None:
    calls: list[tuple[str, str, list[str]]] = []

    def fake_decode(
            token: str,
            key: str,
            algorithms: list[str],
            ) -> dict[str, object]:
        calls.append(
            (
                token,
                key,
                algorithms,
            )
        )
        return {'sub': 'user-id'}

    monkeypatch.setattr(
        security,
        'PUBLIC_KEY',
        'test-public-key',
    )
    monkeypatch.setattr(
        jwt,
        'decode',
        fake_decode,
    )

    security.decode_access_token('test-token')

    assert calls == [
        (
            'test-token',
            'test-public-key',
            ['RS256'],
        ),
    ]


def test_decode_access_token_propagates_invalid_token_error(
        monkeypatch: pytest.MonkeyPatch,
        ) -> None:
    error = jwt.InvalidTokenError('invalid token')

    def fake_decode(
            token: str,
            key: str,
            algorithms: list[str],
            ) -> dict[str, object]:
        raise error

    monkeypatch.setattr(
        jwt,
        'decode',
        fake_decode,
    )

    with pytest.raises(jwt.InvalidTokenError) as exc_info:
        security.decode_access_token('invalid-token')

    assert exc_info.value is error
