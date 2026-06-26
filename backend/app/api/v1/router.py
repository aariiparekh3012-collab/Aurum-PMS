"""Aggregates all v1 routers under a single APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers import (
    applications,
    audit,
    auth,
    auth_recovery,
    clients,
    dashboard,
    documents,
    fees,
    health,
    investor,
    market_data,
    messaging,
    notifications,
    nse_reports,
    onboarding,
    performance,
    portfolio,
    reference,
    reports,
    trading,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(auth_recovery.router)
api_router.include_router(dashboard.router)
api_router.include_router(onboarding.router)
api_router.include_router(applications.router)
api_router.include_router(clients.router)
api_router.include_router(reference.router)
api_router.include_router(trading.router)
api_router.include_router(portfolio.router)
api_router.include_router(investor.router)
api_router.include_router(performance.router)
api_router.include_router(reports.router)
api_router.include_router(nse_reports.router)
api_router.include_router(notifications.router)
api_router.include_router(market_data.router)
api_router.include_router(fees.router)
api_router.include_router(documents.router)
api_router.include_router(messaging.router)
api_router.include_router(audit.router)
