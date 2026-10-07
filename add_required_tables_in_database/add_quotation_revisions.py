#!/usr/bin/env python3
"""
Quotation revisions (QUO-0012 Rev.1 -> Rev.2):
- A revision is a NEW row with the same quotation_no and revision + 1, so the old
  unique (quotation_no) becomes unique (quotation_no, revision).
- quotations.replaced_by_id: set on the old row -> the revision that replaced it
  (the old row's status becomes 'REVISED': read-only, PDF only).
- quotations.status_before_revised: the old row's status before it became REVISED,
  put back if the newer revision is deleted.
- status is a VARCHAR column, but SQLAlchemy casts it to the Postgres enum type
  `quotationstatus` on write, so 'REVISED' is added to that type too.

Runs on every branch database (schemas must stay identical). Idempotent - safe to run
multiple times.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DB_ENVS = ["DATABASE_URL", "DATABASE_URL_KARIMABAD"]

COLUMNS = [
    ("replaced_by_id", "UUID NULL REFERENCES quotations(id)"),
    ("status_before_revised", "VARCHAR(20) NULL"),
]


async def migrate(env: str, url: str):
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(url)
    try:
        # ALTER TYPE ... ADD VALUE can't run inside a transaction block on older Postgres.
        has_type = await conn.fetchval("SELECT 1 FROM pg_type WHERE typname = 'quotationstatus'")
        if has_type:
            await conn.execute("ALTER TYPE quotationstatus ADD VALUE IF NOT EXISTS 'REVISED';")
            print(f"[{env}] quotationstatus enum has REVISED")
        async with conn.transaction():
            for column, ddl in COLUMNS:
                exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'quotations' AND column_name = $1
                    );
                """, column)
                if not exists:
                    await conn.execute(f"ALTER TABLE quotations ADD COLUMN {column} {ddl};")
                    print(f"[{env}] Added quotations.{column}")
                else:
                    print(f"[{env}] quotations.{column} already exists")

            old_unique = await conn.fetchval(
                "SELECT 1 FROM pg_constraint WHERE conrelid = 'quotations'::regclass AND conname = 'quotations_quotation_no_key'"
            )
            if old_unique:
                await conn.execute("ALTER TABLE quotations DROP CONSTRAINT quotations_quotation_no_key;")
                print(f"[{env}] Dropped unique (quotation_no)")

            new_unique = await conn.fetchval(
                "SELECT 1 FROM pg_constraint WHERE conrelid = 'quotations'::regclass AND conname = 'uq_quotations_no_revision'"
            )
            if not new_unique:
                await conn.execute(
                    "ALTER TABLE quotations ADD CONSTRAINT uq_quotations_no_revision UNIQUE (quotation_no, revision);"
                )
                print(f"[{env}] Added unique (quotation_no, revision)")
            else:
                print(f"[{env}] unique (quotation_no, revision) already exists")
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
