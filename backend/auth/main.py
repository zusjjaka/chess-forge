from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    Request,
)
from fastapi.responses import JSONResponse

from api.v1.auth import router as auth_router
from clients.rabbitmq import RabbitmqClient
from core.config import get_settings
from exceptions import APIException
from publishers.email import EmailPublisher


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    settings = get_settings()

    rabbitmq_client = RabbitmqClient(settings.rabbitmq.url)
    await rabbitmq_client.connect()
    await rabbitmq_client.setup_topology()

    app.state.email_publisher = EmailPublisher(rabbitmq=rabbitmq_client)

    try:
        yield
    finally:
        await rabbitmq_client.close()


app = FastAPI(title='ChessForge Auth Service', version='0.1.0', lifespan=lifespan)

app.include_router(auth_router, prefix='/api/v1')


@app.exception_handler(APIException)
def api_exception_handler(_request: Request, exc: APIException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})
