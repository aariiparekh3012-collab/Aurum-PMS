"""Seed demo data: 1 admin, 2 compliance, 3 RMs, 20 investors with full portfolio data.

Run:  python seed_demo.py
Requires: backend .env to be configured, aurum-main database to exist with tables.
"""
import os
import sys
import uuid
import random
import hashlib
import secrets as _secrets
from datetime import datetime, date, timedelta, timezone

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# -- Config --
DB_URL = "postgresql://postgres:aarya123@localhost:5432/aurum-main"
PASSWORD = "demo123"  # all demo accounts use this password


def hash_password(password):
    salt = _secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000)
    return f"pbkdf2${salt}${dk.hex()}"


def now():
    return datetime.now(timezone.utc)


def random_date(start_days_ago=365, end_days_ago=30):
    d = random.randint(end_days_ago, start_days_ago)
    return date.today() - timedelta(days=d)


def random_pan():
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return (
        random.choice(letters)
        + random.choice(letters)
        + random.choice(letters)
        + random.choice(letters)
        + random.choice(letters)
        + str(random.randint(1000, 9999))
        + random.choice(letters)
    )


# -- People data --
COMPLIANCE_OFFICERS = [
    {"name": "Neha Kulkarni", "email": "neha.kulkarni@aurumpms.com", "phone": "+919876500001"},
    {"name": "Vikram Deshmukh", "email": "vikram.deshmukh@aurumpms.com", "phone": "+919876500002"},
]

RMS = [
    {"name": "Priya Sharma", "email": "priya.sharma@aurumpms.com", "phone": "+919876500003"},
    {"name": "Rahul Mehta", "email": "rahul.mehta@aurumpms.com", "phone": "+919876500004"},
    {"name": "Ananya Iyer", "email": "ananya.iyer@aurumpms.com", "phone": "+919876500005"},
]

INVESTORS = [
    {"name": "Rajesh Gupta", "email": "rajesh.gupta@gmail.com", "phone": "+919876510001"},
    {"name": "Sunita Patel", "email": "sunita.patel@gmail.com", "phone": "+919876510002"},
    {"name": "Amit Joshi", "email": "amit.joshi@gmail.com", "phone": "+919876510003"},
    {"name": "Kavita Reddy", "email": "kavita.reddy@gmail.com", "phone": "+919876510004"},
    {"name": "Manoj Kumar", "email": "manoj.kumar@gmail.com", "phone": "+919876510005"},
    {"name": "Deepa Nair", "email": "deepa.nair@gmail.com", "phone": "+919876510006"},
    {"name": "Sanjay Verma", "email": "sanjay.verma@gmail.com", "phone": "+919876510007"},
    {"name": "Pooja Agarwal", "email": "pooja.agarwal@gmail.com", "phone": "+919876510008"},
    {"name": "Vivek Saxena", "email": "vivek.saxena@gmail.com", "phone": "+919876510009"},
    {"name": "Ritu Malhotra", "email": "ritu.malhotra@gmail.com", "phone": "+919876510010"},
    {"name": "Arun Bhat", "email": "arun.bhat@gmail.com", "phone": "+919876510011"},
    {"name": "Meera Kapoor", "email": "meera.kapoor@gmail.com", "phone": "+919876510012"},
    {"name": "Nitin Chopra", "email": "nitin.chopra@gmail.com", "phone": "+919876510013"},
    {"name": "Swati Tiwari", "email": "swati.tiwari@gmail.com", "phone": "+919876510014"},
    {"name": "Rohit Singh", "email": "rohit.singh@gmail.com", "phone": "+919876510015"},
    {"name": "Anjali Menon", "email": "anjali.menon@gmail.com", "phone": "+919876510016"},
    {"name": "Karan Bajaj", "email": "karan.bajaj@gmail.com", "phone": "+919876510017"},
    {"name": "Nisha Rao", "email": "nisha.rao@gmail.com", "phone": "+919876510018"},
    {"name": "Gaurav Pandey", "email": "gaurav.pandey@gmail.com", "phone": "+919876510019"},
    {"name": "Lakshmi Subramaniam", "email": "lakshmi.subra@gmail.com", "phone": "+919876510020"},
]

