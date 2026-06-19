"""End-to-end smoke test — drives a full onboarding from DRAFT to ACTIVE.

Run against a live backend (uses the bundled Fake* KYC/bank/eSign adapters, so no
real vendor credentials are needed):

    # 1) start the backend (see README) so http://localhost:8000 is up
    # 2) then:
    python scripts/smoke_test.py

It prints the status after every step so you have visible output to show.
"""
from __future__ import annotations

import sys

import httpx

BASE = "http://localhost:8000/api/v1"


def main() -> int:
    with httpx.Client(base_url=BASE, timeout=15) as c:
        # 0) get a dev JWT (compliance role can also approve at the end)
        token = c.post("/auth/token", json={"username": "smoke-test@local", "role": "compliance"}).json()["access_token"]
        c.headers["Authorization"] = f"Bearer {token}"
        print("auth          : got dev token")

        # 1) create application
        r = c.post(
            "/onboarding/applications",
            json={
                "investor_type": "individual",
                "full_name": "Asha Rao",
                "email": "asha@example.com",
                "mobile": "9876543210",
                "pan": "ABCDE1234F",
                "proposed_investment_inr": 5_000_000,
            },
        )
        r.raise_for_status()
        app = r.json()
        app_id = app["id"]
        print(f"create        : {app['status']:<18} id={app_id}")

        # 2) submit KYC (FakeKyc verifies any PAN not ending in 'Z')
        r = c.post(
            f"/onboarding/applications/{app_id}/kyc",
            json={
                "aadhaar_full": "234567890123",
                "bank_account_number": "12345678901",
                "bank_ifsc": "HDFC0001234",
                "bank_holder_name": "Asha Rao",
                "demat_bo_id": "1234567812345678",
                "demat_depository": "NSDL",
            },
        )
        r.raise_for_status()
        print(f"submit_kyc    : {r.json()['status']:<18} source={r.json()['kyc_source']}")

        # 3) risk profile (5 answers)
        r = c.post(
            f"/onboarding/applications/{app_id}/risk-profile",
            json={"answers": [{"question_id": f"q{i}", "weight": w}
                              for i, w in enumerate([3, 4, 3, 4, 5])]},
        )
        r.raise_for_status()
        print(f"risk_profile  : {r.json()['status']:<18} category={r.json()['risk_category']}")

        # 4) confirm eSign (FakeEsign always returns SIGNED)
        r = c.post(
            f"/onboarding/applications/{app_id}/esign/confirm",
            json={"transaction_id": "TXN-SANDBOX"},
        )
        r.raise_for_status()
        print(f"esign_confirm : {r.json()['status']:<18}")

        # 5) compliance approval
        r = c.post(
            f"/onboarding/applications/{app_id}/decision",
            json={"approve": True},
        )
        r.raise_for_status()
        final = r.json()["status"]
        print(f"decision      : {final:<18}")

    print("\nRESULT:", "PASS ✅" if final == "active" else f"UNEXPECTED ({final}) ❌")
    return 0 if final == "active" else 1


if __name__ == "__main__":
    sys.exit(main())
