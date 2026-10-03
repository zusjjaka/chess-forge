from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
)

from exceptions import (
    APIException,
    DatabaseConnectionError,
    DatabaseError,
    TrainingSessionNotFoundError,
)
from main import (
    api_exception_handler,
    operational_error_handler,
    integrity_error_handler,
    sqlalchemy_error_handler,
)


def make_request() -> Request:
    return Request(
        {
            'type': 'http',
            'method': 'GET',
            'path': '/',
            'headers': [],
            'query_string': b'',
            'server': ('test', 80),
            'client': ('test', 1234),
            'scheme': 'http',
        }
    )


def test_api_exception_handler():
    request = make_request()

    response = api_exception_handler(
        request,
        TrainingSessionNotFoundError(),
    )

    assert isinstance(response, JSONResponse)
    assert response.status_code == 404
    assert response.body == (
        b'{"detail":"Training session not found"}'
    )


def test_operational_error_handler():
    request = make_request()

    exception = OperationalError(
        'SELECT 1',
        {},
        Exception('connection failed'),
    )

    response = operational_error_handler(
        request,
        exception,
    )

    assert response.status_code == 503
    assert response.body == (
        b'{"detail":"Database is unavailable"}'
    )


def test_integrity_error_handler():
    request = make_request()

    exception = IntegrityError(
        'INSERT',
        {},
        Exception('constraint'),
    )

    response = integrity_error_handler(
        request,
        exception,
    )

    assert response.status_code == 500
    assert response.body == (
        b'{"detail":"Database error"}'
    )


def test_sqlalchemy_error_handler():
    request = make_request()

    response = sqlalchemy_error_handler(
        request,
        SQLAlchemyError(),
    )

    assert response.status_code == 500
    assert response.body == (
        b'{"detail":"Database error"}'
    )


def test_api_exception_context_formatting():
    class CustomException(APIException):
        detail = 'Invalid value: {value}'
        status_code = 400

    exception = CustomException(value='test')

    assert exception.detail == 'Invalid value: test'
    assert str(exception) == 'Invalid value: test'
