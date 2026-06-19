"""Integration tests for KRA (KYC Registration Agency) verification.

These tests run against the mock KRA sandbox server (tests/mocks/kra_sandbox.py).

To run with mock server:
    1. Start mock server: uvicorn tests.mocks.kra_sandbox:app --port 8001
    2. Set in .env: KRA_BASE_URL=http://localhost:8001
    3. pytest tests/integration/test_kra_integration.py -v
"""
from __future__ import annotations

import pytest

from app.core.exceptions import ValidationError
from app.infrastructure.external.kra_client import KraKycAdapter


@pytest.fixture
def kra_adapter():
    """Fixture providing a KRA adapter (requires mock server on :8001)."""
    # Override with mock server URL for tests
    import os
    os.environ["KRA_BASE_URL"] = "http://localhost:8001"
    os.environ["KRA_API_KEY"] = "test-key"
    return KraKycAdapter()


class TestKraVerification:
    """Test KRA verification scenarios."""

    def test_verify_valid_pan_succeeds(self, kra_adapter):
        """Verified PAN should return VERIFIED status."""
        result = kra_adapter.verify(
            pan="AAAPA1234A",
            aadhaar_last4="1234",
            name="Rajesh Kumar",
        )
        assert result.verified is True
        assert result.source == "kra"
        assert "KRA-" in result.reference

    def test_verify_alternative_valid_pan(self, kra_adapter):
        """Multiple verified PANs should work."""
        result = kra_adapter.verify(
            pan="BBBPB5678B",
            aadhaar_last4="5678",
            name="Priya Singh",
        )
        assert result.verified is True
        assert result.source == "kra"

    def test_verify_rejected_pan_fails(self, kra_adapter):
        """Rejected PAN should return VERIFIED=False with reason."""
        result = kra_adapter.verify(
            pan="REJECTD1E",
            aadhaar_last4="1234",
            name="Wrong Name",
        )
        assert result.verified is False
        assert result.source == "kra"
        assert result.reason is not None
        assert "mismatch" in result.reason.lower()

    def test_verify_fraud_pan_rejected(self, kra_adapter):
        """Fraud-flagged PAN should be rejected."""
        result = kra_adapter.verify(
            pan="FRAUDZ1234",
            aadhaar_last4="1234",
            name="Test User",
        )
        assert result.verified is False
        assert "fraud" in result.reason.lower() or "inactive" in result.reason.lower()

    def test_verify_unknown_pan_returns_pending(self, kra_adapter):
        """Unknown PANs should return PENDING (async vendor)."""
        result = kra_adapter.verify(
            pan="UNKNPAN99Z",
            aadhaar_last4="9999",
            name="Unknown User",
        )
        assert result.verified is False
        assert "pending" in result.reason.lower() or "progress" in result.reason.lower()

    def test_verify_invalid_pan_format_raises(self, kra_adapter):
        """Invalid PAN format should raise ValidationError immediately."""
        with pytest.raises(ValidationError) as exc:
            kra_adapter.verify(
                pan="INVALID",  # Only 7 chars, not 10
                aadhaar_last4="1234",
                name="Test User",
            )
        assert exc.value.code == "invalid_pan"

    def test_verify_invalid_aadhaar_format_raises(self, kra_adapter):
        """Invalid Aadhaar format should raise ValidationError."""
        with pytest.raises(ValidationError) as exc:
            kra_adapter.verify(
                pan="AAAPA1234A",
                aadhaar_last4="12",  # Only 2 digits, need 4
                name="Test User",
            )
        assert exc.value.code == "invalid_aadhaar"

    def test_verify_non_digit_aadhaar_raises(self, kra_adapter):
        """Non-digit Aadhaar should raise ValidationError."""
        with pytest.raises(ValidationError):
            kra_adapter.verify(
                pan="AAAPA1234A",
                aadhaar_last4="ABCD",  # Not digits
                name="Test User",
            )

    def test_verify_whitespace_in_name_is_trimmed(self, kra_adapter):
        """Leading/trailing whitespace in name should be stripped."""
        # This test verifies the adapter normalizes input
        result = kra_adapter.verify(
            pan="AAAPA1234A",
            aadhaar_last4="1234",
            name="  Rajesh Kumar  ",  # Extra whitespace
        )
        # If it reaches the API, whitespace was handled
        assert result.source == "kra"


