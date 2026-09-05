from fastapi import status


class APIException(Exception):
    """Base class for exception, that must be handled."""

    detail: str
    status_code: int

    def __init__(self, **context: object) -> None:
        self.detail = self.detail.format(**context)
        super().__init__(self.detail)


class InvalidAccessTokenError(APIException):
    """Access token is invalid."""

    detail = 'Invalid access token'
    status_code = status.HTTP_401_UNAUTHORIZED


class RepertoireNotFoundError(APIException):
    """Repertoire was not found."""

    detail = 'Repertoire not found'
    status_code = status.HTTP_404_NOT_FOUND


class LineNotFoundError(APIException):
    """Line was not found."""

    detail = 'Line not found'
    status_code = status.HTTP_404_NOT_FOUND


class RootLineDeletionError(APIException):
    """Root line cannot be deleted."""

    detail = 'Root line cannot be deleted'
    status_code = status.HTTP_400_BAD_REQUEST


class ParentLineMovesUpdateError(APIException):
    """Parent line moves cannot be updated."""

    detail = 'Cannot update moves of a parent line'
    status_code = status.HTTP_400_BAD_REQUEST


class InvalidLineMovesError(APIException):
    """Line moves are invalid."""

    detail = 'Invalid line moves'
    status_code = status.HTTP_400_BAD_REQUEST


class RepertoireVersionConflictError(APIException):
    """Repertoire version conflict."""

    detail = 'Repertoire version conflict'
    status_code = status.HTTP_409_CONFLICT


class RootLineAlreadyExistsError(APIException):
    """Root line already exists."""

    detail = 'Root line already exists'
    status_code = status.HTTP_409_CONFLICT


class InvalidLineRelationshipError(APIException):
    """Line relationship is invalid."""

    detail = 'Invalid line relationship'
    status_code = status.HTTP_409_CONFLICT


class DatabaseCheckConstraintError(APIException):
    """Database check constraint was violated."""

    detail = 'Invalid data'
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT


class DatabaseConnectionError(APIException):
    """Database connection failed."""

    detail = 'Database unavailable'
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class DatabaseError(APIException):
    """Unexpected database error occurred."""

    detail = 'Internal server error'
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
