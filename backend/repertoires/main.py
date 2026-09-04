from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    Request,
)
from fastapi.responses import JSONResponse
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
)

from api.v1.repertoires import router as repertoires_router
from core.constants import (
    LINES_MOVES_CHECK_CONSTRAINT,
    LINES_REPERTOIRE_PARENT_FK,
    UNIQUE_ROOT_CONSTRAINT,
)
from db.session import engine
from exceptions import (
    APIException,
    DatabaseCheckConstraintError,
    DatabaseConnectionError,
    DatabaseError,
    InvalidLineRelationshipError,
    RootLineAlreadyExistsError,
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(
    title='ChessForge Repertoires Service',
    version='0.1.0',
    lifespan=lifespan,
)

app.include_router(repertoires_router, prefix='/api/v1')


@app.exception_handler(APIException)
def api_exception_handler(
        _request: Request,
        exc: APIException,
        ) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={'detail': exc.detail},
    )


@app.exception_handler(IntegrityError)
def integrity_error_handler(
        _request: Request,
        exc: IntegrityError,
        ) -> JSONResponse:
    constraint_name = getattr(
        getattr(exc.orig, 'diag', None),
        'constraint_name',
        None,
    )

    error: APIException

    if constraint_name == UNIQUE_ROOT_CONSTRAINT:
        error = RootLineAlreadyExistsError()

    elif constraint_name == LINES_REPERTOIRE_PARENT_FK:
        error = InvalidLineRelationshipError()

    elif constraint_name == LINES_MOVES_CHECK_CONSTRAINT:
        error = DatabaseCheckConstraintError()

    else:
        error = DatabaseError()

    return JSONResponse(
        status_code=error.status_code,
        content={'detail': error.detail},
    )


@app.exception_handler(OperationalError)
def operational_error_handler(
        _request: Request,
        _exc: OperationalError,
        ) -> JSONResponse:
    error = DatabaseConnectionError()

    return JSONResponse(
        status_code=error.status_code,
        content={'detail': error.detail},
    )


@app.exception_handler(SQLAlchemyError)
def sqlalchemy_error_handler(
        _request: Request,
        _exc: SQLAlchemyError,
        ) -> JSONResponse:
    error = DatabaseError()

    return JSONResponse(
        status_code=error.status_code,
        content={'detail': error.detail},
    )
