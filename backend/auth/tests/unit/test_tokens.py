import uuid

import jwt
import pytest

from utils.tokens import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)


def test_create_access_token():
    user_id = uuid.uuid4()

    token = create_access_token(user_id)

    assert isinstance(token, str)
    assert token


def test_decode_access_token():
    user_id = uuid.uuid4()

    token = create_access_token(user_id)
    payload = decode_access_token(token)

    assert payload['sub'] == str(user_id)
    assert 'iat' in payload
    assert 'exp' in payload
    assert 'jti' in payload


def test_access_token_has_unique_jti():
    user_id = uuid.uuid4()

    first_payload = decode_access_token(create_access_token(user_id))
    second_payload = decode_access_token(create_access_token(user_id))

    assert first_payload['jti'] != second_payload['jti']


def test_access_token_contains_correct_expiration():
    user_id = uuid.uuid4()

    token = create_access_token(user_id)
    payload = decode_access_token(token)

    assert payload['exp'] > payload['iat']


def test_decode_invalid_token():
    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token('invalid-token')


def test_generate_refresh_token():
    token = generate_refresh_token()

    assert isinstance(token, str)
    assert token


def test_generate_refresh_tokens_are_unique():
    first = generate_refresh_token()
    second = generate_refresh_token()

    assert first != second


def test_hash_refresh_token():
    token = 'refresh-token'

    token_hash = hash_refresh_token(token)

    assert isinstance(token_hash, bytes)
    assert len(token_hash) == 32


def test_hash_refresh_token_is_deterministic():
    token = 'refresh-token'

    first_hash = hash_refresh_token(token)
    second_hash = hash_refresh_token(token)

    assert first_hash == second_hash


def test_different_refresh_tokens_have_different_hashes():
    first_hash = hash_refresh_token('first-token')
    second_hash = hash_refresh_token('second-token')

    assert first_hash != second_hash
