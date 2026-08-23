import uuid
from datetime import UTC, datetime

import jwt

from core.jwt import PUBLIC_KEY
from utils.tokens import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_refresh_token,
)


class TestAccessToken:
    def test_create_access_token(self) -> None:
        user_id = uuid.uuid4()

        token = create_access_token(user_id)
        payload = jwt.decode(
            token,
            PUBLIC_KEY,
            algorithms=['RS256'],
        )

        assert payload['sub'] == str(user_id)
        assert 'iat' in payload
        assert 'exp' in payload
        assert 'jti' in payload

    def test_access_token_has_expiration(self) -> None:
        user_id = uuid.uuid4()

        token = create_access_token(user_id)
        payload = jwt.decode(
            token,
            PUBLIC_KEY,
            algorithms=['RS256'],
        )

        now = datetime.now(UTC).timestamp()

        assert payload['exp'] > now

    def test_decode_access_token(self) -> None:
        user_id = uuid.uuid4()

        token = create_access_token(user_id)
        payload = decode_access_token(token)

        assert payload['sub'] == str(user_id)

    def test_invalid_token_raises_error(self) -> None:
        invalid_token = 'not.a.valid.jwt'

        try:
            decode_access_token(invalid_token)
        except jwt.InvalidTokenError:
            pass
        else:
            raise AssertionError('Expected jwt.InvalidTokenError')


class TestRefreshToken:
    def test_generate_refresh_token(self) -> None:
        token = generate_refresh_token()

        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_refresh_tokens_are_unique(self) -> None:
        first_token = generate_refresh_token()
        second_token = generate_refresh_token()

        assert first_token != second_token

    def test_hash_refresh_token(self) -> None:
        token = 'refresh-token'

        token_hash = hash_refresh_token(token)

        assert isinstance(token_hash, bytes)
        assert len(token_hash) == 32

    def test_same_refresh_token_has_same_hash(self) -> None:
        token = generate_refresh_token()

        first_hash = hash_refresh_token(token)
        second_hash = hash_refresh_token(token)

        assert first_hash == second_hash

    def test_different_refresh_tokens_have_different_hashes(self) -> None:
        first_token = generate_refresh_token()
        second_token = generate_refresh_token()

        first_hash = hash_refresh_token(first_token)
        second_hash = hash_refresh_token(second_token)

        assert first_hash != second_hash