# -- Securities (Indian stocks) --
SECURITIES = [
    {"isin": "INE002A01018", "symbol": "RELIANCE", "name": "Reliance Industries Ltd", "sector": "Energy", "price": 295000},
    {"isin": "INE009A01021", "symbol": "INFY", "name": "Infosys Ltd", "sector": "IT", "price": 158000},
    {"isin": "INE467B01029", "symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT", "price": 365000},
    {"isin": "INE040A01034", "symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "sector": "Banking", "price": 168000},
    {"isin": "INE090A01021", "symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "sector": "Banking", "price": 125000},
    {"isin": "INE154A01025", "symbol": "ITC", "name": "ITC Ltd", "sector": "FMCG", "price": 45000},
    {"isin": "INE030A01027", "symbol": "HINDUNILVR", "name": "Hindustan Unilever", "sector": "FMCG", "price": 245000},
    {"isin": "INE585B01010", "symbol": "MARUTI", "name": "Maruti Suzuki India", "sector": "Auto", "price": 1250000},
    {"isin": "INE075A01022", "symbol": "WIPRO", "name": "Wipro Ltd", "sector": "IT", "price": 48000},
    {"isin": "INE101A01026", "symbol": "SBIN", "name": "State Bank of India", "sector": "Banking", "price": 82000},
    {"isin": "INE528G01035", "symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "Banking", "price": 185000},
    {"isin": "INE296A01024", "symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "sector": "Telecom", "price": 165000},
    {"isin": "INE018A01030", "symbol": "HCLTECH", "name": "HCL Technologies", "sector": "IT", "price": 162000},
    {"isin": "INE160A01022", "symbol": "SUNPHARMA", "name": "Sun Pharma Industries", "sector": "Pharma", "price": 175000},
    {"isin": "INE117A01022", "symbol": "TATAMOTORS", "name": "Tata Motors Ltd", "sector": "Auto", "price": 95000},
]

# -- Strategies --
STRATEGIES = [
    {"name": "Aurum Growth", "code": "AURUM_GRW", "approach": "growth"},
    {"name": "Aurum Value", "code": "AURUM_VAL", "approach": "value"},
    {"name": "Aurum Balanced", "code": "AURUM_BAL", "approach": "balanced"},
]

# -- Fee Schedules --
FEE_SCHEDULES = [
    {"name": "Standard", "mgmt": 2.0, "perf": 20.0, "hwm": True, "hurdle": 8.0},
    {"name": "Premium", "mgmt": 1.5, "perf": 15.0, "hwm": True, "hurdle": 10.0},
    {"name": "Elite", "mgmt": 1.0, "perf": 10.0, "hwm": True, "hurdle": 12.0},
]

# -- Brokers --
BROKERS = [
    {"name": "Zerodha Broking Ltd", "sebi_reg": "INZ000031633"},
    {"name": "ICICI Securities Ltd", "sebi_reg": "INZ000183631"},
]


def main():
    engine = create_engine(DB_URL, echo=False)
    Session = sessionmaker(bind=engine)
    db = Session()

    t = now()
    pw_hash = hash_password(PASSWORD)

    print("Seeding demo data into aurum-main...")

    # ========== 0. Clean up previous seed data ==========
    print("\n[0] Cleaning up previous seed data...")
    # Null out FKs before cleanup
    try:
        db.execute(text("UPDATE users SET client_id = NULL WHERE client_id IS NOT NULL"))
        db.commit()
    except Exception:
        db.rollback()

    # Delete in reverse dependency order
    for tbl in [
        "audit.audit_logs",
        "messaging.messages",
        "messaging.conversation_participants",
        "messaging.conversations",
        "trading.trades",
        "trading.order_allocations",
        "trading.orders",
        "portfolio.capital_flows",
        "portfolio.cash_ledger",
        "portfolio.holding_lots",
        "portfolio.holdings",
        "portfolio.portfolio_accounts",
        "client.client_risk_profiles",
        "client.nominees",
        "client.client_demat_accounts",
        "client.client_bank_accounts",
        "client.clients",
        "onboarding_documents",
        "onboarding_applications",
        "reference.strategy_constituents",
        "reference.strategies",
        "reference.benchmark_values",
        "reference.benchmarks",
        "reference.brokers",
        "portfolio.fee_schedules",
        "reference.securities_master",
        "email_verification_tokens",
        "refresh_tokens",
        "phone_verification_tokens",
    ]:
        try:
            db.execute(text(f"DELETE FROM {tbl}"))
        except Exception:
            db.rollback()
    # Delete seed users (not admin)
    db.execute(text("DELETE FROM users WHERE role IN ('investor','relationship_manager','compliance')"))
    db.commit()
    print("  Done.")

    # ========== 1. Create users ==========
    print("\n[1] Creating users...")

    user_ids = {}

    # Admin (already exists if you registered via UI - skip if so)
    admin_exists = db.execute(text("SELECT id FROM users WHERE role='admin'")).fetchone()
    if admin_exists:
        user_ids["admin"] = admin_exists[0]
        print(f"  Admin already exists: {admin_exists[0]}")
    else:
        admin_id = uuid.uuid4()
        db.execute(text("""
            INSERT INTO users (id, email, password_hash, full_name, role, is_active, email_verified, phone, phone_verified, created_at, updated_at)
            VALUES (:id, :email, :pw, :name, 'admin', true, true, :phone, false, :t, :t)
        """), {"id": admin_id, "email": "aariiparekh3012@gmail.com", "pw": pw_hash, "name": "Aarii P", "phone": "+919769795975", "t": t})
        user_ids["admin"] = admin_id
        print(f"  Admin: Aarii P ({admin_id})")

    # Compliance Officers
    co_ids = []
    for co in COMPLIANCE_OFFICERS:
        uid = uuid.uuid4()
        db.execute(text("""
            INSERT INTO users (id, email, password_hash, full_name, role, is_active, email_verified, phone, phone_verified, created_at, updated_at)
            VALUES (:id, :email, :pw, :name, 'compliance', true, true, :phone, true, :t, :t)
        """), {"id": uid, "email": co["email"], "pw": pw_hash, "name": co["name"], "phone": co["phone"], "t": t})
        co_ids.append(uid)
        print(f"  Compliance: {co['name']} ({uid})")

    # Relationship Managers
    rm_ids = []
    for rm in RMS:
        uid = uuid.uuid4()
        db.execute(text("""
            INSERT INTO users (id, email, password_hash, full_name, role, is_active, email_verified, phone, phone_verified, created_at, updated_at)
            VALUES (:id, :email, :pw, :name, 'relationship_manager', true, true, :phone, true, :t, :t)
        """), {"id": uid, "email": rm["email"], "pw": pw_hash, "name": rm["name"], "phone": rm["phone"], "t": t})
        rm_ids.append(uid)
        print(f"  RM: {rm['name']} ({uid})")

    # Investors
    investor_ids = []
    for inv in INVESTORS:
        uid = uuid.uuid4()
        db.execute(text("""
            INSERT INTO users (id, email, password_hash, full_name, role, is_active, email_verified, phone, phone_verified, created_at, updated_at)
            VALUES (:id, :email, :pw, :name, 'investor', true, true, :phone, true, :t, :t)
        """), {"id": uid, "email": inv["email"], "pw": pw_hash, "name": inv["name"], "phone": inv["phone"], "t": t})
        investor_ids.append(uid)
        print(f"  Investor: {inv['name']} ({uid})")

    db.commit()
    print(f"\n  Total users: 1 admin + {len(co_ids)} compliance + {len(rm_ids)} RMs + {len(investor_ids)} investors = {1 + len(co_ids) + len(rm_ids) + len(investor_ids)}")

    # ========== 2. Reference data ==========
    print("\n[2] Creating reference data...")

    # Securities
    security_ids = []
    for sec in SECURITIES:
        sid = uuid.uuid4()
        db.execute(text("""
            INSERT INTO reference.securities_master (id, isin, symbol, exchange, instrument_type, sector, is_active)
            VALUES (:id, :isin, :symbol, 'NSE', 'equity', :sector, true)
        """), {"id": sid, "isin": sec["isin"], "symbol": sec["symbol"], "sector": sec["sector"]})
        security_ids.append(sid)
    print(f"  {len(security_ids)} securities added")

    # Benchmarks
    nifty_id = uuid.uuid4()
    sensex_id = uuid.uuid4()
    db.execute(text("""
        INSERT INTO reference.benchmarks (id, name, code) VALUES (:id, 'NIFTY 50', 'NIFTY50')
    """), {"id": nifty_id})
    db.execute(text("""
        INSERT INTO reference.benchmarks (id, name, code) VALUES (:id, 'BSE SENSEX', 'SENSEX')
    """), {"id": sensex_id})
    print("  2 benchmarks added (NIFTY 50, SENSEX)")

    # Strategies
    strategy_ids = []
    benchmarks = [nifty_id, sensex_id, nifty_id]
    for i, strat in enumerate(STRATEGIES):
        sid = uuid.uuid4()
        db.execute(text("""
            INSERT INTO reference.strategies (id, name, code, approach, benchmark_id, is_active)
            VALUES (:id, :name, :code, :approach, :bench, true)
        """), {"id": sid, "name": strat["name"], "code": strat["code"], "approach": strat["approach"], "bench": benchmarks[i]})
        strategy_ids.append(sid)

        # Add constituents (random 5-8 stocks per strategy)
        stocks = random.sample(list(enumerate(security_ids)), random.randint(5, 8))
        total_weight = 0
        for j, (idx, sec_id) in enumerate(stocks):
            if j == len(stocks) - 1:
                weight = round(1.0 - total_weight, 4)
            else:
                weight = round(random.uniform(0.08, 0.20), 4)
                total_weight += weight
            db.execute(text("""
                INSERT INTO reference.strategy_constituents (id, strategy_id, security_id, target_weight)
                VALUES (:id, :strat, :sec, :w)
            """), {"id": uuid.uuid4(), "strat": sid, "sec": sec_id, "w": weight})
    print(f"  {len(strategy_ids)} strategies added with constituents")

    # Brokers
    broker_ids = []
    for br in BROKERS:
        bid = uuid.uuid4()
        db.execute(text("""
            INSERT INTO reference.brokers (id, name, sebi_reg_no, is_active)
            VALUES (:id, :name, :reg, true)
        """), {"id": bid, "name": br["name"], "reg": br["sebi_reg"]})
        broker_ids.append(bid)
    print(f"  {len(broker_ids)} brokers added")

    # Fee Schedules
    fee_ids = []
    for fs in FEE_SCHEDULES:
        fid = uuid.uuid4()
        db.execute(text("""
            INSERT INTO portfolio.fee_schedules (id, name, mgmt_fee_pct, perf_fee_pct, high_water_mark, hurdle_rate_pct)
            VALUES (:id, :name, :mgmt, :perf, :hwm, :hurdle)
        """), {"id": fid, "name": fs["name"], "mgmt": fs["mgmt"], "perf": fs["perf"], "hwm": fs["hwm"], "hurdle": fs["hurdle"]})
        fee_ids.append(fid)
    print(f"  {len(fee_ids)} fee schedules added")

    db.commit()

    # ========== 3. Onboarding applications & clients ==========
    print("\n[3] Creating onboarding applications and clients...")

    client_ids = []
    client_demat_ids = []

    for i, inv in enumerate(INVESTORS):
        inv_user_id = investor_ids[i]
        assigned_rm = rm_ids[i % len(rm_ids)]
        assigned_co = co_ids[i % len(co_ids)]
        pan = random_pan()
        pan_hash = hashlib.sha256(pan.encode()).hexdigest()
        investment = random.choice([5000000, 7500000, 10000000, 15000000, 25000000, 50000000])
        onb_date = random_date(300, 60)

        # Onboarding application (completed)
        app_id = uuid.uuid4()
        db.execute(text("""
            INSERT INTO onboarding_applications
            (id, status, investor_type, full_name, email, mobile, pan_hash, pan_enc,
             proposed_investment_paise, risk_category, risk_score, assigned_rm_id, assigned_compliance_id,
             created_at, updated_at)
            VALUES (:id, 'approved', 'individual', :name, :email, :phone, :pan_hash, :pan_enc,
                    :inv_paise, :risk_cat, :risk_score, :rm, :co, :t, :t)
        """), {
            "id": app_id, "name": inv["name"], "email": inv["email"], "phone": inv["phone"],
            "pan_hash": pan_hash, "pan_enc": f"ENC_{pan}",
            "inv_paise": investment * 100,
            "risk_cat": random.choice(["conservative", "moderate", "aggressive"]),
            "risk_score": random.randint(30, 90),
            "rm": assigned_rm, "co": assigned_co,
            "t": datetime.combine(onb_date, datetime.min.time()).replace(tzinfo=timezone.utc),
        })

        # Client record
        client_id = uuid.uuid4()
        client_code = f"AUR{i+1:04d}"
        db.execute(text("""
            INSERT INTO client.clients
            (id, onboarding_application_id, client_code, pan_hash, pan_enc, status,
             investor_type, full_name, email, mobile, assigned_rm_id, assigned_compliance_id,
             created_at, updated_at)
            VALUES (:id, :app, :code, :pan_hash, :pan_enc, 'active',
                    'individual', :name, :email, :phone, :rm, :co, :t, :t)
        """), {
            "id": client_id, "app": app_id, "code": client_code,
            "pan_hash": pan_hash, "pan_enc": f"ENC_{pan}",
            "name": inv["name"], "email": inv["email"], "phone": inv["phone"],
            "rm": assigned_rm, "co": assigned_co,
            "t": datetime.combine(onb_date, datetime.min.time()).replace(tzinfo=timezone.utc),
        })
        client_ids.append(client_id)

        # Link user to client
        db.execute(text("UPDATE users SET client_id = :cid WHERE id = :uid"),
                   {"cid": client_id, "uid": inv_user_id})

        # Bank account
        db.execute(text("""
            INSERT INTO client.client_bank_accounts (id, client_id, account_enc, ifsc, holder_name, is_primary, created_at)
            VALUES (:id, :cid, :acc, :ifsc, :name, true, :t)
        """), {
            "id": uuid.uuid4(), "cid": client_id,
            "acc": f"ENC_{random.randint(10000000000, 99999999999)}",
            "ifsc": f"HDFC0{random.randint(100000, 999999)}",
            "name": inv["name"],
            "t": datetime.combine(onb_date, datetime.min.time()).replace(tzinfo=timezone.utc),
        })

        # Demat account
        demat_id = uuid.uuid4()
        db.execute(text("""
            INSERT INTO client.client_demat_accounts (id, client_id, bo_id, depository, created_at)
            VALUES (:id, :cid, :bo, :dep, :t)
        """), {
            "id": demat_id, "cid": client_id,
            "bo": f"{random.randint(1000000000000000, 9999999999999999)}",
            "dep": random.choice(["NSDL", "CDSL"]),
            "t": datetime.combine(onb_date, datetime.min.time()).replace(tzinfo=timezone.utc),
        })
        client_demat_ids.append(demat_id)

        print(f"  Client {client_code}: {inv['name']} -> RM: {RMS[i % len(RMS)]['name']}, CO: {COMPLIANCE_OFFICERS[i % len(co_ids)]['name']}")

    db.commit()

    # ========== 4. Portfolio accounts, holdings, trades ==========
    print("\n[4] Creating portfolios, holdings, and trades...")

    portfolio_ids = []
    for i, client_id in enumerate(client_ids):
        strat_id = strategy_ids[i % len(strategy_ids)]
        fee_id = fee_ids[i % len(fee_ids)]
        inception = random_date(270, 50)
        cash = random.randint(100000, 5000000) * 100  # paise

        pa_id = uuid.uuid4()
        acct_code = f"PA{i+1:04d}"
        db.execute(text("""
            INSERT INTO portfolio.portfolio_accounts
            (id, client_id, strategy_id, demat_account_id, fee_schedule_id, account_code, status, inception_date, cash_balance_paise, created_at)
            VALUES (:id, :cid, :strat, :demat, :fee, :code, 'active', :inception, :cash, :t)
        """), {
            "id": pa_id, "cid": client_id, "strat": strat_id,
            "demat": client_demat_ids[i], "fee": fee_id,
            "code": acct_code, "inception": inception, "cash": cash, "t": t,
        })
        portfolio_ids.append(pa_id)

        # Holdings (3-6 random stocks per portfolio)
        num_holdings = random.randint(3, 6)
        chosen_stocks = random.sample(list(range(len(SECURITIES))), num_holdings)

        for stock_idx in chosen_stocks:
            sec_id = security_ids[stock_idx]
            sec_info = SECURITIES[stock_idx]
            qty = random.randint(10, 500)
            avg_cost = int(sec_info["price"] * random.uniform(0.85, 1.15))
            buy_date = random_date(250, 40)

            h_id = uuid.uuid4()
            db.execute(text("""
                INSERT INTO portfolio.holdings (id, portfolio_account_id, security_id, quantity, avg_cost_paise, updated_at)
                VALUES (:id, :pa, :sec, :qty, :cost, :t)
            """), {"id": h_id, "pa": pa_id, "sec": sec_id, "qty": qty, "cost": avg_cost, "t": t})

            # Holding lot
            db.execute(text("""
                INSERT INTO portfolio.holding_lots (id, holding_id, quantity, cost_paise, acquired_on)
                VALUES (:id, :hid, :qty, :cost, :d)
            """), {"id": uuid.uuid4(), "hid": h_id, "qty": qty, "cost": avg_cost, "d": buy_date})

            # Trade for this holding
            db.execute(text("""
                INSERT INTO trading.trades
                (id, portfolio_account_id, security_id, broker_id, side, quantity, price_paise, traded_at, contract_note, created_at)
                VALUES (:id, :pa, :sec, :br, 'buy', :qty, :price, :traded, :cn, :t)
            """), {
                "id": uuid.uuid4(), "pa": pa_id, "sec": sec_id,
                "br": random.choice(broker_ids),
                "qty": qty, "price": avg_cost,
                "traded": datetime.combine(buy_date, datetime.min.time()).replace(tzinfo=timezone.utc),
                "cn": f"CN{random.randint(100000, 999999)}",
                "t": t,
            })

        # Cash ledger entries
        # Initial deposit
        deposit_amt = random.randint(5000000, 50000000) * 100
        db.execute(text("""
            INSERT INTO portfolio.cash_ledger (id, portfolio_account_id, entry_type, amount_paise, balance_paise, posted_on, description, created_at)
            VALUES (:id, :pa, 'deposit', :amt, :amt, :d, 'Initial deposit', :t)
        """), {"id": uuid.uuid4(), "pa": pa_id, "amt": deposit_amt, "d": inception, "t": t})

        # Capital flow
        db.execute(text("""
            INSERT INTO portfolio.capital_flows (id, portfolio_account_id, flow_type, asset_kind, amount_paise, value_date)
            VALUES (:id, :pa, 'inflow', 'cash', :amt, :d)
        """), {"id": uuid.uuid4(), "pa": pa_id, "amt": deposit_amt, "d": inception})

        # Some orders
        for _ in range(random.randint(2, 5)):
            sec_idx = random.randint(0, len(SECURITIES) - 1)
            db.execute(text("""
                INSERT INTO trading.orders
                (id, strategy_id, security_id, side, quantity, order_type, status, created_at)
                VALUES (:id, :strat, :sec, :side, :qty, 'market', :status, :t)
            """), {
                "id": uuid.uuid4(), "strat": strat_id,
                "sec": security_ids[sec_idx],
                "side": random.choice(["buy", "sell"]),
                "qty": random.randint(10, 200),
                "status": random.choice(["executed", "executed", "executed", "pending_approval", "cancelled"]),
                "t": t - timedelta(days=random.randint(1, 60)),
            })

    db.commit()
    print(f"  {len(portfolio_ids)} portfolio accounts with holdings, trades, and orders created")

    # ========== 5. Audit log entries ==========
    print("\n[5] Creating audit log entries...")

    audit_events = [
        ("auth.login", "User logged in"),
        ("auth.register", "New user registered"),
        ("onboarding.approved", "Application approved"),
        ("order.created", "New order placed"),
        ("trade.executed", "Trade executed"),
    ]

    all_actors = [(uid, "investor") for uid in investor_ids] + \
                  [(uid, "relationship_manager") for uid in rm_ids] + \
                  [(uid, "compliance") for uid in co_ids]
    for _ in range(50):
        evt = random.choice(audit_events)
        actor_id, actor_role = random.choice(all_actors)
        db.execute(text("""
            INSERT INTO audit.audit_logs (id, event_type, description, actor_id, actor_role, ip_address, created_at)
            VALUES (:id, :evt, :desc, :actor, :role, :ip, :t)
        """), {
            "id": uuid.uuid4(), "evt": evt[0], "desc": evt[1],
            "actor": str(actor_id),
            "role": actor_role,
            "ip": f"192.168.1.{random.randint(10, 250)}",
            "t": t - timedelta(hours=random.randint(1, 720)),
        })
    db.commit()
    print("  50 audit log entries created")

    # ========== Done ==========
    print("\n" + "=" * 60)
    print("SEED COMPLETE!")
    print("=" * 60)
    print(f"\nAll demo accounts use password: {PASSWORD}")
    print(f"\nAdmin:      aariiparekh3012@gmail.com")
    print(f"Compliance: {', '.join(co['email'] for co in COMPLIANCE_OFFICERS)}")
    print(f"RMs:        {', '.join(rm['email'] for rm in RMS)}")
    print(f"Investors:  {INVESTORS[0]['email']} ... {INVESTORS[-1]['email']} (20 total)")
    print(f"\nRM assignments:")
    for i, inv in enumerate(INVESTORS):
        print(f"  {inv['name']:25s} -> {RMS[i % len(RMS)]['name']}")
    print(f"\nCompliance assignments:")
    for i, inv in enumerate(INVESTORS):
        print(f"  {inv['name']:25s} -> {COMPLIANCE_OFFICERS[i % len(co_ids)]['name']}")

    db.close()


if __name__ == "__main__":
    main()
