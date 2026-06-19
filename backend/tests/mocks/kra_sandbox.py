"""Mock KRA (KYC Registration Agency) sandbox server for local development & testing.

This simulates the behavior of real KRA vendors (CVL, NDML, etc.) and allows
testing the onboarding flow without live credentials.

Run: uvicorn tests.mocks.kra_sandbox:app --port 8001

Then set in .env:
  KRA_BASE_URL=http://localhost:8001
  KRA_API_KEY=test-key
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException, Header, Request
from pydantic import BaseModel

app = FastAPI(title="Mock KRA Sandbox", version="1.0")


class VerifyRequest(BaseModel):
    pan: str
    aadhaar_last4: str
    name: str
    request_id: str | None = None


class VerifyResponse(BaseModel):
    status: str  # VERIFIED | REJECTED | PENDING
    kra_reference: str
    pan: str
    aadhaar_last4: str
    name: str
    verified_at: str | None = None
    reason: str | None = None


# Deterministic test data
VERIFIED_PANS = {
    "AAAPA1234A",  # Will verify
    "BBBPB5678B",
    "CCCPC9012C",
}

REJECTED_PANS = {
    "REJECTD1E",  # Will reject (simulates name mismatch)
    "FRAUDZ1234",  # Will reject (fraud flag)
}


@app.post("/verify", response_model=VerifyResponse)
async def verify_identity(
    request_body: VerifyRequest,
    authorization: str | None = Header(None),
    x_request_id: str | None = Header(None),
):
    """Simulate KRA identity verification endpoint.

    Query params for testing:
    - PAN in VERIFIED_PANS → returns VERIFIED
    - PAN in REJECTED_PANS → returns REJECTED with reason
    - Other PANs → returns PENDING (simulates async vendor)
    """
    # Auth check
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    # Input validation
    if len(request_body.pan) != 10:
        raise HTTPException(status_code=400, detail="PAN must be 10 characters")
    if not request_body.aadhaar_last4.isdigit() or len(request_body.aadhaar_last4) != 4:
        raise HTTPException(status_code=400, detail="Aadhaar last4 must be 4 digits")
    if not request_body.name.strip():
        raise HTTPException(status_code=400, detail="Name is required")

    # Deterministic responses based on PAN for testing
    pan_upper = request_body.pan.upper()
    request_id = request_body.request_id or x_request_id or str(uuid.uuid4())

    if pan_upper in VERIFIED_PANS:
        return VerifyResponse(
            status="VERIFIED",
            kra_reference=f"KRA-{pan_upper[-4:]}-{request_body.aadhaar_last4}",
            pan=request_body.pan,
            aadhaar_last4=request_body.aadhaar_last4,
            name=request_body.name,
            verified_at=datetime.utcnow().isoformat(),
            reason=None,
        )

    elif pan_upper in REJECTED_PANS:
        reason = "Name/PAN mismatch" if "REJECT" in pan_upper else "Fraud/Inactive PAN"
        return VerifyResponse(
            status="REJECTED",
            kra_reference=f"KRA-REJECT-{request_id[:8]}",
            pan=request_body.pan,
            aadhaar_last4=request_body.aadhaar_last4,
            name=request_body.name,
            verified_at=None,
            reason=reason,
        )

    else:
        # Simulate async/pending response for unknown PANs
        return VerifyResponse(
            status="PENDING",
            kra_reference=f"KRA-PENDING-{request_id[:8]}",
            pan=request_body.pan,
            aadhaar_last4=request_body.aadhaar_last4,
            name=request_body.name,
            verified_at=None,
            reason="Verification in progress, check back later",
        )


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "Mock KRA Sandbox"}


@app.get("/docs")
async def docs():
    """OpenAPI docs at /docs"""
    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
