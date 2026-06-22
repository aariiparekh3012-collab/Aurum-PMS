"""API endpoint tests for the auth routes (/api/v1/auth/*).

These hit the real FastAPI app via TestClient with a transaction-wrapped
Postgres session that rolls back after each test.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_header


# ── Registration ─────────────────────────────────────────────────────────

_REG = {
    "email": "newuser@example.com",
    "password": "StrongP@ss1",
    "full_name": "Test User",
    "role": "investor",
}


def test_register_success(client: TestClient):
    resp = client.post("/api/v1/auth/register", json=_REG)
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_email(client: TestClient):
    client.post("/api/v1/auth/register", json=_REG)
    resp = client.post("/api/v1/auth/register", json=_REG)
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


def test_register_short_password(client: TestClient):
    resp = client.post("/api/v1/auth/register", json={**_REG, "password": "short"})
    assert resp.status_code == 422
    assert "8 characters" in resp.json()["detail"]


def test_register_invalid_role(client: TestClient):
    resp = client.post("/api/v1/auth/register", json={**_REG, "role": "admin"})
    assert resp.status_code == 422
    assert "role" in resp.json()["detail"].lower()


# ── Login ────────────────────────────────────────────────────────────────

def test_login_success(client: TestClient):
    client.post("/api/v1/auth/register", json=_REG)
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": _REG["email"], "password": _REG["password"]},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client: TestClient):
    client.post("/api/v1/auth/register", json=_REG)
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": _REG["email"], "password": "WrongPass99"},
    )
    assert resp.status_code == 401
    assert "Invalid email or password" in resp.json()["detail"]


def test_login_unknown_email(client: TestClient):
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever123"},
    )
    assert resp.status_code == 401


# ── /me ──────────────────────────────────────────────────────────────────

def test_me_authenticated(client: TestClient):
    # Register, then use the returned token to call /me.
    reg_resp = client.post("/api/v1/auth/register", json=_REG)
    token = reg_resp.json()["access_token"]
    resp = client.get("/api/v1/auth/me", headers=auth_header(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == _REG["email"].lower()
    assert data["full_name"] == _REG["full_name"]
    assert data["role"] == "investor"


def test_me_unauthenticated(client: TestClient):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


# ── Dev token endpoint ───────────────────────────────────────────────────

def test_dev_token_endpoint(client: TestClient):
    """The /auth/token dev endpoint should work in test environment."""
    resp = client.post(
        "/api/v1/auth/token",
        json={"username": "testuser", "role": "compliance"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()
