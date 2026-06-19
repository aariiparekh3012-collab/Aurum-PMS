# Aadhaar eSign Integration Guide

This document explains the Aadhaar eSign integration for digitally signing the PMS agreement using NSDL/UIDAI infrastructure.

## Overview

**Aadhaar eSign** enables clients to digitally sign the PMS agreement using their Aadhaar-based biometric authentication (fingerprint, iris, or OTP). This is SEBI-compliant and required before funds can be accepted.

### Vendors

- **NSDL eSign** (recommended): https://esign.nsdl.com
- **Yodlee eSign** (alternative): https://api.yodleesesign.com
- **Other ASPs**: DigiSigns, eMudhra, etc.

## Architecture

```
Client                      Our API                    eSign ASP (NSDL)
  │                           │                           │
  ├─POST /esign/initiate────►│                           │
  │                           │─POST /initiate──────────►│
  │                           │◄─transaction_id──────────│
  │◄─{ transaction_id }───────│                           │
  │                           │                           │
  ├─Redirect to eSign────────────────────────────────────►│
  │                                                        │
  │◄────User signs with Aadhaar────────────────────────────│
  │                                                        │
  │                           │◄─POST /callback──────────│
  │                           │  (webhook from NSDL)     │
  │                           │                           │
  │                           ├─Update app status        │
  │                           ├─Publish event            │
  │                           │                           │
  │◄────Redirect to success───┤                           │
```

## Flow

### 1. Client Initiates eSign

```http
POST /api/v1/onboarding/applications/{application_id}/esign/initiate
Authorization: Bearer <token>

Response:
{
  "transaction_id": "TXN-abc123...",
  "redirect_url": "https://esign-sandbox.nsdl.com/transaction/TXN-abc123...",
  "message": "Redirect user to redirect_url to complete Aadhaar eSign"
}
```

### 2. Frontend Redirects User

The frontend redirects the user to the `redirect_url` where they:
- Enter Aadhaar number
- Choose authentication method (fingerprint, iris, OTP)
- Complete biometric/OTP verification
- Review and accept the agreement

### 3. eSign ASP Posts Callback

After signing, NSDL posts to our webhook:

```http
POST /api/v1/onboarding/applications/{application_id}/esign/callback

{
  "transaction_id": "TXN-abc123...",
  "status": "SIGNED",
  "esign_reference": "ESIGN-xyz789...",
  "signed_document_url": "https://esign.nsdl.com/documents/signed-doc.pdf",
  "timestamp": "2026-06-08T10:30:00Z"
}
```

We validate the signature, update application status, and publish an event.

### 4. Return to Client Portal

Frontend detects callback completion and returns to onboarding success page.

## Configuration

### Environment Variables

```bash
# Sandbox
ESIGN_BASE_URL=https://esign-sandbox.nsdl.com/api/v1
ESIGN_API_KEY=your_sandbox_api_key

# Production
ESIGN_BASE_URL=https://esign.nsdl.com/api/v1
ESIGN_API_KEY=your_production_api_key

# Required for webhook callbacks
API_BASE_URL=https://api.aurum.pms  # Public API URL
```

### Setup Steps

1. **Register with NSDL**
   - Visit https://www.nsdl.com/
   - Apply for eSign ASP credentials
   - Receive API key and base URL

2. **Configure Credentials**
   ```bash
   # .env
   ESIGN_BASE_URL=https://esign-sandbox.nsdl.com/api/v1
   ESIGN_API_KEY=your-key-here
   API_BASE_URL=https://api.aurum.pms
   ```

3. **Test in Sandbox**
   - Use test Aadhaar numbers provided by NSDL
   - Verify callback webhook is reachable

4. **Deploy to Production**
   - Update ESIGN_BASE_URL to production endpoint
   - Update ESIGN_API_KEY with production credentials
   - Ensure webhook endpoint is HTTPS and accessible

## Implementation Details

### Backend

**Enhanced eSign Adapter** (`app/infrastructure/external/esign_client.py`):
- Retry logic (3x exponential backoff)
- Timeout handling (20s for initiate, 15s for fetch)
- Signature verification (HMAC-SHA256)
- Error handling for common scenarios

**eSign Use Case** (`app/application/onboarding/use_cases/esign_agreement.py`):
- `initiate()` - Start eSign, generate agreement PDF
- `confirm()` - Poll for signature (direct integration)
- `handle_esign_callback()` - Process webhook callback

**API Endpoints**:
- `POST /onboarding/applications/{id}/esign/initiate` - Start eSign
- `POST /onboarding/applications/{id}/esign/confirm` - Confirm (polling)
- `POST /onboarding/applications/{id}/esign/callback` - Webhook (async)

### Frontend

**eSign Flow Component**:
- Display agreement PDF
- Show "Sign with Aadhaar" button
- Handle redirect to NSDL
- Detect callback completion
- Display success/error messages

