from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    SQLAlchemyError,
)

from api.v1.training import router as training_router
from db.session import engine
from exceptions import (
    APIException,
    DatabaseConnectionError,
    DatabaseError,
)
from grpc_client.client import RepertoireGrpcClient


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    repertoire_client = RepertoireGrpcClient()

    app.state.repertoire_client = repertoire_client

    try:
        yield
    finally:
        await repertoire_client.close()
        await engine.dispose()


app = FastAPI(
    title='ChessForge Training Service',
    version='1.0.0',
    lifespan=lifespan,
)

app.include_router(
    training_router,
    prefix='/api/v1',
)


@app.exception_handler(APIException)
def api_exception_handler(
        _request: Request,
        exc: APIException,
        ) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={'detail': exc.detail},
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


@app.exception_handler(IntegrityError)
def integrity_error_handler(
        _request: Request,
        _exc: IntegrityError,
        ) -> JSONResponse:

    error = DatabaseError()

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
