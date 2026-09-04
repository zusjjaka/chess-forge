from utils.security import hash_password, verify_password


class TestHashPassword:
    def test_hash_is_different_from_plain_password(self) -> None:
        password = 'password123'

        password_hash = hash_password(password)

        assert password_hash != password

    def test_same_password_produces_different_hashes(self) -> None:
        password = 'password123'

        first_hash = hash_password(password)
        second_hash = hash_password(password)

        assert first_hash != second_hash


class TestVerifyPassword:
    def test_correct_password(self) -> None:
        password = 'password123'
        password_hash = hash_password(password)

        assert verify_password(password, password_hash) is True

    def test_incorrect_password(self) -> None:
        password_hash = hash_password('password123')

        assert verify_password('wrong-password', password_hash) is False
