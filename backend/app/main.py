"""FastAPI application factory — the single entry point.

    uvicorn app.main:app --reload
"""
from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from app.api.v1.error_handlers import register_error_handlers
from app.api.v1.router import api_router
from app.api.middleware import CorrelationIdMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from app.core.config import get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def _lifespan(application: FastAPI):  # noqa: ARG001
    """Start background tasks on startup; cancel on shutdown."""
    from app.services.nse_bhavcopy import start_scheduler
    scheduler_task = start_scheduler()
    logger.info("NSE Bhavcopy scheduler launched")
    try:
        yield
    finally:
        scheduler_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await scheduler_task
        logger.info("NSE Bhavcopy scheduler stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(debug=settings.debug)

    is_prod = settings.environment == "production"
    application = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        docs_url=None if is_prod else "/docs",
        openapi_url=None if is_prod else "/openapi.json",
        lifespan=_lifespan,
    )

    # Middleware (order matters — outermost first)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(CorrelationIdMiddleware)
    application.add_middleware(SecurityHeadersMiddleware)
    application.add_middleware(RateLimitMiddleware)

    # Exception handlers
    register_error_handlers(application)

    # Routers — full v1 API surface
    api_prefix = "/api/v1"
    application.include_router(api_router, prefix=api_prefix)

    return application


app = create_app()
