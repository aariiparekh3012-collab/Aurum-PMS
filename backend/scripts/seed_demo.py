"""Seed demo data via the public API (no DB internals required).

Drives the real onboarding endpoints to create a handful of clients end-to-end, then
populates reference master data, portfolio accounts, holdings, trades, and performance
history so every page in the frontend shows realistic data.

Prereq: backend running (uvicorn) + DB migrated (alembic upgrade head).

    python scripts/seed_demo.py
    # or point at another host:
    BASE_URL=http://localhost:8000/api/v1 python scripts/seed_demo.py

Uses the local-only /auth/dev-token for the compliance actor (approve + provision),
which exists when ENVIRONMENT != production. Safe to re-run: duplicate PANs are
skipped and the run continues.
"""
from __future__ import annotations

import os
import random
import sys
from datetime import date, timedelta

import httpx

BASE = os.getenv("BASE_URL", "http://localhost:8000/api/v1")

# ── Onboarding applicants ────────────────────────────────────────────────────
# (name, email, pan, mobile, investment ₹, demat, risk weights)
# These 4 go all the way through to "active" client status.
APPLICANTS = [
    ("Asha Rao",      "asha@example.com",    "ABCDE1234F", "9876543210", 5_000_000,  "NSDL", [2, 2, 1, 2, 2]),
    ("Vikram Mehta",  "vikram@example.com",  "PQRST5678K", "9811111111", 12_000_000, "CDSL", [3, 3, 4, 3, 3]),
    ("Neha Kapoor",   "neha@example.com",    "LMNOP4321J", "9822222222", 25_000_000, "NSDL", [5, 4, 5, 4, 5]),
    ("Rohan Iyer",    "rohan@example.com",   "FGHIJ8765D", "9833333333", 8_000_000,  "CDSL", [3, 2, 3, 4, 3]),
]

# These 2 stay in the compliance queue (under_review) so the review page isn't empty.
PENDING_APPLICANTS = [
    ("Priya Sharma",  "priya@example.com",   "XYZAB9876G", "9844444444", 15_000_000, "NSDL", [4, 3, 4, 4, 3]),
    ("Arjun Nair",    "arjun@example.com",   "MNOPQ5432H", "9855555555", 7_500_000,  "CDSL", [2, 3, 2, 3, 2]),
]

# ── Realistic NSE stock prices (symbol -> price in ₹) ────────────────────────
# Used to compute realistic paise values
STOCK_PRICES = {
    "RELIANCE": 2950,
    "TCS":      3890,
    "HDFCBANK": 1720,
    "INFY":     1600,
    "ICICIBANK": 1280,
    "BAJFINANCE": 7100,
    "ASIANPAINT": 2850,
    "MARUTI":   13200,
    "SUNPHARMA": 1740,
    "TITAN":    3700,
    "WIPRO":     520,
    "NESTLEIND": 2450,
    "ULTRACEMCO": 12000,
    "HCLTECH":  1750,
    "AXISBANK":  1200,
}


def _dev_token(c: httpx.Client, role: str) -> str:
    r = c.post("/auth/token", json={"username": f"seed.{role}", "role": role})
    r.raise_for_status()
    return r.json()["access_token"]


# ── Phase 1: Onboarding ───────────────────────────────────────────────────────

def seed_one(c: httpx.Client, applicant, approve: bool = True) -> str | None:
    """Seed one applicant through the full onboarding flow.
    If approve=False, leaves the application at under_review (for compliance demo)."""
    name, email, pan, mobile, inv, depo, weights = applicant
    r = c.post("/onboarding/applications", json={
        "investor_type": "individual", "full_name": name, "email": email,
        "mobile": mobile, "pan": pan, "proposed_investment_inr": inv,
    })
    if r.status_code >= 400:
        print(f"  skip {name}: {r.json().get('error', {}).get('message', r.text)}")
        return None
    app_id = r.json()["id"]

    c.post(f"/onboarding/applications/{app_id}/kyc", json={
        "aadhaar_full": "234567890123", "bank_account_number": "12345678901",
        "bank_ifsc": "HDFC0001234", "bank_holder_name": name,
        "demat_bo_id": "1234567812345678", "demat_depository": depo,
    }).raise_for_status()

    c.post(f"/onboarding/applications/{app_id}/risk-profile", json={
        "answers": [{"question_id": f"q{i}", "weight": w} for i, w in enumerate(weights)],
    }).raise_for_status()

    c.post(f"/onboarding/applications/{app_id}/esign/confirm",
           json={"transaction_id": "TXN-SEED"}).raise_for_status()

    if approve:
        c.post(f"/onboarding/applications/{app_id}/decision",
               json={"approve": True}).raise_for_status()
        print(f"  ✓ {name} ({pan}) → approved")
    else:
        print(f"  ✓ {name} ({pan}) → under_review (pending compliance decision)")
    return app_id


