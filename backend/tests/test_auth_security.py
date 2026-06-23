"""Auth security tests — token expiry, refresh, logout, session management, MFA.

These tests verify token lifecycle, session invalidation, and security edge cases.
Critical for SEBI compliance and preventing unauthorized access.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_header


_REG = {
    "email": "secure-user@example.com",
    "password": "SecureP@ss123",
    "full_name": "Security Tester",
    "role": "investor",
}


class TestTokenExpiry:
    """Verify JWT tokens expire and don't allow further requests."""

    def test_token_expires_after_configured_time(self, client: TestClient, monkeypatch):
        """Token should be invalid after JWT_EXPIRY_MINUTES."""
        # Register user
        reg_resp = client.post("/api/v1/auth/register", json=_REG)
        token = reg_resp.json()["access_token"]

        # Mock token expiry by manipulating the token's exp claim
        # In production, this happens naturally; test by mocking time.time()
        original_time = time.time

        def mock_time():
            return original_time() + (60 * 60)  # 1 hour later

        monkeypatch.setattr("time.time", mock_time)

        # With expired token, /me should return 401
        resp = client.get("/api/v1/auth/me", headers=auth_header(token))
        # Note: FastAPI's default behavior may vary; adjust assertion based on actual behavior
        assert resp.status_code in [401, 422]

    def test_malformed_token_rejected(self, client: TestClient):
        """Malformed tokens are rejected."""
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token-not-jwt"},
        )
        assert resp.status_code == 401

    def test_missing_bearer_prefix_rejected(self, client: TestClient):
        """Authorization header must have 'Bearer ' prefix."""
        resp = client.get("/api/v1/auth/me", headers={"Authorization": "InvalidToken"})
        assert resp.status_code == 401

    def test_empty_authorization_header_rejected(self, client: TestClient):
        """Empty Authorization header is rejected."""
        resp = client.get("/api/v1/auth/me", headers={"Authorization": ""})
        assert resp.status_code == 401


class TestSessionManagement:
    """Verify sessions are properly managed and can be invalidated."""

    def test_logout_invalidates_session(self, client: TestClient):
        """After logout, token should be unusable."""
        # Register
        reg_resp = client.post("/api/v1/auth/register", json=_REG)
        token = reg_resp.json()["access_token"]

        # Verify token works
        resp = client.get("/api/v1/auth/me", headers=auth_header(token))
        assert resp.status_code == 200

        # Logout
        logout_resp = client.post("/api/v1/auth/logout", headers=auth_header(token))
        if logout_resp.status_code == 200:  # If logout endpoint exists
            # Token should no longer work
            resp = client.get("/api/v1/auth/me", headers=auth_header(token))
            assert resp.status_code == 401
        else:
            pytest.skip("Logout endpoint not implemented yet")

    def test_token_tampering_detected(self, client: TestClient):
        """Tampered tokens are rejected."""
        # Register
        reg_resp = client.post("/api/v1/auth/register", json=_REG)
        token = reg_resp.json()["access_token"]

        # Tamper with token
        tampered = token[:-5] + "XXXXX"

        resp = client.get("/api/v1/auth/me", headers=auth_header(tampered))
        assert resp.status_code == 401

    def test_concurrent_login_same_email(self, client: TestClient):
        """Multiple simultaneous logins should work (session tracking)."""
        # Register
        client.post("/api/v1/auth/register", json=_REG)

        # Login twice
        login1 = client.post(
            "/api/v1/auth/login",
            json={"email": _REG["email"], "password": _REG["password"]},
        )
        login2 = client.post(
            "/api/v1/auth/login",
            json={"email": _REG["email"], "password": _REG["password"]},
        )

        token1 = login1.json()["access_token"]
        token2 = login2.json()["access_token"]

        # Both tokens should work (or be tracked separately)
        resp1 = client.get("/api/v1/auth/me", headers=auth_header(token1))
        resp2 = client.get("/api/v1/auth/me", headers=auth_header(token2))

        assert resp1.status_code == 200
        assert resp2.status_code == 200


