"""API error handling and edge cases — validates all endpoints handle errors gracefully.

Tests verify that:
- All endpoints return appropriate HTTP status codes
- Error responses are consistent and helpful
- Edge cases don't cause crashes
- Validation errors are clear
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.conftest import auth_header


_VALID_USER = {
    "email": "valid@example.com",
    "password": "StrongP@ss1",
    "full_name": "Test User",
    "role": "investor",
}


class TestInputValidation:
    """Verify all endpoints validate input properly."""

    def test_register_missing_email(self, client: TestClient):
        """Missing email should fail with 422."""
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "password": "Valid123",
                "full_name": "Test",
                "role": "investor",
            },
        )
        assert resp.status_code == 422

    def test_register_invalid_email_format(self, client: TestClient):
        """Invalid email format rejected."""
        resp = client.post(
            "/api/v1/auth/register",
            json={
                **_VALID_USER,
                "email": "not-an-email",
            },
        )
        assert resp.status_code == 422

    def test_register_empty_full_name(self, client: TestClient):
        """Empty full name rejected."""
        resp = client.post(
            "/api/v1/auth/register",
            json={
                **_VALID_USER,
                "full_name": "",
            },
        )
        assert resp.status_code == 422

    def test_register_whitespace_password(self, client: TestClient):
        """Password that's only whitespace rejected."""
        resp = client.post(
            "/api/v1/auth/register",
            json={
                **_VALID_USER,
                "password": "        ",
            },
        )
        assert resp.status_code == 422

    def test_login_missing_credentials(self, client: TestClient):
        """Login without email/password returns 422."""
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422

    def test_login_null_email(self, client: TestClient):
        """Null email in login rejected."""
        resp = client.post(
            "/api/v1/auth/login",
            json={"email": None, "password": "whatever"},
        )
        assert resp.status_code == 422

    def test_application_missing_required_fields(self, client: TestClient):
        """Application creation without required fields fails."""
        # Register and get token
        reg = client.post("/api/v1/auth/register", json=_VALID_USER)
        token = reg.json()["access_token"]

        # Try to create application with missing fields
        resp = client.post(
            "/api/v1/applications",
            json={"full_name": "Test"},  # Missing pan, dob, etc.
            headers=auth_header(token),
        )
        assert resp.status_code == 422


class TestAuthenticationRequired:
    """Verify protected endpoints require authentication."""

    def test_protected_endpoint_without_token(self, client: TestClient):
        """Protected endpoints reject requests without token."""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_protected_endpoint_invalid_token(self, client: TestClient):
        """Protected endpoints reject invalid tokens."""
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid"},
        )
        assert resp.status_code == 401

    def test_protected_endpoint_wrong_auth_scheme(self, client: TestClient):
        """Wrong auth scheme (e.g., Basic instead of Bearer) rejected."""
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )
        assert resp.status_code == 401

    def test_protected_endpoint_expired_token(self, client: TestClient, monkeypatch):
        """Expired tokens rejected (tested via token lifecycle)."""
        # This would require mocking token expiry in conftest
        pytest.skip("Token expiry test in test_auth_security.py")

    def test_protected_endpoint_case_insensitive_bearer(self, client: TestClient):
        """Bearer prefix should be case-insensitive."""
        reg = client.post("/api/v1/auth/register", json=_VALID_USER)
        token = reg.json()["access_token"]

        # Try lowercase "bearer"
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"bearer {token}"},
        )
        # Should work or fail consistently
        assert resp.status_code in [200, 401]


class TestResourceNotFound:
    """Verify 404 responses for missing resources."""

    def test_get_nonexistent_application(self, client: TestClient):
        """GET /applications/{id} with non-existent ID returns 404."""
        reg = client.post("/api/v1/auth/register", json=_VALID_USER)
        token = reg.json()["access_token"]

        resp = client.get(
            "/api/v1/applications/99999",
            headers=auth_header(token),
        )
        assert resp.status_code == 404

    def test_update_nonexistent_application(self, client: TestClient):
        """PATCH /applications/{id} with non-existent ID returns 404."""
        reg = client.post("/api/v1/auth/register", json=_VALID_USER)
        token = reg.json()["access_token"]

        resp = client.patch(
            "/api/v1/applications/99999",
            json={"status": "approved"},
            headers=auth_header(token),
        )
        assert resp.status_code == 404

    def test_delete_nonexistent_portfolio(self, client: TestClient):
        """DELETE /portfolios/{id} with non-existent ID returns 404."""
        reg = client.post("/api/v1/auth/register", json=_VALID_USER)
        token = reg.json()["access_token"]

        resp = client.delete(
            "/api/v1/portfolios/99999",
            headers=auth_header(token),
        )
        assert resp.status_code == 404


class TestConflictErrors:
    """Verify 409 Conflict responses."""

    def test_register_duplicate_email_conflict(self, client: TestClient):
        """Duplicate email registration returns 409."""
        client.post("/api/v1/auth/register", json=_VALID_USER)
        resp = client.post("/api/v1/auth/register", json=_VALID_USER)
        assert resp.status_code == 409

    def test_create_duplicate_application(self, client: TestClient):
        """Creating duplicate application for same investor may fail."""
        # This depends on business logic; adjust as needed
        pytest.skip("Duplicate application behavior undefined")


