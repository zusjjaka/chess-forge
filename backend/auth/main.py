from fastapi import (
    FastAPI,
    Request,
)
from fastapi.responses import JSONResponse

from api.v1.auth import router as auth_router
from exceptions import APIException

app = FastAPI(title='ChessForge Auth Service', version='0.1.0')

app.include_router(auth_router, prefix='/api/v1')


@app.exception_handler(APIException)
def api_exception_handler(_request: Request, exc: APIException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={'detail': exc.detail})