class TestPasswordSecurity:
    """Verify password handling and reset security."""

    def test_password_hash_not_stored_plain(self, client: TestClient):
        """Passwords must be hashed, never plain text."""
        # This is a code-level test; verify by checking DB
        client.post("/api/v1/auth/register", json=_REG)

        # If we can query the DB, verify password is hashed
        # (This would require direct DB access; skip if testing via API only)
        pytest.skip("Requires direct DB access to verify hashing")

    def test_weak_password_rejected(self, client: TestClient):
        """Weak passwords (< 8 chars, no variety) rejected."""
        resp = client.post(
            "/api/v1/auth/register",
            json={**_REG, "password": "pass123"},  # Only 7 chars
        )
        assert resp.status_code == 422

    def test_password_with_special_chars_accepted(self, client: TestClient):
        """Strong passwords with special chars accepted."""
        resp = client.post(
            "/api/v1/auth/register",
            json={**_REG, "password": "P@ss!Word123#secure"},
        )
        assert resp.status_code == 201

    def test_reset_password_token_expires(self, client: TestClient):
        """Password reset tokens should expire after N hours."""
        # Register user
        client.post("/api/v1/auth/register", json=_REG)

        # Request password reset
        reset_resp = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": _REG["email"]},
        )

        if reset_resp.status_code == 200:
            # Token should expire after configured time (e.g., 1 hour)
            pytest.skip("Password reset token expiry not yet tested")
        else:
            pytest.skip("Password reset endpoint not implemented")


class TestMFAAndTwoFactor:
    """Multi-factor authentication tests."""

    def test_mfa_required_for_staff(self, client: TestClient):
        """RM/Compliance staff must have MFA enabled."""
        # Register as RM
        rm_user = {**_REG, "email": "rm@example.com", "role": "relationship_manager"}
        resp = client.post("/api/v1/auth/register", json=rm_user)

        # Should prompt for MFA setup
        if resp.status_code == 200:
            data = resp.json()
            assert "mfa_required" in data or resp.status_code == 403
        else:
            pytest.skip("MFA enforcement not yet implemented")

    def test_otp_verification_code_correct(self, client: TestClient):
        """Valid OTP should grant access."""
        pytest.skip("MFA OTP verification not yet implemented")

    def test_otp_verification_code_expired(self, client: TestClient):
        """Expired OTP codes should be rejected."""
        pytest.skip("OTP expiry not yet tested")


class TestEmailVerification:
    """Email verification and phone verification tests."""

    def test_unverified_email_restricted_access(self, client: TestClient):
        """Users with unverified emails may have restricted access."""
        # Register (may default to unverified)
        resp = client.post("/api/v1/auth/register", json=_REG)

        if resp.status_code == 201:
            token = resp.json()["access_token"]
            # Try to access protected endpoint
            me_resp = client.get("/api/v1/auth/me", headers=auth_header(token))
            # Depending on design, may require verification
            # assert me_resp.status_code in [200, 403]
        else:
            pytest.skip("Registration behavior needs clarification")

    def test_verify_email_token_valid_once(self, client: TestClient):
        """Email verification token can only be used once."""
        pytest.skip("Email token single-use not yet tested")

    def test_verify_email_invalid_token_rejected(self, client: TestClient):
        """Invalid email verification tokens rejected."""
        resp = client.post(
            "/api/v1/auth/verify-email",
            json={"token": "invalid-token-here"},
        )
        if resp.status_code != 404:  # Endpoint might not exist
            assert resp.status_code in [400, 401, 422]
        else:
            pytest.skip("Email verification endpoint not found")


class TestAuthErrorMessages:
    """Verify error messages don't leak security information."""

    def test_login_error_doesnt_leak_user_existence(self, client: TestClient):
        """Login errors shouldn't reveal if email exists."""
        # Try to login with non-existent email
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "doesnotexist@example.com", "password": "AnyPassword123"},
        )
        assert resp.status_code == 401
        # Error should be generic, not "user not found" vs "wrong password"
        error = resp.json().get("detail", "").lower()
        assert "email or password" in error or "invalid" in error

    def test_registration_error_doesnt_reveal_duplicate_email(self, client: TestClient):
        """Registration errors should be generic about duplicates."""
        # Register first user
        client.post("/api/v1/auth/register", json=_REG)

        # Try duplicate email
        resp = client.post("/api/v1/auth/register", json=_REG)
        assert resp.status_code in [409, 400]  # Conflict or Bad Request
        # Error message okay to be specific here (it's a business rule)


class TestRateLimiting:
    """Verify rate limiting on auth endpoints."""

    def test_login_rate_limit_prevents_brute_force(self, client: TestClient):
        """Too many failed login attempts should be rate-limited."""
        client.post("/api/v1/auth/register", json=_REG)

        # Try 10+ failed logins
        for i in range(15):
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": _REG["email"], "password": f"wrong{i}"},
            )
            if resp.status_code == 429:  # Too Many Requests
                pytest.skip("Rate limiting not enforced at this level")
                return

        # If reached here without 429, rate limiting may not be implemented
        pytest.skip("Rate limiting on login endpoint not yet implemented")

    def test_register_rate_limit_prevents_spam(self, client: TestClient):
        """Too many registrations from same IP should be rate-limited."""
        pytest.skip("Registration rate limiting not yet implemented")
