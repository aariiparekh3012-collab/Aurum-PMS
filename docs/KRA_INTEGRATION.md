# KRA Integration Guide

This document explains the KYC Registration Agency (KRA) integration for real-time PAN + Aadhaar verification.

## Overview

The Aurum PMS platform integrates with **KRA vendors** to verify client identity before onboarding per **SEBI regulations**. Supported vendors:

- **CVL** (CDSL Ventures Ltd) — most common
- **NDML** (National Document Management Ltd)
- **CERSAI CKYC** (Central KYC Registry)

## Architecture

```
OnboardingApplication
    └─ SubmitKycUseCase
        └─ KycPort (abstract)
            ├─ KraKycAdapter (CVL/NDML) ← production
            ├─ CkycKycAdapter (CERSAI) ← alternative
            └─ FakeKycAdapter ← local dev/tests
```

The use case is **adapter-agnostic**; switching vendors is a config change:

```python
# app/api/dependencies.py
def get_kyc_adapter(settings: Settings) -> KycPort:
    if settings.environment == "production":
        return KraKycAdapter()  # Real vendor
    elif settings.environment == "staging":
        return KraKycAdapter()  # Vendor sandbox
    else:
        return FakeKycAdapter()  # Deterministic test stub
```

## Local Development (Mock Server)

Use the bundled mock KRA sandbox to test without vendor credentials.

### 1. Start Mock KRA Server

```bash
cd backend
uvicorn tests.mocks.kra_sandbox:app --port 8001
```

### 2. Configure .env

```env
KRA_BASE_URL=http://localhost:8001
KRA_API_KEY=test-key
ENVIRONMENT=local
```

### 3. Test Responses

The mock server responds based on PAN:

| PAN | Response | Notes |
|-----|----------|-------|
| `AAAPA1234A` | VERIFIED | Returns KRA reference |
| `BBBPB5678B` | VERIFIED | Any PAN in hardcoded list |
| `REJECTD1E` | REJECTED | Simulates name mismatch |
| `FRAUDZ1234` | REJECTED | Simulates fraud flag |
| `OTHERPAN99` | PENDING | Any other PAN → async |

### 4. Test Onboarding Flow

```bash
# Start the main app
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload

# In another terminal, create an application with a verified PAN
curl -X POST http://localhost:8000/api/v1/onboarding/applications \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Rajesh Kumar",
    "email": "rajesh@example.com",
    "mobile": "+919876543210",
    "pan": "AAAPA1234A",
    "investor_type": "individual",
    "proposed_investment_inr": 5000000
  }'
```

The onboarding will transition to `KYC_PENDING` → automatically verify via mock server.

## Sandbox Testing (Real Vendor)

To test against actual vendor sandboxes:

### CVL Sandbox

1. **Request sandbox credentials** at https://www.cvlkyc.com/enterprise
2. Set in `.env`:

```env
KRA_BASE_URL=https://sandbox.cvlkyc.com/api/v2
KRA_API_KEY=your_cvl_sandbox_api_key
ENVIRONMENT=staging
```

3. **Test PANs** provided by CVL in sandbox docs:
   - Verified: `ABCDE1234F` (name: "Test User")
   - Rejected: `REJECTPAN1` (name mismatch)

### NDML Sandbox

1. Request credentials at https://www.ndml.in/business/kyc-services
2. Set in `.env`:

```env
KRA_BASE_URL=https://kyc-api-sandbox.ndml.in/v1
KRA_API_KEY=your_ndml_sandbox_api_key
ENVIRONMENT=staging
```

## Production Deployment

### Prerequisites

1. **SEBI approval** — Your firm must be registered as a Portfolio Manager
2. **Vendor contract** — Execute a service agreement with CVL/NDML
3. **Live credentials** — Receive API keys from vendor
4. **Secrets management** — Store credentials in AWS Secrets Manager (not `.env`)

### Setup Steps

1. **Update config**:

```python
# app/core/config.py
from aws_secretsmanager import get_secret

def get_kra_settings(environment: str):
    if environment == "production":
        return get_secret("pms/kra/prod")  # Fetch from KMS
    return Settings()  # From .env for dev/staging
```

2. **Configure credentials** in AWS Secrets Manager:

```json
{
  "kra_base_url": "https://api.cvlkyc.com/api/v2",
  "kra_api_key": "prod-api-key-xxxxx",
  "kra_timeout_seconds": 15,
  "kra_max_retries": 3
}
```

3. **Deploy** with restricted IAM role:

```yaml
# IAM Policy
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:pms/kra/prod-*"
    }
  ]
}
```

