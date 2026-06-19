"""Structured JSON logging.

Regulated workloads need tamper-evident, queryable logs. We emit JSON with a
per-request correlation id (see api/middleware.py) and NEVER log raw PII.
"""
from __future__ import annotations

import logging

import structlog


def configure_logging(debug: bool = False) -> None:
    logging.basicConfig(format="%(message)s", level=logging.DEBUG if debug else logging.INFO)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "pms"):
    return structlog.get_logger(name)