# ── Phase 2: Reference master data ───────────────────────────────────────────

def seed_reference(c: httpx.Client) -> dict:
    """Call the built-in reference seed endpoint, return entity maps."""
    r = c.post("/reference/seed")
    if r.status_code < 400:
        d = r.json()
        print(f"  ✓ reference: {d.get('securities',0)} securities, "
              f"{d.get('strategies',0)} strategies, "
              f"{d.get('brokers',0)} brokers")
    else:
        print(f"  reference seed warn: {r.text[:120]}")

    # Fetch back IDs we'll need
    securities = {s["symbol"]: s["id"] for s in c.get("/reference/securities").json()}
    strategies = {s["code"]: s["id"] for s in c.get("/reference/strategies").json()}
    brokers    = [b["id"] for b in c.get("/reference/brokers").json()]
    return {"securities": securities, "strategies": strategies, "brokers": brokers}


# ── Phase 3: Portfolio accounts + holdings ────────────────────────────────────

# Which stocks go in each strategy (subset of SEED_SECURITIES in the router)
STRATEGY_HOLDINGS = {
    "LCV": [("RELIANCE", 50), ("HDFCBANK", 80), ("ICICIBANK", 100),
            ("AXISBANK", 120), ("NESTLEIND", 30)],
    "MCG": [("TCS", 40), ("INFY", 60), ("WIPRO", 150),
            ("HCLTECH", 70), ("BAJFINANCE", 20)],
    "FCC": [("ASIANPAINT", 35), ("MARUTI", 10), ("SUNPHARMA", 45),
            ("TITAN", 25), ("ULTRACEMCO", 15)],
}

# Map applicant index → strategy code
APPLICANT_STRATEGY = ["LCV", "MCG", "FCC", "LCV"]


def seed_portfolio(c: httpx.Client, clients: list[dict], ref: dict) -> list[str]:
    """Create one portfolio account per client with holdings and a cash entry."""
    account_ids = []
    today = date.today()

    for i, client in enumerate(clients):
        strategy_code = APPLICANT_STRATEGY[i % len(APPLICANT_STRATEGY)]
        strategy_id   = ref["strategies"].get(strategy_code)
        if not strategy_id:
            print(f"  warn: strategy {strategy_code} not found, skipping {client['full_name']}")
            continue

        account_code  = f"PMS{1001 + i:04d}"
        inception     = (today - timedelta(days=180 + i * 15)).isoformat()

        r = c.post("/portfolio/accounts", json={
            "client_id":      client["id"],
            "strategy_id":    strategy_id,
            "account_code":   account_code,
            "inception_date": inception,
        })
        if r.status_code >= 400:
            print(f"  skip account {account_code}: {r.text[:100]}")
            continue
        acct_id = r.json()["id"]
        account_ids.append(acct_id)
        print(f"  ✓ account {account_code} ({strategy_code}) for {client['full_name']}")

        # Add holdings
        holdings = STRATEGY_HOLDINGS.get(strategy_code, [])
        cash_spent = 0
        for symbol, qty in holdings:
            sec_id = ref["securities"].get(symbol)
            if not sec_id:
                continue
            price_paise = STOCK_PRICES.get(symbol, 1000) * 100
            # Small variation per client so data looks different
            variation = 1 + (i * 0.03)
            cost_paise = int(price_paise * 0.92 * variation)  # bought ~8% below current
            c.post(f"/portfolio/accounts/{acct_id}/holdings", json={
                "security_id":    sec_id,
                "quantity":       qty,
                "avg_cost_paise": cost_paise,
            })
            cash_spent += qty * cost_paise

        # Initial capital inflow cash entry
        initial_capital = int(cash_spent * 1.15)  # 15% buffer cash
        c.post(f"/portfolio/accounts/{acct_id}/cash", json={
            "entry_type":    "capital_inflow",
            "amount_paise":  initial_capital,
            "balance_paise": initial_capital - int(cash_spent),
            "posted_on":     inception,
        })

    print(f"  ✓ {len(account_ids)} portfolio accounts with holdings created")
    return account_ids


