"""Presentation seed script — creates all demo users and rich data for every page.

Creates:
  - admin@aurumpms.com        / Admin@123        (role: admin — maps to compliance)
  - compliance@aurumpms.com   / Comply@123       (role: compliance)
  - rm@aurumpms.com           / Manager@123      (role: relationship_manager)
  - ojas@aurumpms.com         / Investor@123     (role: investor, client: Ojas Parekh)

Also seeds:
  - 6 fully-approved clients (incl. Ojas Parekh) with portfolios, holdings, trades, performance
  - 2 clients in under_review (compliance queue not empty)
  - Reference data: securities, strategies, brokers
  - 90-day performance history + period returns
  - Realistic trading orders (filled + pending)
  - Messages between all user pairs
  - Activity log entries

Run from the backend/ folder with the venv activated:
    python scripts/seed_presentation.py
"""
from __future__ import annotations

import os
import random
import sys
import time
from datetime import date, timedelta

import httpx

BASE = os.getenv("BASE_URL", "http://localhost:8000/api/v1")

# ── Users to create ──────────────────────────────────────────────────────────
STAFF_USERS = [
    # (email, password, full_name, role)
    ("admin@aurumpms.com",      "Admin@123",    "Arjun Sharma",    "compliance"),
    ("compliance@aurumpms.com", "Comply@123",   "Priya Compliance","compliance"),
    ("rm@aurumpms.com",         "Manager@123",  "Rahul Mehta",     "relationship_manager"),
]

# ── Onboarding applicants (fully approved → active clients) ──────────────────
# (name, email, pan, mobile, investment ₹, demat, risk weights)
# NOTE: PANs are intentionally distinct from seed_demo.py to avoid DB conflicts
APPLICANTS = [
    ("Ojas Parekh",   "ojas@aurumpms.com",   "OJSPR1234A", "9870000001", 25_000_000, "NSDL", [5, 4, 5, 5, 4]),
    ("Asha Rao",      "asha2@example.com",   "ASHAR2234F", "9870000002",  5_000_000, "NSDL", [2, 2, 1, 2, 2]),
    ("Vikram Mehta",  "vikram2@example.com", "VIKMT5678K", "9870000003", 12_000_000, "CDSL", [3, 3, 4, 3, 3]),
    ("Neha Kapoor",   "neha2@example.com",   "NEHKP4321J", "9870000004", 30_000_000, "NSDL", [5, 4, 5, 4, 5]),
    ("Rohan Iyer",    "rohan2@example.com",  "ROHIY8765D", "9870000005",  8_000_000, "CDSL", [3, 2, 3, 4, 3]),
    ("Sunita Joshi",  "sunita2@example.com", "SNJSH5678E", "9870000006",  9_500_000, "NSDL", [4, 3, 3, 4, 4]),
]

# ── Clients left in compliance queue ────────────────────────────────────────
PENDING_APPLICANTS = [
    ("Priya Sharma",  "priya2@example.com",  "PRISH9876G", "9870000007", 15_000_000, "NSDL", [4, 3, 4, 4, 3]),
    ("Arjun Nair",    "arjun2@example.com",  "ARJNR5432H", "9870000008",  7_500_000, "CDSL", [2, 3, 2, 3, 2]),
]

# ── Stock prices (₹) ─────────────────────────────────────────────────────────
STOCK_PRICES = {
    "RELIANCE":   2950,
    "TCS":        3890,
    "HDFCBANK":   1720,
    "INFY":       1600,
    "ICICIBANK":  1280,
    "BAJFINANCE": 7100,
    "ASIANPAINT": 2850,
    "MARUTI":    13200,
    "SUNPHARMA":  1740,
    "TITAN":      3700,
    "WIPRO":       520,
    "NESTLEIND":  2450,
    "ULTRACEMCO":12000,
    "HCLTECH":    1750,
    "AXISBANK":   1200,
}