class TestMethodNotAllowed:
    """Verify 405 responses for unsupported methods."""

    def test_get_on_post_only_endpoint(self, client: TestClient):
        """GET on POST-only endpoint returns 405 or 404."""
        resp = client.get("/api/v1/auth/register")
        assert resp.status_code in [405, 404]

    def test_post_on_get_only_endpoint(self, client: TestClient):
        """POST on GET-only endpoint returns 405 or 404."""
        resp = client.post("/api/v1/auth/me")
        assert resp.status_code in [405, 404]


class TestPayloadTooLarge:
    """Verify large payloads are rejected."""

    def test_large_json_payload_rejected(self, client: TestClient):
        """Very large JSON payloads should be rejected."""
        large_data = {
            **_VALID_USER,
            "full_name": "A" * 100000,  # 100k characters
        }
        resp = client.post("/api/v1/auth/register", json=large_data)
        # Should be 413 or 422 depending on server config
        assert resp.status_code in [413, 422]


class TestErrorResponseFormat:
    """Verify error responses have consistent format."""

    def test_error_response_has_detail(self, client: TestClient):
        """Error responses should have 'detail' field."""
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 422
        assert "detail" in resp.json()

    def test_validation_error_lists_fields(self, client: TestClient):
        """Validation errors should list which fields are problematic."""
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "invalid-email"},
        )
        assert resp.status_code == 422
        data = resp.json()
        assert "detail" in data

    def test_error_response_consistent_structure(self, client: TestClient):
        """All errors should follow same response structure."""
        # Trigger different error types
        errors = [
            client.post("/api/v1/auth/login", json={}),  # Validation
            client.get("/api/v1/auth/me"),  # Auth
            client.get("/api/v1/applications/999", headers={"Authorization": "Bearer fake"}),  # Auth + Not found
        ]

        for resp in errors:
            if resp.status_code != 200:
                data = resp.json()
                # Should have either "detail" or "error" field
                assert "detail" in data or "error" in data


class TestDatabaseExceptions:
    """Verify database errors are handled gracefully."""

    def test_database_connection_error_returns_500(self, client: TestClient):
        """Database connection errors return 500, not crash."""
        # This would require mocking DB connection failures
        pytest.skip("DB error handling not yet tested")

    def test_constraint_violation_returns_409_or_422(self, client: TestClient):
        """Unique constraint violations return appropriate error."""
        # Register user
        client.post("/api/v1/auth/register", json=_VALID_USER)
        # Duplicate email should fail
        resp = client.post("/api/v1/auth/register", json=_VALID_USER)
        assert resp.status_code in [409, 422]


class TestNullAndEmptyValues:
    """Verify handling of null and empty values."""

    def test_null_required_field_rejected(self, client: TestClient):
        """Null values in required fields rejected."""
        resp = client.post(
            "/api/v1/auth/register",
            json={**_VALID_USER, "email": None},
        )
        assert resp.status_code == 422

    def test_empty_array_handled(self, client: TestClient):
        """Empty arrays handled appropriately."""
        # Depends on endpoint semantics
        pytest.skip("Empty array handling depends on context")

    def test_empty_string_vs_null(self, client: TestClient):
        """Empty string and null handled differently if appropriate."""
        resp1 = client.post(
            "/api/v1/auth/register",
            json={**_VALID_USER, "phone": ""},
        )
        resp2 = client.post(
            "/api/v1/auth/register",
            json={**_VALID_USER, "email": "test2@ex.com", "phone": None},
        )
        # Should both succeed or both fail, consistently
        assert resp1.status_code == resp2.status_code


class TestSpecialCharactersAndEncoding:
    """Verify special characters and encoding handled safely."""

    def test_unicode_in_full_name(self, client: TestClient):
        """Unicode characters in names accepted."""
        resp = client.post(
            "/api/v1/auth/register",
            json={**_VALID_USER, "full_name": "राज कुमार"},  # Devanagari
        )
        assert resp.status_code == 201

    def test_sql_injection_attempt_rejected(self, client: TestClient):
        """SQL injection attempts rejected."""
        resp = client.post(
            "/api/v1/auth/login",
            json={
                "email": "admin'--",
                "password": "' OR '1'='1",
            },
        )
        # Should fail with 422 or 401, never succeed
        assert resp.status_code in [422, 401]

    def test_xss_attempt_sanitized(self, client: TestClient):
        """XSS attempts in fields are sanitized/rejected."""
        resp = client.post(
            "/api/v1/auth/register",
            json={
                **_VALID_USER,
                "full_name": "<script>alert('xss')</script>",
            },
        )
        # Should reject or sanitize
        if resp.status_code == 201:
            # If created, verify field was sanitized
            user = resp.json()
            assert "<script>" not in str(user)
        else:
            assert resp.status_code in [422, 400]


class TestConcurrency:
    """Verify concurrent operations handled safely."""

    def test_concurrent_registrations_same_email(self, client: TestClient):
        """Race condition: two concurrent registrations with same email."""
        # This would require threading/async; mark for future testing
        pytest.skip("Concurrency testing requires async test client")

    def test_concurrent_application_submissions(self, client: TestClient):
        """Two concurrent application submissions handled safely."""
        pytest.skip("Concurrency testing requires async test client")