# ── Phase 4: Trading orders + trades ─────────────────────────────────────────

def seed_trading(c: httpx.Client, account_ids: list[str], ref: dict) -> None:
    """Create a realistic mix of orders (pending, approved, filled) and trades."""
    if not account_ids or not ref["brokers"]:
        print("  skip trading: no accounts or brokers")
        return

    today = date.today()
    all_securities = list(ref["securities"].items())  # [(symbol, id), ...]
    strategies     = list(ref["strategies"].values())
    broker_id      = ref["brokers"][0]

    # Recent filled trades (last 60 days)
    recent_trades = [
        ("RELIANCE",  "BUY",  25,  2820),
        ("TCS",       "BUY",  15,  3710),
        ("HDFCBANK",  "BUY",  50,  1650),
        ("INFY",      "SELL", 20,  1580),
        ("ICICIBANK", "BUY",  40,  1190),
        ("WIPRO",     "BUY",  80,   495),
        ("SUNPHARMA", "SELL", 10,  1700),
        ("BAJFINANCE","BUY",  10,  6950),
        ("MARUTI",    "SELL",  5, 12800),
        ("TITAN",     "BUY",  15,  3550),
    ]

    order_count = 0
    trade_count = 0

    for idx, (symbol, side, qty, price) in enumerate(recent_trades):
        sec_id      = ref["securities"].get(symbol)
        strategy_id = strategies[idx % len(strategies)] if strategies else None
        if not sec_id or not strategy_id:
            continue

        days_ago = 5 + idx * 6
        acct_id  = account_ids[idx % len(account_ids)]

        # Create order → approve → record trade
        r = c.post("/trading/orders", json={
            "security_id": sec_id,
            "strategy_id": strategy_id,
            "side":        side,
            "quantity":    qty,
            "order_type":  "market",
        })
        if r.status_code >= 400:
            continue
        order_id = r.json()["id"]
        order_count += 1

        # Approve the order
        c.post(f"/trading/orders/{order_id}/decide", json={"approve": True})

        # Allocate to account
        c.post(f"/trading/orders/{order_id}/allocations", json={
            "portfolio_account_id": acct_id,
            "allocated_qty": qty,
        })

        # Record the trade (filled)
        r2 = c.post("/trading/trades", json={
            "order_id":             order_id,
            "portfolio_account_id": acct_id,
            "security_id":          sec_id,
            "broker_id":            broker_id,
            "side":                 side,
            "quantity":             qty,
            "price_paise":          price * 100,
            "contract_note":        f"CN-{2024100 + idx}",
        })
        if r2.status_code < 400:
            trade_count += 1

    # Create a few PENDING orders (awaiting approval)
    pending_stocks = [("ASIANPAINT", "BUY", 20), ("NESTLEIND", "BUY", 12), ("AXISBANK", "SELL", 60)]
    for symbol, side, qty in pending_stocks:
        sec_id      = ref["securities"].get(symbol)
        strategy_id = strategies[0] if strategies else None
        if not sec_id or not strategy_id:
            continue
        c.post("/trading/orders", json={
            "security_id": sec_id,
            "strategy_id": strategy_id,
            "side":        side,
            "quantity":    qty,
            "order_type":  "market",
        })
        order_count += 1

    print(f"  ✓ {order_count} orders, {trade_count} filled trades seeded")


# ── Phase 5: Performance history ─────────────────────────────────────────────