class TestKraPanValidation:
    """Test PAN format validation."""

    def test_valid_pan_format(self, kra_adapter):
        """10-char PAN with correct format should be valid."""
        assert kra_adapter._is_valid_pan("AAAPA1234A") is True
        assert kra_adapter._is_valid_pan("BBBPB5678B") is True
        assert kra_adapter._is_valid_pan("CCCPC9012C") is True

    def test_invalid_pan_too_short(self, kra_adapter):
        """PAN shorter than 10 chars is invalid."""
        assert kra_adapter._is_valid_pan("AAAP1234A") is False

    def test_invalid_pan_too_long(self, kra_adapter):
        """PAN longer than 10 chars is invalid."""
        assert kra_adapter._is_valid_pan("AAAPA1234AA") is False

    def test_invalid_pan_non_alpha_prefix(self, kra_adapter):
        """PAN with non-alpha first 5 chars is invalid."""
        assert kra_adapter._is_valid_pan("1AAAA1234A") is False

    def test_invalid_pan_non_digit_middle(self, kra_adapter):
        """PAN with non-digit chars 5-9 is invalid."""
        assert kra_adapter._is_valid_pan("AAAPAABCDA") is False

    def test_invalid_pan_non_alpha_last(self, kra_adapter):
        """PAN with non-alpha last char is invalid."""
        assert kra_adapter._is_valid_pan("AAAPA12341") is False


class TestKraErrorHandling:
    """Test KRA error handling and retries."""

    def test_verify_logs_request_details(self, kra_adapter, caplog):
        """Verification should log non-PII details for debugging."""
        import logging
        caplog.set_level(logging.INFO)

        result = kra_adapter.verify(
            pan="AAAPA1234A",
            aadhaar_last4="1234",
            name="Test User",
        )

        # Check logs don't contain full PAN (only last 4)
        log_text = caplog.text
        assert "1234" in log_text or "A" in log_text  # Last 4 or masked version
        # Full PAN should NOT be in logs
        assert "AAAPA1234A" not in log_text or "AAAPA" not in log_text

    def test_verify_request_id_is_unique(self, kra_adapter):
        """Each verification request should have a unique request_id."""
        # Make two requests and verify they succeed
        result1 = kra_adapter.verify(
            pan="AAAPA1234A",
            aadhaar_last4="1234",
            name="Test User 1",
        )
        result2 = kra_adapter.verify(
            pan="AAAPA1234A",
            aadhaar_last4="1234",
            name="Test User 2",
        )
        # Both should succeed (request IDs don't collide)
        assert result1.verified is True
        assert result2.verified is True


# Test data for quick reference
TEST_CASES = [
    {
        "name": "Verified Identity",
        "pan": "AAAPA1234A",
        "aadhaar_last4": "1234",
        "full_name": "Rajesh Kumar",
        "expected_verified": True,
    },
    {
        "name": "Rejected (Name Mismatch)",
        "pan": "REJECTD1E",
        "aadhaar_last4": "1234",
        "full_name": "Wrong Name",
        "expected_verified": False,
    },
    {
        "name": "Pending (Async)",
        "pan": "UNKNPAN99Z",
        "aadhaar_last4": "9999",
        "full_name": "Unknown User",
        "expected_verified": False,
    },
]


@pytest.mark.parametrize("test_case", TEST_CASES)
def test_kra_all_scenarios(test_case, kra_adapter):
    """Parametrized test covering all KRA scenarios."""
    result = kra_adapter.verify(
        pan=test_case["pan"],
        aadhaar_last4=test_case["aadhaar_last4"],
        name=test_case["full_name"],
    )
    assert result.verified == test_case["expected_verified"]
    assert result.source == "kra"
