#!/usr/bin/env python3
"""
Warehouse -> branch transfer (multi-branch, MULTI_BRANCH_PLAN.md Phase 7):
- warehouse_customers.destination_branch: branch code (e.g. 'karimabad') whose
  database receives the stock of this customer's warehouse invoices. NULL = old
  behaviour (stock goes to the Light House shop on the same product row).
- warehouse_invoices.transfer_status: NULL (no transfer) / 'pending' / 'done'.
- warehouse_invoices.transfer_error: last transfer failure message.

Runs on every branch database (schemas must stay identical). All columns are
nullable, existing rows are not touched. Idempotent - safe to run multiple times.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DB_ENVS = ["DATABASE_URL", "DATABASE_URL_KARIMABAD"]

COLUMNS = [
    ("warehouse_customers", "destination_branch", "VARCHAR(50) NULL"),
    ("warehouse_invoices", "transfer_status", "VARCHAR(20) NULL"),
    ("warehouse_invoices", "transfer_error", "TEXT NULL"),
]


async def migrate(env: str, url: str):
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(url)
    try:
        for table, column, ddl in COLUMNS:
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = $1 AND column_name = $2
                );
            """, table, column)
            if not exists:
                await conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl};")
                print(f"[{env}] Added {table}.{column}")
            else:
                print(f"[{env}] {table}.{column} already exists")
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
