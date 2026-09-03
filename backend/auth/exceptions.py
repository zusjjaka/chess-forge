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


class InvalidCredentialsError(APIException):
    """Invalid creditionals email:password."""

    def __init__(self) -> None:
        super().__init__(
            detail='Invalid credentials', status_code=status.HTTP_401_UNAUTHORIZED
        )


class InvalidAccessTokenError(APIException):
    """Access token is invalid."""

    def __init__(self) -> None:
        super().__init__(
            detail='Invalid access token',
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class RefreshTokenExpiredError(APIException):
    """Refresh token have been expired."""

    def __init__(self) -> None:
        super().__init__(
            detail='Refresh token expired', status_code=status.HTTP_401_UNAUTHORIZED
        )


class RefreshTokenReuseError(APIException):
    """Refresh token reuse was detected."""

    def __init__(self) -> None:
        super().__init__(
            detail='Refresh token reuse detected',
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class RefreshTokenInvalidError(APIException):
    """Refresh token is invalid."""

    def __init__(self) -> None:
        super().__init__(
            detail='Invalid refresh token',
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class EmailNotConfirmedError(APIException):
    """Access token is invalid."""

    def __init__(self) -> None:
        super().__init__(
            detail='Email is not verified',
            status_code=status.HTTP_403_FORBIDDEN,
        )


class VerificationCodeInvalidError(APIException):
    """Validation code is invalid."""

    def __init__(self) -> None:
        super().__init__(
            detail='Invalid or expired verification code',
            status_code=status.HTTP_400_BAD_REQUEST,
        )
