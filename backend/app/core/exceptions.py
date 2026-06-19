"""Application-wide exception hierarchy.

All custom exceptions inherit from PmsError so a single handler can catch
everything at the API boundary. Error codes are machine-readable strings
for the frontend to key on.
"""
from __future__ import annotations


class PmsError(Exception):
    """Base for all PMS domain/application errors."""

    def __init__(self, message: str, *, code: str = "pms_error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class ValidationError(PmsError):
    def __init__(self, message: str, *, code: str = "validation_error") -> None:
        super().__init__(message, code=code)


class NotFoundError(PmsError):
    def __init__(self, message: str = "Resource not found", *, code: str = "not_found") -> None:
        super().__init__(message, code=code)


class InvalidStateTransition(PmsError):
    def __init__(self, message: str, *, code: str = "invalid_transition") -> None:
        super().__init__(message, code=code)


class AuthenticationError(PmsError):
    def __init__(self, message: str = "Authentication required", *, code: str = "unauthenticated") -> None:
        super().__init__(message, code=code)


class AuthorizationError(PmsError):
    def __init__(self, message: str = "Insufficient permissions", *, code: str = "forbidden") -> None:
        super().__init__(message, code=code)


class ExternalServiceError(PmsError):
    def __init__(self, message: str, *, code: str = "external_service_error") -> None:
        super().__init__(message, code=code)


class DuplicateError(PmsError):
    def __init__(self, message: str, *, code: str = "duplicate") -> None:
        super().__init__(message, code=code)


# Backwards-compatible alias: several routers/dependencies import DomainError
DomainError = PmsError
