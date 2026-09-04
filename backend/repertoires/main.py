from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.v1.repertoires import router as repertoires_router
from db.session import engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    try:
        yield
    finally:
        await engine.dispose()


app = FastAPI(
    title='ChessForge Repertoires Service',
    version='0.1.0',
    lifespan=lifespan
)

app.include_router(repertoires_router, prefix='/api/v1')
