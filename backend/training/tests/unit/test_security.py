import jwt

import utils.security as security


def test_decode_access_token(monkeypatch):
    expected = {
        'sub': '123',
        'exp': 9999999999,
    }

    calls = {}

    def fake_decode(*args, **kwargs):
        calls['args'] = args
        calls['kwargs'] = kwargs
        return expected

    monkeypatch.setattr(
        security.jwt,
        'decode',
        fake_decode,
    )

    result = security.decode_access_token('token')

    assert result == expected
    assert calls['args'] == (
        'token',
        security.PUBLIC_KEY,
    )
    assert calls['kwargs'] == {
        'algorithms': ['RS256'],
    }
