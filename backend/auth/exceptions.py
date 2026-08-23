from fastapi import status


class APIException(Exception):
    """Base class for exception, that must be handled."""

    def __init__(self, detail: str, status_code: int) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


class UserAlreadyExistError(APIException):
    """Trying to create the second user with the same email."""

    def __init__(self, email: str) -> None:
        super().__init__(
            detail=f'Пользователь с почтой {email} уже существует',
            status_code=status.HTTP_409_CONFLICT,
        )


class InvalidAccessTokenError(APIException):
    """Access token is invalid."""

    def __init__(self) -> None:
        super().__init__(
            detail='Invalid access token',
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