## Testing

### Unit Tests

```python
def test_esign_initiate():
    """Test eSign initiation."""
    adapter = AadhaarEsignAdapter()
    txn_id = adapter.initiate(
        application_id="app-123",
        document_bytes=b"PDF content"
    )
    assert txn_id.startswith("TXN-")

def test_esign_fetch_result():
    """Test fetching signature status."""
    adapter = AadhaarEsignAdapter()
    result = adapter.fetch_result(transaction_id="TXN-123")
    assert isinstance(result, EsignResult)
    assert result.signed is bool
```

### Integration Tests

```python
def test_esign_full_flow():
    """Test complete eSign workflow."""
    # 1. Initiate
    response = client.post(
        "/api/v1/onboarding/applications/app-123/esign/initiate",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    txn_id = response.json()["transaction_id"]

    # 2. Simulate callback
    response = client.post(
        "/api/v1/onboarding/applications/app-123/esign/callback",
        json={
            "transaction_id": txn_id,
            "status": "SIGNED",
            "esign_reference": "ESIGN-xyz",
            "signed_document_url": "https://..."
        }
    )
    assert response.status_code == 200

    # 3. Verify application is signed
    app = db.query(OnboardingApplication).get("app-123")
    assert app.status == OnboardingStatus.UNDER_REVIEW  # Auto-transitions after sign
```

### Manual Testing

```bash
# 1. Start onboarding
curl -X POST http://localhost:8000/api/v1/onboarding/applications \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{...application data...}'

# 2. Progress to KYC, risk profile, etc.
# ...

# 3. Initiate eSign
curl -X POST http://localhost:8000/api/v1/onboarding/applications/<id>/esign/initiate \
  -H "Authorization: Bearer <token>"

# Returns:
# {
#   "transaction_id": "TXN-...",
#   "redirect_url": "https://esign-sandbox.nsdl.com/transaction/TXN-..."
# }

# 4. Visit redirect_url in browser
# 5. Complete eSign process
# 6. Webhook callback is received automatically
```

## Compliance & Security

### SEBI Compliance

- ✅ Digital signature via Aadhaar (NSDL)
- ✅ Non-repudiation guaranteed
- ✅ Audit trail (all eSign events logged)
- ✅ Document retention (signed PDFs archived)

### Security

- ✅ HTTPS-only for all eSign API calls
- ✅ Signature verification on callbacks (HMAC-SHA256)
- ✅ Timeout protection (20-30s)
- ✅ Retry logic with exponential backoff
- ✅ No PII in logs (only transaction IDs)

### Idempotency

eSign callbacks include `transaction_id` for idempotency. If the same callback is received twice:
1. Application already has `esign_reference` set
2. Event already published
3. Second webhook is ignored

## Troubleshooting

### "Transaction not found"

**Cause**: Transaction ID expired or incorrect.

**Fix**:
- Check `transaction_id` matches
- Verify ESIGN_BASE_URL is correct
- Test in sandbox first

### "Callback not received"

**Cause**: NSDL cannot reach our webhook.

**Fix**:
- Verify `API_BASE_URL` is public and HTTPS
- Check firewall/load balancer allows POST
- Verify webhook path: `/api/v1/onboarding/applications/{id}/esign/callback`
- Test: `curl -X POST https://your-api.com/api/v1/onboarding/applications/test-id/esign/callback`

### "Signature verification failed"

**Cause**: HMAC signature doesn't match.

**Fix**:
- Verify ESIGN_API_KEY is correct (typo check)
- Check payload is not modified
- Compare signature hex string case

### User gets stuck on eSign page

**Cause**: Callback not processed or redirects not configured.

**Fix**:
- Check logs for webhook callback receipt
- Verify application status updated to `UNDER_REVIEW`
- Test callback endpoint: `curl -X POST http://localhost:8000/api/v1/onboarding/applications/<id>/esign/callback -d '{...}'`

## Performance

- **Initiate latency**: 1-2s (HTTP to NSDL)
- **Callback latency**: < 100ms (process webhook)
- **Polling latency**: 1-2s per fetch (HTTP to NSDL)

For best UX, use async webhook callbacks instead of polling.

## Future Enhancements

- [ ] **Multi-language support** - Agreement in regional languages
- [ ] **Biometric choice** - Let users pick fingerprint vs iris vs OTP
- [ ] **Signature timestamps** - Include timezone in audit trail
- [ ] **Signed PDF download** - Allow clients to download signed agreement
- [ ] **Batch signing** - Multiple documents per session
- [ ] **Hardware token support** - For high-value clients

## References

- SEBI (Portfolio Managers) Regulations, 2020
- NSDL eSign API docs: https://docs.nsdl.com/esign
- Aadhaar Act, 2016
- IT Act, 2000 (digital signatures)
