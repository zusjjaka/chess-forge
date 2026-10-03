class APIException(Exception):
    detail: str
    status_code: int

    def __init__(
            self,
            **context: object,
            ) -> None:
        self.detail = self.detail.format(**context)
        super().__init__(self.detail)


class InvalidAccessTokenError(APIException):
    detail = 'Invalid access token'
    status_code = 401


class TrainingSessionNotFoundError(APIException):
    detail = 'Training session not found'
    status_code = 404


class TrainingSessionNotActiveError(APIException):
    detail = 'Training session is not active'
    status_code = 409


class TrainingSessionInvalidatedError(APIException):
    detail = 'Training session was invalidated'
    status_code = 409


class RepertoireNotFoundError(APIException):
    detail = 'Repertoire not found'
    status_code = 404


class TrainingTreeNotFoundError(APIException):
    detail = 'Training tree not found'
    status_code = 404


class DatabaseConnectionError(APIException):
    detail = 'Database is unavailable'
    status_code = 503


class DatabaseError(APIException):
    detail = 'Database error'
    status_code = 500
