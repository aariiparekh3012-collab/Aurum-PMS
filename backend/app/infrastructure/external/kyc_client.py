"""Re-exports from kra_client for backward compatibility.

All KYC adapter implementations now live in kra_client.py (Surepass).
"""
from app.infrastructure.external.kra_client import (  # noqa: F401
    FakeKycAdapter,
    KraKycAdapter,
    SurepassKycAdapter,
)
