#!/usr/bin/env python3
"""
Cash deposits (cash in hand taken to the bank):
- cash_deposits: one deposit (DEP-0001 / KDEP-0001), cash_from -> cash_to (info only),
  status PENDING / APPROVED / REJECTED (plain VARCHAR, not an enum).
- cash_deposit_slips: bank slip images of a deposit (several per deposit).

Runs on every branch database (schemas must stay identical). Idempotent - safe to run
multiple times.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DB_ENVS = ["DATABASE_URL", "DATABASE_URL_KARIMABAD"]

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS cash_deposits (
        id UUID PRIMARY KEY,
        deposit_no VARCHAR(20) NOT NULL UNIQUE,
        cash_from DATE NOT NULL,
        cash_to DATE NOT NULL,
        deposit_date DATE NOT NULL,
        total_amount NUMERIC(12, 2) NOT NULL,
        notes VARCHAR(500) NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
        submitted_by UUID NOT NULL REFERENCES users(id),
        submitted_at TIMESTAMP NOT NULL,
        reviewed_by UUID NULL REFERENCES users(id),
        reviewed_at TIMESTAMP NULL,
        reject_reason VARCHAR(500) NULL,
        branch VARCHAR(100) NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_cash_deposits_deposit_no ON cash_deposits (deposit_no);",
    "CREATE INDEX IF NOT EXISTS ix_cash_deposits_deposit_date ON cash_deposits (deposit_date);",
    "CREATE INDEX IF NOT EXISTS ix_cash_deposits_status ON cash_deposits (status);",
    "CREATE INDEX IF NOT EXISTS ix_cash_deposits_submitted_by ON cash_deposits (submitted_by);",
    "CREATE INDEX IF NOT EXISTS ix_cash_deposits_submitted_at ON cash_deposits (submitted_at);",
    "CREATE INDEX IF NOT EXISTS ix_cash_deposits_branch ON cash_deposits (branch);",
    """
    CREATE TABLE IF NOT EXISTS cash_deposit_slips (
        id UUID PRIMARY KEY,
        deposit_id UUID NOT NULL REFERENCES cash_deposits(id) ON DELETE CASCADE,
        file_url VARCHAR(500) NOT NULL,
        public_id VARCHAR(255) NULL,
        bank_name VARCHAR(100) NOT NULL,
        slip_no VARCHAR(100) NULL,
        amount NUMERIC(12, 2) NOT NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_cash_deposit_slips_deposit_id ON cash_deposit_slips (deposit_id);",
]


async def migrate(env: str, url: str):
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(url)
    try:
        async with conn.transaction():
            for sql in STATEMENTS:
                await conn.execute(sql)
        print(f"[{env}] cash_deposits + cash_deposit_slips ready")
    finally:
        await conn.close()


async def main():
    for env in DB_ENVS:
        url = os.getenv(env)
        if not url:
            print(f"[{env}] not set - skipped")
            continue
        try:
            await migrate(env, url)
        except Exception as e:
            print(f"[{env}] Error: {e}")
            import traceback
            traceback.print_exc()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
