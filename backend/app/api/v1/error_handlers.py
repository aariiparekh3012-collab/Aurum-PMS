"""Global exception handlers — map domain errors to HTTP responses."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DuplicateError,
    ExternalServiceError,
    InvalidStateTransition,
    NotFoundError,
    PmsError,
    ValidationError,
)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValidationError)
    async def validation_error(_req: Request, exc: ValidationError):
        return JSONResponse(status_code=422, content={"error": exc.code, "message": exc.message})

    @app.exception_handler(NotFoundError)
    async def not_found(_req: Request, exc: NotFoundError):
        return JSONResponse(status_code=404, content={"error": exc.code, "message": exc.message})

    @app.exception_handler(InvalidStateTransition)
    async def bad_transition(_req: Request, exc: InvalidStateTransition):
        return JSONResponse(status_code=409, content={"error": exc.code, "message": exc.message})

    @app.exception_handler(DuplicateError)
    async def duplicate(_req: Request, exc: DuplicateError):
        return JSONResponse(status_code=409, content={"error": exc.code, "message": exc.message})

    @app.exception_handler(AuthenticationError)
    async def authn(_req: Request, exc: AuthenticationError):
        return JSONResponse(status_code=401, content={"error": exc.code, "message": exc.message})

    @app.exception_handler(AuthorizationError)
    async def authz(_req: Request, exc: AuthorizationError):
        return JSONResponse(status_code=403, content={"error": exc.code, "message": exc.message})

    @app.exception_handler(ExternalServiceError)
    async def external(_req: Request, exc: ExternalServiceError):
        return JSONResponse(status_code=502, content={"error": exc.code, "message": exc.message})

    @app.exception_handler(PmsError)
    async def generic_pms(_req: Request, exc: PmsError):
        return JSONResponse(status_code=500, content={"error": exc.code, "message": exc.message})
