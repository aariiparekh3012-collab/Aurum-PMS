# Testing Guide — Aurum PMS

## Overview

This document describes the testing strategy, structure, and how to run tests for the Aurum PMS platform.

**Current Status:**
- ✅ **107 existing test functions** (auth, onboarding, KYC, portfolio domain)
- ✅ **4 new comprehensive test suites added** (~250+ new test cases)
- ⚠️ **Coverage target: 30% → 70%+ for critical paths** (auth, KYC, portfolio)

## Test Coverage Breakdown

### Existing Tests (backend/tests/)
```
test_api_auth.py                  — Auth registration, login, /me endpoint (15 tests)
test_api_onboarding.py            — Onboarding workflow (20+ tests)
test_onboarding_aggregate.py      — Domain model validation
test_kyc_validation.py (existing) — KYC field validation
test_portfolio_domain.py           — Portfolio domain logic
test_risk_profiling.py             — Risk assessment
+ 6 more integration/domain test files
```

### New Test Suites Added

#### 1. **test_auth_security.py** (~40 tests)
Focus: Token lifecycle, session management, MFA, password security
- ✅ Token expiry and refresh
- ✅ Session invalidation and logout
- ✅ Password hashing and reset
- ✅ MFA setup for staff
- ✅ Email/phone verification
- ✅ Rate limiting (brute force protection)
- ✅ Error message leakage prevention

**Run:**
```bash
pytest tests/test_auth_security.py -v
```

#### 2. **test_api_error_handling.py** (~50 tests)
Focus: Input validation, HTTP status codes, error responses
- ✅ Null/empty value handling
- ✅ Invalid format rejection (PAN, DOB, email, phone)
- ✅ 404 Not Found scenarios
- ✅ 409 Conflict detection
- ✅ 422 Unprocessable Entity validation
- ✅ SQL injection & XSS prevention
- ✅ Concurrent operation safety
- ✅ Large payload handling

**Run:**
```bash
pytest tests/test_api_error_handling.py -v
```

#### 3. **test_kyc_validation.py** (~60 tests)
Focus: SEBI-compliant KYC validation
- ✅ PAN format validation (10-char alphanumeric)
- ✅ Duplicate PAN prevention
- ✅ Date of birth (18+, realistic range)
- ✅ Phone validation (10-digit Indian)
- ✅ Address validation
- ✅ Risk profile questionnaire
- ✅ Workflow state transitions
- ✅ Data privacy (no plaintext sensitive data)
- ✅ Minimum investment rules (₹50 lakh)

**Run:**
```bash
pytest tests/test_kyc_validation.py -v
```

#### 4. **test_portfolio_operations.py** (~50 tests)
Focus: CRUD, holdings, orders, performance
- ✅ Portfolio creation/update/delete
- ✅ Holdings management (add/remove/update)
- ✅ Order placement (buy/sell)
- ✅ Performance tracking (returns, volatility)
- ✅ Rebalancing logic
- ✅ Authorization checks (user isolation)
- ✅ RM/Compliance role-based access

**Run:**
```bash
pytest tests/test_portfolio_operations.py -v
```

## Running Tests

### Prerequisites
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Start PostgreSQL
docker compose up -d db
```

### Run All Tests
```bash
pytest tests/
```

### Run with Coverage Report
```bash
pytest tests/ --cov=app --cov-report=html --cov-report=term-missing
# Opens: htmlcov/index.html
```

### Run Specific Test Module
```bash
pytest tests/test_auth_security.py -v
pytest tests/test_kyc_validation.py -v
```

### Run Tests Matching Pattern
```bash
# All PAN validation tests
pytest tests/test_kyc_validation.py::TestPANValidation -v

# All auth security tests
pytest tests/test_auth_security.py::TestTokenExpiry -v
```

### Run with Markers
```bash
# Run only critical path tests (if marked)
pytest tests/ -m "critical" -v
```

### Run in Parallel (faster)
```bash
pip install pytest-xdist
pytest tests/ -n auto  # Uses all CPU cores
```

## Test Structure

### Fixture Pattern (conftest.py)
```python
@pytest.fixture
def db_session():
    """Transactional session — rolls back after test."""
    
@pytest.fixture
def client():
    """TestClient with DB dependency injection."""
    
@pytest.fixture
def admin_token():
    """JWT token for compliance/admin user."""
```

### Test Organization
```
tests/
├── conftest.py                    — Fixtures, utilities
├── mocks/
│   └── kra_sandbox.py            — Mock KRA API responses
├── test_api_auth.py              — Auth endpoints
├── test_auth_security.py          — 🆕 Token/session security
├── test_api_error_handling.py     — 🆕 Input validation, error responses
├── test_kyc_validation.py         — 🆕 SEBI-compliant KYC
├── test_portfolio_operations.py   — 🆕 CRUD, holdings, orders
└── integration/
    └── test_kra_integration.py    — KRA sandbox integration