def seed_performance(c: httpx.Client, account_ids: list[str]) -> None:
    """Create 90-day valuation snapshots and period returns for each account."""
    if not account_ids:
        print("  skip performance: no accounts")
        return

    today    = date.today()
    snap_count  = 0
    ret_count   = 0

    # Base market values per account (in ₹ crore, converted to paise)
    base_values_cr = [0.85, 1.95, 4.20, 1.10]

    for i, acct_id in enumerate(account_ids):
        base_mv   = int(base_values_cr[i % len(base_values_cr)] * 1e7 * 100)  # paise
        cost_base = int(base_mv * 0.87)  # cost ~87% of market value (unrealised gain)
        cash_base = int(base_mv * 0.08)  # 8% cash

        # 90 daily snapshots with mild upward trend + noise
        for day_offset in range(90, 0, -1):
            snap_date = today - timedelta(days=day_offset)
            trend     = 1 + (90 - day_offset) * 0.0004   # ~3.6% total drift
            noise     = 1 + random.uniform(-0.008, 0.012)  # ±1% daily noise
            mv        = int(base_mv * trend * noise)
            cost      = int(cost_base * (1 + (90 - day_offset) * 0.0001))
            cash      = int(cash_base * (1 + random.uniform(-0.05, 0.05)))

            r = c.post("/performance/snapshots", json={
                "portfolio_account_id": acct_id,
                "as_of":               snap_date.isoformat(),
                "market_value_paise":  mv,
                "cost_value_paise":    cost,
                "cash_paise":          cash,
            })
            if r.status_code < 400:
                snap_count += 1

        # Period returns (TWRR)
        returns = [
            ("1M",  today.isoformat(), round(random.uniform(1.2, 3.8), 2),  round(random.uniform(0.9, 2.5), 2)),
            ("3M",  today.isoformat(), round(random.uniform(3.5, 8.1), 2),  round(random.uniform(2.8, 6.0), 2)),
            ("6M",  today.isoformat(), round(random.uniform(6.0, 14.2), 2), round(random.uniform(5.0, 11.0), 2)),
            ("1Y",  today.isoformat(), round(random.uniform(11.0, 22.5), 2), round(random.uniform(9.0, 18.0), 2)),
            ("SI",  today.isoformat(), round(random.uniform(8.0, 18.0), 2), round(random.uniform(6.5, 14.0), 2)),
        ]
        for period, as_of, twrr, bm in returns:
            r = c.post("/performance/returns", json={
                "portfolio_account_id": acct_id,
                "period":              period,
                "as_of":               as_of,
                "twrr_pct":            twrr,
                "benchmark_pct":       bm,
            })
            if r.status_code < 400:
                ret_count += 1

    print(f"  ✓ {snap_count} valuation snapshots, {ret_count} period returns seeded")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    random.seed(42)  # reproducible noise

    with httpx.Client(base_url=BASE, timeout=30) as c:
        # ── Auth ──────────────────────────────────────────────────────────────
        try:
            token = _dev_token(c, "compliance")
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: could not get dev token ({exc}). Is the backend running?")
            return 1
        c.headers["Authorization"] = f"Bearer {token}"

        # ── Phase 1: Onboarding ───────────────────────────────────────────────
        print("\n[1/5] Seeding onboarding applications...")
        [seed_one(c, a, approve=True) for a in APPLICANTS]
        [seed_one(c, a, approve=False) for a in PENDING_APPLICANTS]

        print("      Provisioning approved clients...")
        r = c.post("/clients/process-outbox")
        if r.status_code < 400:
            print(f"      ✓ provisioned {r.json().get('processed', 0)} client(s)")
        else:
            print(f"      provision warn: {r.text[:80]}")

        # ── Phase 2: Reference master data ────────────────────────────────────
        print("\n[2/5] Seeding reference master data...")
        ref = seed_reference(c)

        # ── Phase 3: Fetch clients → create portfolio accounts ────────────────
        print("\n[3/5] Seeding portfolio accounts + holdings...")
        clients_resp = c.get("/clients")
        clients = clients_resp.json() if clients_resp.status_code < 400 else []
        if not clients:
            print("      warn: no clients found — run onboarding first")
        account_ids = seed_portfolio(c, clients, ref)

        # ── Phase 4: Trading orders + trades ──────────────────────────────────
        print("\n[4/5] Seeding trading orders + trades...")
        seed_trading(c, account_ids, ref)

        # ── Phase 5: Performance history ──────────────────────────────────────
        print("\n[5/5] Seeding performance history (90 days)...")
        seed_performance(c, account_ids)

        # ── Investor login ────────────────────────────────────────────────────
        try:
            reg = c.post("/auth/register", json={
                "email": "asha@example.com", "password": "investor123",
                "full_name": "Asha Rao", "role": "investor",
            })
            if reg.status_code < 400:
                print("\n  ✓ investor login ready: asha@example.com / investor123")
            elif "already" in reg.text.lower():
                print("\n  investor asha@example.com already registered")
        except Exception as exc:  # noqa: BLE001
            print(f"\n  investor registration skipped: {exc}")

    print("\n✅ Seed complete. Start the frontend and log in:")
    print("   RM / compliance:  use dev-token or register via /auth/register")
    print("   Investor portal:  asha@example.com / investor123")
    return 0


if __name__ == "__main__":
    sys.exit(main())
