from utils.security import hash_password, verify_password


def test_hash_password():
    password = 'password123'

    password_hash = hash_password(password)

    assert password_hash != password
    assert password_hash


def test_hash_password_generates_different_hashes():
    password = 'password123'

    first_hash = hash_password(password)
    second_hash = hash_password(password)

    assert first_hash != second_hash


def test_verify_password_success():
    password = 'password123'
    password_hash = hash_password(password)

    assert verify_password(password, password_hash) is True


def test_verify_password_failure():
    password_hash = hash_password('password123')

    assert verify_password('wrong-password', password_hash) is False


def test_verify_password_invalid_hash():
    assert (
        verify_password(
            'password123',
            'not-a-valid-argon2-hash',
        )
        is False
    )
