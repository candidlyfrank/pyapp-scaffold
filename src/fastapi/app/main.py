import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings


def configure_logging() -> None:
    level = os.getenv("LOG_LEVEL", "DEBUG").upper()
    logging.basicConfig(level=level, format="%(levelname)s %(name)s %(message)s")


configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.ready = True
    yield
    app.state.ready = False


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.title,
        version=settings.version,
        lifespan=lifespan,
    )
    application.add_middleware(CorrelationIdMiddleware)
    application.include_router(api_router)
    return application


app = create_app()