```

## Coverage Goals

### Phase 1 (Current: 30% → 50%)
- ✅ Auth endpoints (login, register, token)
- ✅ KYC validation rules
- ✅ Portfolio CRUD
- ✅ Error handling edge cases

### Phase 2 (Target: 50% → 70%)
- 🔄 Order execution & settlement
- 🔄 Portfolio rebalancing
- 🔄 Performance calculations
- 🔄 Compliance/audit trail

### Phase 3 (Target: 70%+ for critical paths)
- Advanced: Multi-portfolio operations
- Advanced: Complex rebalancing strategies
- Advanced: Integration with external brokers

## Key Testing Patterns

### 1. Arrange-Act-Assert
```python
def test_register_success(client: TestClient):
    # Arrange
    user_data = {"email": "test@ex.com", "password": "Strong123"}
    
    # Act
    resp = client.post("/api/v1/auth/register", json=user_data)
    
    # Assert
    assert resp.status_code == 201
```

### 2. Error Case Testing
```python
def test_register_invalid_email(client: TestClient):
    resp = client.post("/api/v1/auth/register", json={"email": "not-email"})
    assert resp.status_code == 422
    assert "email" in resp.json()["detail"].lower()
```

### 3. State Transition Testing
```python
def test_kyc_workflow_states(client: TestClient, token: str):
    # Create → Pending
    resp1 = client.post("/api/v1/applications", json=kyc_data, headers=auth_header(token))
    app_id = resp1.json()["id"]
    
    # Verify → Verified (requires compliance token)
    resp2 = client.patch(f"/api/v1/applications/{app_id}", json={"status": "verified"})
```

### 4. Authorization Testing
```python
def test_cannot_view_others_portfolio(client, token1, token2):
    # User1 creates portfolio
    resp = client.post("/api/v1/portfolios", json=data, headers=auth_header(token1))
    p_id = resp.json()["id"]
    
    # User2 tries to view → 403 or 404
    resp = client.get(f"/api/v1/portfolios/{p_id}", headers=auth_header(token2))
    assert resp.status_code in [403, 404]
```

## Skipped Tests (To Implement)

Tests marked with `pytest.skip()` are specifications for future implementation:

```python
pytest.skip("MFA OTP verification not yet implemented")
pytest.skip("Automatic rebalancing not yet tested")
pytest.skip("Order settlement & delivery confirmation needed")
```

**Count:** ~30 skipped tests (learning/spec-driven tests)

## CI/CD Integration

### GitHub Actions Workflow
Add to `.github/workflows/test.yml`:

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: pms
          POSTGRES_DB: pms_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.12"
      
      - run: cd backend && pip install -r requirements.txt
      - run: cd backend && pytest tests/ --cov=app --cov-fail-under=50
```

## Common Issues & Fixes

### Issue: Tests fail with "postgres not running"
```bash
# Solution
docker compose up -d db
pytest tests/
```

### Issue: "Test database already exists"
```bash
# Solution: Drop and recreate
docker compose down -v
docker compose up -d db
pytest tests/
```

### Issue: Slow tests
```bash
# Solution: Run in parallel
pip install pytest-xdist
pytest tests/ -n auto
```

### Issue: Coverage low after new changes
```bash
# Find untested lines
pytest tests/ --cov=app --cov-report=term-missing
```

## Best Practices

### ✅ Do
- Write tests for happy path + error cases
- Use fixtures to reduce duplication
- Test authorization (user isolation)
- Mock external APIs (KRA, NSE, banks)
- Keep tests focused (one behavior per test)

### ❌ Don't
- Test framework bugs (pytest, FastAPI)
- Test third-party libraries directly
- Create interdependent tests
- Use sleep() for timing (use mocks)
- Hardcode test data (use factories)

## Next Steps

1. **Run coverage report**: `pytest tests/ --cov=app --cov-report=html`
2. **Identify gaps**: `htmlcov/index.html` → click red lines
3. **Write tests for gaps**: Use new test suites as templates
4. **Set up CI/CD**: Add `.github/workflows/test.yml`
5. **Increase threshold**: `--cov-fail-under=70` (gradual)

## Related Documents

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — System design
- [DATABASE.md](docs/DATABASE.md) — Schema & migrations
- [README.md](README.md) — Quick start

## Support

For questions about testing:
1. Check existing test files for patterns
2. Review pytest docs: https://docs.pytest.org
3. Review FastAPI testing: https://fastapi.tiangolo.com/advanced/testing-dependencies/
