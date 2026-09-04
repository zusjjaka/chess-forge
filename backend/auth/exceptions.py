from fastapi import status


class APIException(Exception):
    """Base class for exception, that must be handled."""

    detail: str
    status_code: int

    def __init__(self, **context: object) -> None:
        self.detail = self.detail.format(**context)
        super().__init__(self.detail)


class UserAlreadyExistError(APIException):
    """User with the given email already exists."""

    detail = 'User with email {email} is already exists'
    status_code = status.HTTP_409_CONFLICT


class InvalidCredentialsError(APIException):
    """Invalid credentials email:password."""

    detail = 'Invalid credentials'
    status_code = status.HTTP_401_UNAUTHORIZED


class InvalidAccessTokenError(APIException):
    """Access token is invalid."""

    detail = 'Invalid access token'
    status_code = status.HTTP_401_UNAUTHORIZED


class RefreshTokenExpiredError(APIException):
    """Refresh token has expired."""

    detail = 'Refresh token expired'
    status_code = status.HTTP_401_UNAUTHORIZED


class RefreshTokenReuseError(APIException):
    """Refresh token reuse was detected."""

    detail = 'Refresh token reuse detected'
    status_code = status.HTTP_401_UNAUTHORIZED


class RefreshTokenInvalidError(APIException):
    """Refresh token is invalid."""

    detail = 'Invalid refresh token'
    status_code = status.HTTP_401_UNAUTHORIZED


class EmailNotConfirmedError(APIException):
    """Email is not confirmed."""

    detail = 'Email is not verified'
    status_code = status.HTTP_403_FORBIDDEN


class VerificationCodeInvalidError(APIException):
    """Verification code is invalid."""

    detail = 'Invalid or expired verification code'
    status_code = status.HTTP_400_BAD_REQUEST


class PasswordInvalidError(APIException):
    """Current password is invalid."""

    detail = 'Current password is invalid'
    status_code = status.HTTP_400_BAD_REQUEST


class EmailSameError(APIException):
    """New email is the same as old one."""

    detail = 'New email is the same as the current email'
    status_code = status.HTTP_400_BAD_REQUEST