STRATEGY_HOLDINGS = {
    "LCV": [("RELIANCE", 50), ("HDFCBANK", 80), ("ICICIBANK", 100),
            ("AXISBANK", 120), ("NESTLEIND", 30)],
    "MCG": [("TCS", 40), ("INFY", 60), ("WIPRO", 150),
            ("HCLTECH", 70), ("BAJFINANCE", 20)],
    "FCC": [("ASIANPAINT", 35), ("MARUTI", 10), ("SUNPHARMA", 45),
            ("TITAN", 25), ("ULTRACEMCO", 15)],
}

APPLICANT_STRATEGY = ["FCC", "LCV", "MCG", "FCC", "LCV", "MCG"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_json(r: httpx.Response):
    try:
        return r.json()
    except Exception:
        return []


def _dev_token(c: httpx.Client, role: str) -> str:
    r = c.post("/auth/token", json={"username": f"seed.{role}", "role": role})
    r.raise_for_status()
    return r.json()["access_token"]


def _set_token(c: httpx.Client, token: str):
    c.headers["Authorization"] = f"Bearer {token}"


def _get_retry(c: httpx.Client, path: str, retries: int = 5) -> httpx.Response:
    """GET with retry + backoff on connection drop."""
    for attempt in range(retries):
        try:
            return c.get(path)
        except (httpx.ReadError, httpx.ConnectError) as e:
            if attempt < retries - 1:
                wait = 4 + attempt * 2
                print(f"    GET {path} connection error, retrying in {wait}s... ({e})")
                time.sleep(wait)
            else:
                raise


# ── Phase 0: Register staff users ────────────────────────────────────────────

def _register(c: httpx.Client, email, password, full_name, role):
    """Register a user, retrying once on 429 rate-limit."""
    payload = {"email": email, "password": password, "full_name": full_name, "role": role}
    for attempt in range(3):
        r = c.post("/auth/register", json=payload)
        if r.status_code == 429:
            wait = 15
            print(f"    rate-limited, waiting {wait}s...")
            time.sleep(wait)
            continue
        return r
    return r


def seed_users(c: httpx.Client):
    print("\n[0/6] Creating staff & admin user accounts...")
    for email, password, full_name, role in STAFF_USERS:
        r = _register(c, email, password, full_name, role)
        if r.status_code == 409:
            print(f"  -> {email} already exists, skipping")
        elif r.status_code >= 400:
            print(f"  x {email}: {r.text[:80]}")
        else:
            print(f"  ok {full_name} <{email}> ({role})")
        time.sleep(13)  # stay under 5/min rate limit (60s / 5 = 12s apart)


# ── Phase 1: Onboarding ───────────────────────────────────────────────────────

def _post_retry(c: httpx.Client, path: str, data: dict, retries: int = 5):
    """POST with retry on connection drop (WinError 10054)."""
    for attempt in range(retries):
        try:
            return c.post(path, json=data)
        except (httpx.ReadError, httpx.ConnectError) as e:
            if attempt < retries - 1:
                wait = 4 + attempt * 2
                print(f"    connection error, retrying in {wait}s... ({e})")
                time.sleep(wait)
            else:
                raise


def seed_one(c: httpx.Client, applicant, approve: bool = True) -> str | None:
    name, email, pan, mobile, inv, depo, weights = applicant
    r = _post_retry(c, "/onboarding/applications", {
        "investor_type": "individual", "full_name": name,
        "email": email, "mobile": mobile, "pan": pan,
        "proposed_investment_inr": inv,
    })
    if r.status_code >= 400:
        body = _safe_json(r)
        msg = body.get("message", r.text) if isinstance(body, dict) else r.text
        print(f"  skip {name}: {msg}")
        return None
    app_id = r.json()["id"]

    _post_retry(c, f"/onboarding/applications/{app_id}/kyc", {
        "aadhaar_full": "234567890123",
        "bank_account_number": "12345678901",
        "bank_ifsc": "HDFC0001234",
        "bank_holder_name": name,
        "demat_bo_id": "1234567812345678",
        "demat_depository": depo,
    }).raise_for_status()

    _post_retry(c, f"/onboarding/applications/{app_id}/risk-profile", {
        "answers": [{"question_id": f"q{i}", "weight": w} for i, w in enumerate(weights)],
    }).raise_for_status()

    _post_retry(c, f"/onboarding/applications/{app_id}/esign/confirm",
                {"transaction_id": "TXN-SEED"}).raise_for_status()

    if approve:
        _post_retry(c, f"/onboarding/applications/{app_id}/decision",
                    {"approve": True}).raise_for_status()
        print(f"  ok {name} ({pan}) -> approved")
    else:
        print(f"  ok {name} ({pan}) -> under_review")
    return app_id


def seed_onboarding(c: httpx.Client) -> list[dict]:
    print("\n[1/6] Seeding onboarding applications...")
    for a in APPLICANTS:
        seed_one(c, a, approve=True)
    for a in PENDING_APPLICANTS:
        seed_one(c, a, approve=False)

    print("      Provisioning approved clients...")
    r = c.post("/clients/process-outbox")
    if r.status_code < 400:
        print(f"      ok provisioned {r.json().get('processed', 0)} client(s)")
    else:
        print(f"      provision warn: {r.text[:80]}")

    # Fetch provisioned clients so we can create portfolios for them
    token = _dev_token(c, "compliance")
    _set_token(c, token)
    clients_resp = _get_retry(c, "/clients")
    clients = _safe_json(clients_resp)
    if isinstance(clients, dict):
        clients = clients.get("items", [])
    print(f"      fetched {len(clients)} client(s) from API")
    return clients


# ── Phase 2: Register Ojas as investor (links to his client record) ───────────

def seed_investor_user(c: httpx.Client):
    print("\n[1b] Registering Ojas Parekh investor login...")
    time.sleep(13)  # wait for rate limit window
    r = _register(c, "ojas@aurumpms.com", "Investor@123", "Ojas Parekh", "investor")
    if r.status_code == 409:
        print("  -> ojas@aurumpms.com already exists")
    elif r.status_code >= 400:
        print(f"  x Ojas registration: {r.text[:80]}")
    else:
        print("  ok ojas@aurumpms.com registered")


# ── Phase 3: Reference data ───────────────────────────────────────────────────

def seed_reference(c: httpx.Client) -> dict:
    print("\n[2/6] Seeding reference master data...")
    # Give the server a moment after the heavy provisioning batch
    time.sleep(3)
    r = _post_retry(c, "/reference/seed", {})
    if r.status_code < 400:
        d = _safe_json(r)
        if isinstance(d, dict):
            print(f"  ok {d.get('securities', 0)} securities, "
                  f"{d.get('strategies', 0)} strategies, "
                  f"{d.get('brokers', 0)} brokers")
    else:
        print(f"  reference seed warn: {r.text[:100]}")

    securities = {s["symbol"]: s["id"] for s in _safe_json(_get_retry(c, "/reference/securities"))}
    strategies = {s["code"]: s["id"] for s in _safe_json(_get_retry(c, "/reference/strategies"))}
    brokers    = [b["id"] for b in _safe_json(_get_retry(c, "/reference/brokers"))]
    print(f"  ok fetched: {len(securities)} securities, {len(strategies)} strategies, {len(brokers)} brokers")
    return {"securities": securities, "strategies": strategies, "brokers": brokers}


# ── Phase 4: Portfolio accounts + holdings ────────────────────────────────────

def seed_portfolio(c: httpx.Client, clients: list[dict], ref: dict) -> list[str]:
    print("\n[3/6] Seeding portfolio accounts + holdings...")
    account_ids = []
    today = date.today()

    for i, client in enumerate(clients):
        strategy_code = APPLICANT_STRATEGY[i % len(APPLICANT_STRATEGY)]
        strategy_id   = ref["strategies"].get(strategy_code)
        if not strategy_id:
            print(f"  warn: strategy {strategy_code} not found for {client['full_name']}")
            continue

        account_code = f"PMS{2001 + i:04d}"
        inception    = (today - timedelta(days=200 + i * 20)).isoformat()

        r = c.post("/portfolio/accounts", json={
            "client_id":      client["id"],
            "strategy_id":    strategy_id,
            "account_code":   account_code,
            "inception_date": inception,
        })
        if r.status_code >= 400:
            print(f"  skip account {account_code}: {r.text[:80]}")
            continue
        acct_id = r.json()["id"]
        account_ids.append(acct_id)
        print(f"  ok {account_code} ({strategy_code}) -> {client['full_name']}")

        holdings = STRATEGY_HOLDINGS.get(strategy_code, [])
        cash_spent = 0
        for symbol, qty in holdings:
            sec_id = ref["securities"].get(symbol)
            if not sec_id:
                continue
            price_paise = STOCK_PRICES.get(symbol, 1000) * 100
            variation   = 1 + (i * 0.04)
            cost_paise  = int(price_paise * 0.90 * variation)
            c.post(f"/portfolio/accounts/{acct_id}/holdings", json={
                "security_id":    sec_id,
                "quantity":       qty,
                "avg_cost_paise": cost_paise,
            })
            cash_spent += qty * cost_paise

        initial_capital = int(cash_spent * 1.18)
        c.post(f"/portfolio/accounts/{acct_id}/cash", json={
            "entry_type":    "capital_inflow",
            "amount_paise":  initial_capital,
            "balance_paise": initial_capital - int(cash_spent),
            "posted_on":     inception,
        })

    print(f"  ok {len(account_ids)} portfolio accounts created")
    return account_ids


# ── Phase 5: Trading ──────────────────────────────────────────────────────────

def seed_trading(c: httpx.Client, account_ids: list[str], ref: dict):
    print("\n[4/6] Seeding trading orders + trades...")
    if not account_ids or not ref["brokers"]:
        print("  skip: no accounts or brokers")
        return

    broker_id  = ref["brokers"][0]
    strategies = list(ref["strategies"].values())

    recent_trades = [
        ("RELIANCE",   "BUY",  25,  2820),
        ("TCS",        "BUY",  15,  3710),
        ("HDFCBANK",   "BUY",  50,  1650),
        ("INFY",       "SELL", 20,  1580),
        ("ICICIBANK",  "BUY",  40,  1190),
        ("WIPRO",      "BUY",  80,   495),
        ("SUNPHARMA",  "SELL", 10,  1700),
        ("BAJFINANCE", "BUY",  10,  6950),
        ("MARUTI",     "SELL",  5, 12800),
        ("TITAN",      "BUY",  15,  3550),
        ("HCLTECH",    "BUY",  30,  1680),
        ("AXISBANK",   "BUY",  60,  1150),
    ]

    order_count = trade_count = 0
    for idx, (symbol, side, qty, price) in enumerate(recent_trades):
        sec_id      = ref["securities"].get(symbol)
        strategy_id = strategies[idx % len(strategies)] if strategies else None
        if not sec_id or not strategy_id:
            continue
        acct_id = account_ids[idx % len(account_ids)]

        r = c.post("/trading/orders", json={
            "security_id": sec_id, "strategy_id": strategy_id,
            "side": side, "quantity": qty, "order_type": "market",
        })
        if r.status_code >= 400:
            continue
        order_id = r.json()["id"]
        order_count += 1

        c.post(f"/trading/orders/{order_id}/decide", json={"approve": True})
        c.post(f"/trading/orders/{order_id}/allocations", json={
            "portfolio_account_id": acct_id, "allocated_qty": qty,
        })

        r2 = c.post("/trading/trades", json={
            "order_id":             order_id,
            "portfolio_account_id": acct_id,
            "security_id":          sec_id,
            "broker_id":            broker_id,
            "side":                 side,
            "quantity":             qty,
            "price_paise":          price * 100,
            "contract_note":        f"CN-{2025100 + idx}",
        })
        if r2.status_code < 400:
            trade_count += 1

    # Pending orders (awaiting compliance approval)
    pending = [
        ("ASIANPAINT", "BUY",  20),
        ("NESTLEIND",  "BUY",  12),
        ("AXISBANK",   "SELL", 60),
        ("ULTRACEMCO", "BUY",   8),
    ]
    for symbol, side, qty in pending:
        sec_id      = ref["securities"].get(symbol)
        strategy_id = strategies[0] if strategies else None
        if not sec_id or not strategy_id:
            continue
        c.post("/trading/orders", json={
            "security_id": sec_id, "strategy_id": strategy_id,
            "side": side, "quantity": qty, "order_type": "market",
        })
        order_count += 1

    print(f"  ok {order_count} orders, {trade_count} filled trades")


# ── Phase 6: Performance history ─────────────────────────────────────────────

def seed_performance(c: httpx.Client, account_ids: list[str]):
    print("\n[5/6] Seeding 90-day performance history...")
    if not account_ids:
        print("  skip: no accounts")
        return

    today           = date.today()
    snap_count      = ret_count = 0
    base_values_cr  = [4.20, 0.85, 1.95, 5.80, 1.45, 1.72]

    for i, acct_id in enumerate(account_ids):
        base_mv   = int(base_values_cr[i % len(base_values_cr)] * 1e7 * 100)
        cost_base = int(base_mv * 0.86)
        cash_base = int(base_mv * 0.09)

        for day_offset in range(90, 0, -1):
            snap_date = today - timedelta(days=day_offset)
            trend     = 1 + (90 - day_offset) * 0.00045
            noise     = 1 + random.uniform(-0.009, 0.013)
            mv        = int(base_mv * trend * noise)
            cost      = int(cost_base * (1 + (90 - day_offset) * 0.00012))
            cash      = int(cash_base * (1 + random.uniform(-0.06, 0.06)))

            r = c.post("/performance/snapshots", json={
                "portfolio_account_id": acct_id,
                "as_of":               snap_date.isoformat(),
                "market_value_paise":  mv,
                "cost_value_paise":    cost,
                "cash_paise":          cash,
            })
            if r.status_code < 400:
                snap_count += 1

        returns = [
            ("1M",  today.isoformat(), round(random.uniform(1.5,  4.2), 2), round(random.uniform(1.1, 3.0), 2)),
            ("3M",  today.isoformat(), round(random.uniform(4.0,  9.5), 2), round(random.uniform(3.2, 7.0), 2)),
            ("6M",  today.isoformat(), round(random.uniform(7.0, 16.0), 2), round(random.uniform(5.5,12.0), 2)),
            ("1Y",  today.isoformat(), round(random.uniform(12.0,25.0), 2), round(random.uniform(9.5,19.0), 2)),
            ("SI",  today.isoformat(), round(random.uniform(9.0, 20.0), 2), round(random.uniform(7.0,15.0), 2)),
        ]
        for period, as_of, twrr, bm in returns:
            r = c.post("/performance/returns", json={
                "portfolio_account_id": acct_id,
                "period": period, "as_of": as_of,
                "twrr_pct": twrr, "benchmark_pct": bm,
            })
            if r.status_code < 400:
                ret_count += 1

    print(f"  ok {snap_count} snapshots, {ret_count} period returns")


# ── Phase 7: Messages between users ──────────────────────────────────────────

def seed_messages(c: httpx.Client):
    """Create realistic message threads between all role pairs."""
    print("\n[6/6] Seeding messages + activity log...")

    conversations = [
        (
            "rm@aurumpms.com", "Manager@123", "relationship_manager",
            "ojas@aurumpms.com",
            [
                "Hi Ojas, welcome aboard! I'm Rahul, your dedicated Relationship Manager at Aurum PMS.",
                "Your portfolio has been set up with the Focused Capital Compounding (FCC) strategy as discussed.",
                "Please let me know if you'd like to review your quarterly performance report.",
            ]
        ),
        (
            "ojas@aurumpms.com", "Investor@123", "investor",
            "rm@aurumpms.com",
            [
                "Thanks Rahul! Excited to get started. When can we schedule a portfolio review?",
                "Also, could you explain how the FCC strategy selects its holdings?",
            ]
        ),
        (
            "compliance@aurumpms.com", "Comply@123", "compliance",
            "rm@aurumpms.com",
            [
                "Rahul, please ensure all KYC documents for the new applications are complete before EOD.",
                "Two applications are pending review - Priya Sharma and Arjun Nair. Please follow up.",
                "The SEBI quarterly report submission deadline is approaching. Confirm readiness.",
            ]
        ),
        (
            "rm@aurumpms.com", "Manager@123", "relationship_manager",
            "compliance@aurumpms.com",
            [
                "Noted. KYC docs for both applicants have been collected and uploaded.",
                "SEBI report is 90% ready - will share draft by tomorrow morning.",
            ]
        ),
        (
            "admin@aurumpms.com", "Admin@123", "compliance",
            "rm@aurumpms.com",
            [
                "Good morning Rahul. Quarterly performance reviews are due next week - please prepare summaries for all active clients.",
                "Also note: the new SEBI disclosure norms for PMS take effect from next month.",
            ]
        ),
        (
            "rm@aurumpms.com", "Manager@123", "relationship_manager",
            "admin@aurumpms.com",
            [
                "Understood. I'll prepare the client summaries by Thursday.",
                "Shall I send the updated fee disclosure to all investors as well?",
            ]
        ),
    ]

    for sender_email, sender_pw, sender_role, recipient_email, messages in conversations:
        for _attempt in range(3):
            login_r = c.post("/auth/login", json={"email": sender_email, "password": sender_pw})
            if login_r.status_code == 429:
                time.sleep(15)
                continue
            break
        if login_r.status_code >= 400:
            print(f"  x login failed for {sender_email}: {login_r.text[:60]}")
            continue
        sender_token = login_r.json()["access_token"]
        old_auth = c.headers.get("Authorization")
        c.headers["Authorization"] = f"Bearer {sender_token}"

        contacts_r = c.get("/messages/contacts")
        if contacts_r.status_code >= 400:
            c.headers["Authorization"] = old_auth
            continue
        contacts = contacts_r.json()
        recipient = next((x for x in contacts if x["email"] == recipient_email), None)
        if not recipient:
            c.headers["Authorization"] = old_auth
            continue

        recipient_id = recipient["id"]

        r = c.post("/messages/conversations", json={
            "recipient_id": recipient_id,
            "body": messages[0],
        })
        if r.status_code >= 400:
            c.headers["Authorization"] = old_auth
            continue

        conv_id = r.json()["id"]

        for msg in messages[1:]:
            c.post(f"/messages/conversations/{conv_id}/messages", json={"body": msg})

        print(f"  ok {sender_email} -> {recipient_email}: {len(messages)} message(s)")
        c.headers["Authorization"] = old_auth

    # Seed activity log entries via compliance token
    time.sleep(2)
    comp_login = c.post("/auth/login", json={
        "email": "compliance@aurumpms.com", "password": "Comply@123"
    })
    if comp_login.status_code < 400:
        c.headers["Authorization"] = f"Bearer {comp_login.json()['access_token']}"
        activities = [
            # Onboarding events
            ("onboarding_approved",  "application", "Ojas Parekh application approved and client provisioned"),
            ("onboarding_approved",  "application", "Asha Rao application approved - KYC verified via DigiLocker"),
            ("onboarding_approved",  "application", "Vikram Mehta application approved - risk profile: aggressive"),
            ("onboarding_approved",  "application", "Neha Kapoor application approved - 30L corpus onboarded"),
            ("onboarding_approved",  "application", "Rohan Iyer application approved and CDSL demat linked"),
            ("onboarding_approved",  "application", "Sunita Joshi application approved - assigned LCV strategy"),
            ("onboarding_review",    "application", "Priya Sharma application under compliance review"),
            ("onboarding_review",    "application", "Arjun Nair application flagged for additional KYC verification"),
            # KYC events
            ("kyc_verified",         "client",      "KYC documents verified for Asha Rao"),
            ("kyc_verified",         "client",      "Bank account verified for Vikram Mehta - ICICI Bank"),
            ("kyc_verified",         "client",      "PAN-Aadhaar linked successfully for Neha Kapoor"),
            # Portfolio events
            ("portfolio_created",    "portfolio",   "FCC portfolio account PMS2001 created for Ojas Parekh"),
            ("portfolio_created",    "portfolio",   "LCV portfolio account PMS2002 created for Asha Rao"),
            ("portfolio_created",    "portfolio",   "MCG portfolio account PMS2003 created for Vikram Mehta"),
            ("capital_inflow",       "portfolio",   "25,00,000 capital inflow received for PMS2001"),
            ("capital_inflow",       "portfolio",   "5,00,000 capital inflow received for PMS2002"),
            # Trading events
            ("trade_executed",       "trade",       "BUY 25 RELIANCE @ 2820 - Contract CN-2025100"),
            ("trade_executed",       "trade",       "BUY 15 TCS @ 3710 - Contract CN-2025101"),
            ("trade_executed",       "trade",       "SELL 20 INFY @ 1580 - Contract CN-2025103"),
            ("trade_executed",       "trade",       "BUY 50 HDFCBANK @ 1650 - Contract CN-2025102"),
            ("trade_executed",       "trade",       "BUY 80 WIPRO @ 495 - Contract CN-2025105"),
            ("trade_executed",       "trade",       "SELL 5 MARUTI @ 12800 - Contract CN-2025108"),
            ("order_approved",       "order",       "Order for 40 ICICIBANK BUY approved by compliance"),
            ("order_approved",       "order",       "Order for 10 BAJFINANCE BUY approved by compliance"),
            ("order_pending",        "order",       "Order for 20 ASIANPAINT BUY awaiting compliance approval"),
            ("order_pending",        "order",       "Order for 12 NESTLEIND BUY awaiting compliance approval"),
            ("order_pending",        "order",       "Order for 60 AXISBANK SELL awaiting compliance approval"),
            # Performance events
            ("performance_snapshot", "performance", "Daily valuation snapshots generated for all 6 accounts"),
            ("performance_snapshot", "performance", "Monthly performance snapshots generated for all accounts"),
            ("benchmark_updated",    "performance", "Nifty 50 benchmark returns updated for Q2 FY2026"),
            # Report events
            ("report_generated",     "report",      "Q2 FY2026 portfolio performance report generated"),
            ("report_generated",     "report",      "Monthly transaction report generated for all active accounts"),
            ("report_generated",     "report",      "Fee invoice generated for PMS2001 - 52300 incl GST"),
            # System events
            ("fee_schedule_created", "settings",    "New fee schedule Standard PMS created - 2.0 pct mgmt + 20 pct perf"),
            ("user_registered",      "user",        "New investor login created for ojas@aurumpms.com"),
            ("security_added",       "reference",   "15 NSE securities added to reference master"),
            ("strategy_added",       "reference",   "Strategy Large Cap Value (LCV) added to platform"),
            ("bhavcopy_processed",   "nse",         "NSE BhavCopy for 2026-06-23 downloaded and processed"),
        ]
        for action, entity_type, detail in activities:
            c.post("/notifications/log", json={
                "action": action,
                "entity_type": entity_type,
                "detail": detail,
            })
        print(f"  ok {len(activities)} activity log entries seeded")


# ── Phase 8: NSE Bhavcopy records ────────────────────────────────────────────

def seed_nse_reports(c: httpx.Client):
    """Seed NSE Bhavcopy report records into the nse DB so Daily Reports page has data."""
    print("\n[7b] Seeding NSE Bhavcopy report records...")
    try:
        import psycopg2
        nse_url = os.getenv(
            "NSE_DATABASE_URL",
            "postgresql://postgres:aarya123@localhost:5432/aurum_market_data",
        )
        nse_url = nse_url.replace("postgresql+psycopg2://", "postgresql://")
        conn = psycopg2.connect(nse_url)
        cur = conn.cursor()

        today = date.today()
        from pathlib import Path as _Path
        store_dir = _Path(__file__).resolve().parents[1] / "bhavcopy_files"

        records = []
        for i in range(10):
            d = today - timedelta(days=i)
            if d.weekday() >= 5:
                continue
            ds = d.strftime("%Y-%m-%d")
            zip_name = f"BhavCopy_NSE_CM_0_0_0_{d.strftime('%Y%m%d')}_F_0000.csv.zip"
            zip_path = store_dir / zip_name
            records.append((ds, zip_name, str(zip_path) if zip_path.exists() else None))

        for report_date, zip_name, zip_path in records:
            cur.execute(
                """INSERT INTO nse_bhavcopy_reports
                   (report_date, zip_filename, zip_filepath, status, records_count, created_at)
                   VALUES (%s, %s, %s, %s, %s, NOW())
                   ON CONFLICT (report_date) DO NOTHING""",
                (report_date, zip_name, zip_path, "completed" if zip_path else "pending", 1800 if zip_path else 0),
            )
        conn.commit()
        cur.close()
        conn.close()
        print(f"  ok {len(records)} NSE bhavcopy records seeded")
    except Exception as e:
        print(f"  warn NSE reports seeding skipped: {e}")


# ── Phase 9: Fee schedules ────────────────────────────────────────────────────

def seed_fee_schedules(c: httpx.Client):
    """Seed fee schedule records so Fee Schedules page has data."""
    print("\n[9] Seeding fee schedules...")
    schedules = [
        {"name": "Standard PMS", "mgmt_fee_pct": 2.00, "perf_fee_pct": 20.0, "high_water_mark": True, "hurdle_rate_pct": 8.0},
        {"name": "Premium PMS", "mgmt_fee_pct": 1.50, "perf_fee_pct": 15.0, "high_water_mark": True, "hurdle_rate_pct": 10.0},
        {"name": "Institutional", "mgmt_fee_pct": 1.00, "perf_fee_pct": 10.0, "high_water_mark": False, "hurdle_rate_pct": None},
        {"name": "Fixed Fee Only", "mgmt_fee_pct": 2.50, "perf_fee_pct": 0.0, "high_water_mark": False, "hurdle_rate_pct": None},
    ]
    for s in schedules:
        body = {k: v for k, v in s.items() if v is not None}
        r = c.post("/portfolio/fee-schedules", json=body)
        if r.status_code < 400:
            print(f"  ok Fee schedule '{s['name']}' created")
        else:
            print(f"  warn Fee schedule '{s['name']}': {r.status_code}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    run_users = os.getenv("SKIP_USERS", "").lower() != "1"
    run_onboarding = os.getenv("SKIP_ONBOARDING", "").lower() != "1"
    run_ref = os.getenv("SKIP_REFERENCE", "").lower() != "1"
    run_portfolio = os.getenv("SKIP_PORTFOLIO", "").lower() != "1"
    run_trading = os.getenv("SKIP_TRADING", "").lower() != "1"
    run_perf = os.getenv("SKIP_PERFORMANCE", "").lower() != "1"
    run_msgs = os.getenv("SKIP_MESSAGES", "").lower() != "1"
    run_nse = os.getenv("SKIP_NSE", "").lower() != "1"
    run_fees = os.getenv("SKIP_FEES", "").lower() != "1"

    with httpx.Client(base_url=BASE, timeout=30) as c:
        if run_users:
            seed_users(c)

        if run_onboarding:
            clients = seed_onboarding(c)
        else:
            clients = []

        seed_investor_user(c)

        if run_ref:
            ref = seed_reference(c)
        else:
            ref = {}

        if run_portfolio and clients and ref:
            account_ids = seed_portfolio(c, clients, ref)
        else:
            account_ids = []

        if run_trading and account_ids and ref:
            seed_trading(c, account_ids, ref)

        if run_perf and account_ids:
            seed_performance(c, account_ids)

        if run_msgs:
            seed_messages(c)

        if run_nse:
            seed_nse_reports(c)

        if run_fees:
            seed_fee_schedules(c)

    print("\nAll seed data created successfully!")


if __name__ == "__main__":
    main()