4. **Monitor & alert**:

```python
# Structured logging with correlation IDs
log.info(
    "KRA verification completed",
    extra={
        "request_id": request_id,
        "verified": verified,
        "duration_ms": elapsed_ms,
        "status": status,
    },
)
```

## API Contract

### Request

```http
POST /verify
Authorization: Bearer {api_key}
Content-Type: application/json
X-Request-ID: {idempotency_key}

{
  "pan": "AAAPA1234A",
  "aadhaar_last4": "1234",
  "name": "Rajesh Kumar",
  "request_id": "uuid-for-idempotency"
}
```

### Response (Verified)

```json
{
  "status": "VERIFIED",
  "kra_reference": "KRA-1234-1234",
  "pan": "AAAPA1234A",
  "aadhaar_last4": "1234",
  "name": "Rajesh Kumar",
  "verified_at": "2026-06-08T10:30:00Z",
  "reason": null
}
```

### Response (Rejected)

```json
{
  "status": "REJECTED",
  "kra_reference": "KRA-REJECT-abc123",
  "pan": "REJECTD1E",
  "aadhaar_last4": "1234",
  "name": "Wrong Name",
  "verified_at": null,
  "reason": "Name/PAN mismatch"
}
```

## Error Handling

| Scenario | Behavior | Action |
|----------|----------|--------|
| Network timeout | Retry 3x (exponential backoff) | User told to retry onboarding |
| Invalid PAN format | Reject immediately (4xx) | Return validation error |
| KRA service down (5xx) | Retry 3x, then fail | Alert ops; manual review queue |
| PII exposure in logs | Never log full PAN/Aadhaar | Use masking (last 4 only) |

## Compliance & Security

### PII Handling

- ✅ Log only last 4 digits of PAN/Aadhaar for debugging
- ✅ Encrypt PII at rest in database (via `PII_ENCRYPTION_KEY`)
- ✅ Use HTTPS for all vendor API calls
- ✅ Rotate API keys quarterly

### Audit Trail

Every KYC verification is recorded in `audit_logs` table:

```sql
SELECT * FROM audit_logs
WHERE event_type = 'kyc_verified'
AND entity_id = 'app-uuid'
ORDER BY created_at DESC;
```

Output includes:
- Request timestamp
- KRA reference ID
- Verification result (VERIFIED/REJECTED)
- Officer who initiated
- Operator correlation ID

## Testing

### Unit Tests

```python
def test_kra_verify_valid_pan():
    adapter = KraKycAdapter()
    result = adapter.verify(
        pan="AAAPA1234A",
        aadhaar_last4="1234",
        name="Rajesh Kumar",
    )
    assert result.verified is True
    assert result.source == "kra"

def test_kra_verify_invalid_pan():
    adapter = KraKycAdapter()
    with pytest.raises(ValidationError) as exc:
        adapter.verify(pan="INVALID", aadhaar_last4="1234", name="Test")
    assert exc.value.code == "invalid_pan"
```

### Integration Tests

```bash
# With mock server running on :8001
pytest tests/integration/test_kyc_flow.py -v
```

### Load Testing

```bash
# Simulate 100 concurrent onboarding requests
locust -f tests/load/onboarding_load.py --host=http://localhost:8000
```

## Troubleshooting

### "KRA_BASE_URL not configured"

**Cause:** Environment variable missing or empty.

**Fix:**
```bash
# Check .env or environment
echo $KRA_BASE_URL

# Update .env
KRA_BASE_URL=https://sandbox.cvlkyc.com/api/v2
```

### "KRA verification timed out"

**Cause:** Vendor API slow or unreachable.

**Fix:**
1. Check vendor status page
2. Increase timeout (in `KraKycAdapter.__init__`): `self._timeout = 30`
3. Check network ACLs / firewalls if on-prem

### "Idempotency key rejected"

**Cause:** Vendor requires unique X-Request-ID per request.

**Fix:** Ensure uuid is generated fresh (library handles this).

## Roadmap

- [ ] **CKYC support** — Add CkycKycAdapter for CERSAI as alternative vendor
- [ ] **Aadhaar eSign** — Automate PMS agreement signing via NSDL/UIDAI
- [ ] **Demat verification** — Query NSDL/CDSL for existing holdings
- [ ] **Webhook callbacks** — Handle async KRA responses (if vendor supports)

## Further Reading

- SEBI (Portfolio Managers) Regulations, 2020
- CVL KRA API documentation: https://docs.cvlkyc.com
- NDML API docs: https://docs.ndml.in
- CERSAI CKYC: https://www.cersai.org
