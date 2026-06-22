"""API endpoint tests for the onboarding routes (/api/v1/onboarding/*).

These tests use FastAPI dependency overrides to inject fake use cases,
so they validate routing, auth, and serialization without touching the DB.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.dependencies import (
    get_approve_uc,
    get_create_application_uc,
    get_current_user,
    get_query_uc,
)
from app.application.onboarding.dto import ApplicationView
from app.core.exceptions import ValidationError
from app.main import app
from tests.conftest import auth_header


# ── Helpers ──────────────────────────────────────────────────────────────

_FAKE_ID = uuid.uuid4()

_APP_VIEW = ApplicationView(
    id=_FAKE_ID,
    status="draft",
    investor_type="individual",
    full_name="Asha Rao",
    email="asha@example.com",
    pan="ABCDE1234F",
    proposed_investment_inr=5_000_000.0,
    risk_category=None,
    kyc_source=None,
)

_CREATE_BODY = {
    "investor_type": "individual",
    "full_name": "Asha Rao",
    "email": "asha@example.com",
    "mobile": "9876543210",
    "pan": "ABCDE1234F",
    "proposed_investment_inr": 5_000_000,
}


def _fake_user(role: str = "investor") -> dict:
    return {"sub": "test@example.com", "role": role}


@pytest.fixture(autouse=True)
def _clear_overrides():
    """Ensure dependency overrides are cleaned up after each test."""
    yield
    app.dependency_overrides.clear()


# ── Create application ───────────────────────────────────────────────────

def test_create_application_success(investor_token: str):
    mock_uc = MagicMock()
    mock_uc.execute.return_value = _APP_VIEW

    app.dependency_overrides[get_create_application_uc] = lambda: mock_uc
    app.dependency_overrides[get_current_user] = lambda: _fake_user()

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            "/api/v1/onboarding/applications",
            json=_CREATE_BODY,
            headers=auth_header(investor_token),
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == str(_FAKE_ID)
    assert data["status"] == "draft"
    assert data["full_name"] == "Asha Rao"
    mock_uc.execute.assert_called_once()


def test_create_application_unauthenticated():
    """Requests without a token should be rejected."""
    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post("/api/v1/onboarding/applications", json=_CREATE_BODY)
    assert resp.status_code == 401


def test_create_application_below_minimum(investor_token: str):
    """Pydantic rejects proposed_investment_inr <= 0 at the schema level."""
    app.dependency_overrides[get_current_user] = lambda: _fake_user()

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            "/api/v1/onboarding/applications",
            json={**_CREATE_BODY, "proposed_investment_inr": -100},
            headers=auth_header(investor_token),
        )
    assert resp.status_code == 422


# ── Get application ──────────────────────────────────────────────────────

def test_get_application(investor_token: str):
    mock_uc = MagicMock()
    mock_uc.get.return_value = _APP_VIEW

    app.dependency_overrides[get_query_uc] = lambda: mock_uc
    app.dependency_overrides[get_current_user] = lambda: _fake_user()

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get(
            f"/api/v1/onboarding/applications/{_FAKE_ID}",
            headers=auth_header(investor_token),
        )
    assert resp.status_code == 200
    assert resp.json()["id"] == str(_FAKE_ID)


# ── List applications (role-restricted) ──────────────────────────────────

def test_list_applications_requires_compliance_or_rm(investor_token: str):
    """Investors should be forbidden from listing all applications."""
    app.dependency_overrides[get_current_user] = lambda: _fake_user("investor")

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get(
            "/api/v1/onboarding/applications",
            headers=auth_header(investor_token),
        )
    assert resp.status_code == 403


def test_list_applications_as_compliance(compliance_token: str):
    mock_uc = MagicMock()
    mock_uc.list_by_status.return_value = [_APP_VIEW]

    app.dependency_overrides[get_query_uc] = lambda: mock_uc
    app.dependency_overrides[get_current_user] = lambda: _fake_user("compliance")

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.get(
            "/api/v1/onboarding/applications?status=draft",
            headers=auth_header(compliance_token),
        )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ── Decision (approve/reject) ───────────────────────────────────────────

def test_approve_requires_compliance_role(investor_token: str):
    """Only compliance users can approve or reject applications."""
    app.dependency_overrides[get_current_user] = lambda: _fake_user("investor")

    with TestClient(app, raise_server_exceptions=False) as client:
        resp = client.post(
            f"/api/v1/onboarding/applications/{_FAKE_ID}/decision",
            json={"approve": True, "reason": "All good"},
            headers=auth_header(investor_token),
        )
    assert resp.status_code == 403
