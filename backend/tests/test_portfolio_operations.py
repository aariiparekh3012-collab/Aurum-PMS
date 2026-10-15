"""Portfolio HTTP contract tests for the current /api/v1/portfolio routes.

Lifecycle and accounting behavior is covered in test_portfolio_use_cases.py;
these tests guard the actual API paths, permissions, and input validation.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_header

_ACCOUNT_ID = str(uuid.uuid4())
_SECURITY_ID = str(uuid.uuid4())


def test_create_account_requires_auth(client: TestClient):
    resp = client.post("/api/v1/portfolio/accounts", json={})
    assert resp.status_code == 401


def test_investor_cannot_create_account(client: TestClient, investor_token: str):
    resp = client.post("/api/v1/portfolio/accounts", json={
        "client_id": str(uuid.uuid4()), "strategy_id": str(uuid.uuid4()),
    }, headers=auth_header(investor_token))
    assert resp.status_code == 403


def test_account_requires_client_and_strategy(client: TestClient, compliance_token: str):
    resp = client.post("/api/v1/portfolio/accounts", json={}, headers=auth_header(compliance_token))
    assert resp.status_code == 422


def test_staff_can_list_accounts(client: TestClient, compliance_token: str):
    resp = client.get("/api/v1/portfolio/accounts", headers=auth_header(compliance_token))
    assert resp.status_code == 200
    assert resp.json() == []


def test_nonexistent_account_is_not_found(client: TestClient, compliance_token: str):
    resp = client.get(
        f"/api/v1/portfolio/accounts/{_ACCOUNT_ID}", headers=auth_header(compliance_token),
    )
    assert resp.status_code == 404


def test_invalid_account_id_rejected(client: TestClient, compliance_token: str):
    resp = client.get("/api/v1/portfolio/accounts/not-a-uuid", headers=auth_header(compliance_token))
    assert resp.status_code == 422


@pytest.mark.parametrize("side,quantity,price", [
    ("hold", 1, 100), ("buy", 0, 100), ("sell", -1, 100), ("buy", 1, 0),
])
def test_invalid_trade_rejected(client: TestClient, compliance_token: str, side, quantity, price):
    resp = client.post(
        f"/api/v1/portfolio/accounts/{_ACCOUNT_ID}/trades",
        json={"security_id": _SECURITY_ID, "side": side, "quantity": quantity, "price_inr": price},
        headers=auth_header(compliance_token),
    )
    assert resp.status_code == 422


def test_investor_cannot_record_trade(client: TestClient, investor_token: str):
    resp = client.post(
        f"/api/v1/portfolio/accounts/{_ACCOUNT_ID}/trades",
        json={"security_id": _SECURITY_ID, "side": "buy", "quantity": 1, "price_inr": 100},
        headers=auth_header(investor_token),
    )
    assert resp.status_code == 403


@pytest.mark.parametrize("flow_type,amount", [
    ("invalid", 100), ("contribution", 0), ("withdrawal", -10),
])
def test_invalid_capital_flow_rejected(client: TestClient, compliance_token: str, flow_type, amount):
    resp = client.post(
        f"/api/v1/portfolio/accounts/{_ACCOUNT_ID}/capital-flows",
        json={"flow_type": flow_type, "amount_inr": amount},
        headers=auth_header(compliance_token),
    )
    assert resp.status_code == 422


def test_investor_cannot_seed_strategy(client: TestClient, investor_token: str):
    resp = client.post(
        "/api/v1/portfolio/strategies", json={"name": "Growth"},
        headers=auth_header(investor_token),
    )
    assert resp.status_code == 403


def test_staff_can_seed_and_list_strategy(client: TestClient, compliance_token: str):
    headers = auth_header(compliance_token)
    created = client.post("/api/v1/portfolio/strategies", json={"name": "Growth"}, headers=headers)
    assert created.status_code == 201
    assert created.json()["code"] == "GROWTH"
    listed = client.get("/api/v1/portfolio/strategies", headers=headers)
    assert listed.status_code == 200
    assert any(row["id"] == created.json()["id"] for row in listed.json()["strategies"])
