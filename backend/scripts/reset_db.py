"""Wipe all application tables so seed_presentation.py can run clean.

Reads DATABASE_URL directly from backend/.env — no app imports needed.

Run from ANY directory with venv active:
    python scripts/reset_db.py
    -- or --
    cd backend && python scripts/reset_db.py
"""
from __future__ import annotations
import os
import sys
from pathlib import Path


def load_env(env_path: Path) -> dict:
    env = {}
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip()
    return env


def main():
    # Find .env — look in backend/ relative to this script
    script_dir = Path(__file__).resolve().parent
    env_path = script_dir.parent / ".env"
    if not env_path.exists():
        print(f"ERROR: .env not found at {env_path}")
        return 1

    env = load_env(env_path)
    db_url = env.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not found in .env")
        return 1

    print(f"Connecting to: {db_url[:40]}...")

    # Try psycopg2 first, fall back to psycopg (v3)
    try:
        import psycopg2
        conn = psycopg2.connect(db_url.replace("postgresql+psycopg://", "postgresql://")
                                       .replace("postgresql+asyncpg://", "postgresql://"))
        conn.autocommit = False
        cur = conn.cursor()
        def execute(sql): cur.execute(sql)
        def commit(): conn.commit()
        print("Using psycopg2")
    except ImportError:
        try:
            import psycopg
            conn = psycopg.connect(db_url.replace("postgresql+psycopg://", "postgresql://")
                                         .replace("postgresql+asyncpg://", "postgresql://"))
            conn.autocommit = False
            cur = conn.cursor()
            def execute(sql): cur.execute(sql)
            def commit(): conn.commit()
            print("Using psycopg3")
        except ImportError:
            print("ERROR: neither psycopg2 nor psycopg installed in this venv")
            return 1

    tables = [
        # trading
        "trading.trades",
        "trading.order_allocations",
        "trading.orders",
        # performance
        "performance.performance_returns",
        "performance.valuation_snapshots",
        # portfolio
        "portfolio.capital_flows",
        "portfolio.cash_ledger",
        "portfolio.holding_lots",
        "portfolio.holdings",
        "portfolio.portfolio_accounts",
        "portfolio.fee_schedules",
        # messaging
        "messaging.messages",
        "messaging.conversation_participants",
        "messaging.conversations",
        # notifications
        "notifications.activity_log",
        "notifications.preferences",
        # client
        "client.client_demat_accounts",
        "client.nominees",
        "client.client_bank_accounts",
        "client.client_risk_profiles",
        "client.clients",
        # onboarding
        "public.onboarding_applications",
        # auth
        "public.email_verification_tokens",
        "public.password_reset_tokens",
        "public.phone_verification_codes",
        "public.refresh_tokens",
        "public.users",
        # reference
        "reference.strategy_constituents",
        "reference.strategies",
        "reference.benchmarks",
        "reference.brokers",
        "reference.securities",
    ]

    try:
        execute("SET session_replication_role = 'replica'")
        wiped = 0
        for t in tables:
            try:
                execute(f"TRUNCATE TABLE {t} CASCADE")
                print(f"  ✓ {t}")
                wiped += 1
            except Exception as e:
                print(f"  ✗ {t}: {e}")
                conn.rollback()
                execute("SET session_replication_role = 'replica'")
        execute("SET session_replication_role = 'origin'")
        commit()
    except Exception as e:
        print(f"FATAL: {e}")
        conn.rollback()
        return 1
    finally:
        conn.close()

    print(f"\n✅ Wiped {wiped}/{len(tables)} tables.")
    print("Now run:\n  python scripts\\seed_presentation.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
