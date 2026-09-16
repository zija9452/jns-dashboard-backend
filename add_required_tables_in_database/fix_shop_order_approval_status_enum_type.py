#!/usr/bin/env python3
"""
Fix-up script: convert shop_orders.approval_status from VARCHAR to a native
Postgres ENUM type (shoporderapprovalstatus), matching the existing
shoporderstatus enum convention used for the `status` column.

The original add_shop_order_approval_columns.py migration created
approval_status as plain VARCHAR, which SQLAlchemy/asyncpg can't compare
against the enum-typed bind parameters it generates for a Python str Enum
column ("operator does not exist: character varying = shoporderapprovalstatus").
This script is idempotent and safe to re-run.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("NEON_DATABASE_URL", ""))

if DATABASE_URL.startswith("postgresql+asyncpg"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

print(f"Using database URL: {DATABASE_URL}")


async def fix_approval_status_enum_type():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        current_type = await conn.fetchval("""
            SELECT data_type
            FROM information_schema.columns
            WHERE table_name = 'shop_orders' AND column_name = 'approval_status'
        """)

        if current_type is None:
            print("[ERROR] approval_status column does not exist - run add_shop_order_approval_columns.py first")
            await conn.close()
            return

        if current_type != "character varying":
            print(f"[INFO] approval_status is already type '{current_type}' - nothing to do")
            await conn.close()
            return

        await conn.execute("""
            DO $$ BEGIN
                CREATE TYPE shoporderapprovalstatus AS ENUM ('PENDING_APPROVAL', 'APPROVED', 'REJECTED');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        print("[OK] Ensured shoporderapprovalstatus enum type exists")

        # Drop the old varchar default before changing the column type, then
        # cast existing values across to the enum and set the new default.
        await conn.execute("ALTER TABLE shop_orders ALTER COLUMN approval_status DROP DEFAULT;")
        await conn.execute("""
            ALTER TABLE shop_orders
            ALTER COLUMN approval_status TYPE shoporderapprovalstatus
            USING approval_status::shoporderapprovalstatus;
        """)
        await conn.execute("""
            ALTER TABLE shop_orders
            ALTER COLUMN approval_status SET DEFAULT 'PENDING_APPROVAL'::shoporderapprovalstatus;
        """)
        print("[OK] Converted approval_status column to shoporderapprovalstatus enum")

        await conn.close()
        print("\n[SUCCESS] shop_orders.approval_status is now a native enum column!")

    except Exception as e:
        print(f"[ERROR] Error updating database schema: {e}")


if __name__ == "__main__":
    asyncio.run(fix_approval_status_enum_type())
