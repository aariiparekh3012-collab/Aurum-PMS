"""Surepass PAN adapter contract tests with deterministic HTTP responses.

No live vendor credentials or sandbox process is required in CI.
"""
from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

from app.core.exceptions import ValidationError
from app.infrastructure.external.kra_client import SurepassKycAdapter


@pytest.fixture
def surepass(monkeypatch):
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        pan = request.read().decode()
        if "REJEC1234D" in pan:
            return httpx.Response(400, text="PAN rejected")
        if "FRAUD1234Z" in pan:
            return httpx.Response(200, json={
                "success": True, "data": {"status": "INVALID", "pan_number": "FRAUD1234Z"},
                "message": "PAN inactive",
            })
        if "UNKNP1234Z" in pan:
            return httpx.Response(200, json={
                "success": False, "data": {}, "message": "Verification pending",
            })
        return httpx.Response(200, json={
            "success": True,
            "data": {"status": "VALID", "pan_number": "AAAPA1234A", "full_name": "Rajesh Kumar"},
        })

    original_client = httpx.Client
    transport = httpx.MockTransport(respond)
    monkeypatch.setattr(
        "app.infrastructure.external.kra_client.get_settings",
        lambda: SimpleNamespace(surepass_base_url="https://surepass.invalid", surepass_api_token="test"),
    )
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original_client(transport=transport, **kwargs),
    )
    return SurepassKycAdapter(), requests


@pytest.mark.parametrize("pan", ["AAAPA1234A", "BBBPB5678B"])
def test_verified_pan(surepass, pan):
    adapter, requests = surepass
    result = adapter.verify(pan=pan, aadhaar_last4="1234", name="Rajesh Kumar")
    assert result.verified is True
    assert result.source == "surepass"
    assert result.reference == "AAAPA1234A"
    assert requests[-1].url == "https://surepass.invalid/pan/pan"
    assert requests[-1].headers["Authorization"] == "Bearer test"


@pytest.mark.parametrize("pan,reason", [
    ("REJEC1234D", "rejected"),
    ("FRAUD1234Z", "inactive"),
    ("UNKNP1234Z", "pending"),
])
def test_unverified_pan(surepass, pan, reason):
    adapter, _ = surepass
    result = adapter.verify(pan=pan, aadhaar_last4="1234", name="Test User")
    assert result.verified is False
    assert result.source == "surepass"
    assert reason in result.reason.lower()


@pytest.mark.parametrize("pan", ["INVALID", "AAAP1234A", "AAAPA1234AA", "1AAAA1234A", "AAAPAABCDA", "AAAPA12341"])
def test_invalid_pan_rejected_before_http(surepass, pan):
    adapter, requests = surepass
    with pytest.raises(ValidationError) as exc:
        adapter.verify(pan=pan, aadhaar_last4="1234", name="Test User")
    assert exc.value.code == "invalid_pan"
    assert not requests


@pytest.mark.parametrize("last4", ["12", "ABCD"])
def test_invalid_aadhaar_rejected_before_http(surepass, last4):
    adapter, requests = surepass
    with pytest.raises(ValidationError) as exc:
        adapter.verify(pan="AAAPA1234A", aadhaar_last4=last4, name="Test User")
    assert exc.value.code == "invalid_aadhaar"
    assert not requests


def test_name_whitespace_and_masked_logging(surepass, caplog):
    adapter, _ = surepass
    result = adapter.verify(pan="AAAPA1234A", aadhaar_last4="1234", name="  Rajesh Kumar  ")
    assert result.verified is True
    assert "AAAPA1234A" not in caplog.text


def test_request_ids_are_unique(surepass):
    adapter, requests = surepass
    for _ in range(2):
        assert adapter.verify(pan="AAAPA1234A", aadhaar_last4="1234", name="Rajesh Kumar").verified
    assert requests[0].headers["X-Request-ID"] != requests[1].headers["X-Request-ID"]
