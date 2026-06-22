"""Request middleware: correlation id, structured access logging, rate limiting, security headers."""
from __future__ import annotations

import time
import uuid
from collections import defaultdict

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Injects X-Correlation-ID into every request/response, structlog context, and
    emits a structured access-log line on completion."""

    async def dispatch(self, request: Request, call_next):
        structlog.contextvars.clear_contextvars()
        correlation_id = request.headers.get("X-Correlation-ID", uuid.uuid4().hex)
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        start = time.perf_counter()
        response = await call_next(request)
        structlog.get_logger("access").info(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=round((time.perf_counter() - start) * 1000, 2),
        )
        response.headers["X-Correlation-ID"] = correlation_id
        structlog.contextvars.clear_contextvars()
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        # HSTS only in production
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiter for auth endpoints.

    Limits:
    - /auth/login: 10 requests per minute per IP
    - /auth/register: 5 requests per minute per IP
    - /auth/forgot-password: 3 requests per hour per IP
    - /auth/refresh: 30 requests per minute per IP

    NOTE: In production, replace with Redis-backed rate limiter for multi-instance.
    """

    _PURGE_INTERVAL = 300  # purge stale keys every 5 minutes

    def __init__(self, app):
        super().__init__(app)
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._last_purge: float = time.time()
        self._limits: dict[str, tuple[int, int]] = {
            "/api/v1/auth/login": (10, 60),
            "/api/v1/auth/register": (5, 60),
            "/api/v1/auth/forgot-password": (3, 3600),
            "/api/v1/auth/refresh": (30, 60),
        }
        self._max_window = max(w for _, w in self._limits.values())

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _purge_stale_keys(self) -> None:
        """Remove bucket keys whose entries are all expired to prevent unbounded memory growth."""
        now = time.time()
        if now - self._last_purge < self._PURGE_INTERVAL:
            return
        self._last_purge = now
        cutoff = now - self._max_window
        stale = [k for k, v in self._buckets.items() if not v or v[-1] < cutoff]
        for k in stale:
            del self._buckets[k]

    def _is_rate_limited(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        bucket = self._buckets[key]
        # Remove expired entries
        cutoff = now - window_seconds
        self._buckets[key] = [t for t in bucket if t > cutoff]
        bucket = self._buckets[key]

        if len(bucket) >= max_requests:
            return True

        bucket.append(now)
        return False

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "POST" and path in self._limits:
            self._purge_stale_keys()
            ip = self._get_client_ip(request)
            max_req, window = self._limits[path]
            key = f"{path}:{ip}"

            if self._is_rate_limited(key, max_req, window):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "code": "rate_limited",
                            "message": "Too many requests. Please try again later.",
                        }
                    },
                    headers={"Retry-After": str(window)},
                )

        return await call_next(request)
