#!/usr/bin/env python3
"""
Monthly expenses (Expenses page Daily / Monthly):
- expenses.is_monthly: TRUE = rent, salary... (admin only, not paid from the counter).
  Kept out of daily cash / daily profit; Sales View shows it as "Monthly Expense".
- Replaces expenses.is_admin_only (the old "Private" checkbox): the column is renamed, so
  every old private expense becomes a Monthly one.

Runs on every branch database (schemas must stay identical). Idempotent.
Run together with the code deploy - the old code still reads is_admin_only.
"""
import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_ENVS = ["DATABASE_URL", "DATABASE_URL_KARIMABAD"]


async def column_exists(conn, column: str) -> bool:
    return await conn.fetchval("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'expenses' AND column_name = $1
        );
    """, column)


async def migrate(env: str, url: str):
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(url)
    try:
        if await column_exists(conn, "is_monthly"):
            print(f"[{env}] expenses.is_monthly already exists")
            return
        async with conn.transaction():
            if await column_exists(conn, "is_admin_only"):
                await conn.execute("ALTER TABLE expenses RENAME COLUMN is_admin_only TO is_monthly;")
                await conn.execute("ALTER INDEX IF EXISTS ix_expenses_is_admin_only RENAME TO ix_expenses_is_monthly;")
                count = await conn.fetchval("SELECT COUNT(*) FROM expenses WHERE is_monthly;")
                print(f"[{env}] Renamed expenses.is_admin_only -> is_monthly ({count} private expenses are now Monthly)")
            else:
                await conn.execute("ALTER TABLE expenses ADD COLUMN is_monthly BOOLEAN NOT NULL DEFAULT FALSE;")
                print(f"[{env}] Added expenses.is_monthly")
            await conn.execute("ALTER TABLE expenses ALTER COLUMN is_monthly SET DEFAULT FALSE;")
            await conn.execute("CREATE INDEX IF NOT EXISTS ix_expenses_is_monthly ON expenses (is_monthly);")
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
            print(f"[{env}] FAILED: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
