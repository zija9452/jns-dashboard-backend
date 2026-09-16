#!/usr/bin/env python3
"""
Script to add the approval workflow columns to the shop_orders table.

New shop orders start as PENDING_APPROVAL and only appear on the Shop Orders
page once an admin approves them. Existing rows are backfilled as APPROVED
(and already-seen) so nothing already in production disappears or triggers
a false "new order" badge after this migration runs.
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


async def column_exists(conn, table: str, column: str) -> bool:
    return bool(await conn.fetchval(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = $1 AND column_name = $2
        """,
        table, column,
    ))


async def add_shop_order_approval_columns():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        if await column_exists(conn, "shop_orders", "approval_status"):
            print("[INFO] approval_status column already exists in shop_orders table")
        else:
            # Native enum type, matching the shoporderstatus convention used
            # for the `status` column - SQLAlchemy/asyncpg compares Python str
            # Enum columns using an enum-typed cast, which a plain VARCHAR
            # column can't satisfy.
            await conn.execute("""
                DO $$ BEGIN
                    CREATE TYPE shoporderapprovalstatus AS ENUM ('PENDING_APPROVAL', 'APPROVED', 'REJECTED');
                EXCEPTION
                    WHEN duplicate_object THEN null;
                END $$;
            """)
            await conn.execute("""
                ALTER TABLE shop_orders
                ADD COLUMN approval_status shoporderapprovalstatus NOT NULL DEFAULT 'PENDING_APPROVAL';
            """)
            # Backfill existing orders as already-approved so they keep showing
            # up on the Shop Orders page exactly as before this migration.
            await conn.execute("""
                UPDATE shop_orders SET approval_status = 'APPROVED';
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS ix_shop_orders_approval_status ON shop_orders (approval_status);
            """)
            print("[OK] Added approval_status column to shop_orders table (backfilled existing rows as APPROVED)")

        if await column_exists(conn, "shop_orders", "approved_by"):
            print("[INFO] approved_by column already exists in shop_orders table")
        else:
            await conn.execute("ALTER TABLE shop_orders ADD COLUMN approved_by UUID REFERENCES users(id);")
            print("[OK] Added approved_by column to shop_orders table")

        if await column_exists(conn, "shop_orders", "approved_at"):
            print("[INFO] approved_at column already exists in shop_orders table")
        else:
            await conn.execute("ALTER TABLE shop_orders ADD COLUMN approved_at TIMESTAMP;")
            print("[OK] Added approved_at column to shop_orders table")

        if await column_exists(conn, "shop_orders", "rejected_at"):
            print("[INFO] rejected_at column already exists in shop_orders table")
        else:
            await conn.execute("ALTER TABLE shop_orders ADD COLUMN rejected_at TIMESTAMP;")
            print("[OK] Added rejected_at column to shop_orders table")

        if await column_exists(conn, "shop_orders", "seen_by_admin"):
            print("[INFO] seen_by_admin column already exists in shop_orders table")
        else:
            await conn.execute("ALTER TABLE shop_orders ADD COLUMN seen_by_admin BOOLEAN NOT NULL DEFAULT FALSE;")
            # Existing rows were just backfilled as APPROVED above, so there is
            # nothing pending approval for them - mark them seen too.
            await conn.execute("UPDATE shop_orders SET seen_by_admin = TRUE;")
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS ix_shop_orders_seen_by_admin ON shop_orders (seen_by_admin);
            """)
            print("[OK] Added seen_by_admin column to shop_orders table (backfilled existing rows as seen)")

        if await column_exists(conn, "shop_orders", "seen_in_shop_orders"):
            print("[INFO] seen_in_shop_orders column already exists in shop_orders table")
        else:
            await conn.execute("ALTER TABLE shop_orders ADD COLUMN seen_in_shop_orders BOOLEAN NOT NULL DEFAULT FALSE;")
            await conn.execute("UPDATE shop_orders SET seen_in_shop_orders = TRUE;")
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS ix_shop_orders_seen_in_shop_orders ON shop_orders (seen_in_shop_orders);
            """)
            print("[OK] Added seen_in_shop_orders column to shop_orders table (backfilled existing rows as seen)")

        await conn.close()
        print("\n[SUCCESS] shop_orders table schema updated successfully!")

    except Exception as e:
        print(f"[ERROR] Error updating database schema: {e}")


if __name__ == "__main__":
    asyncio.run(add_shop_order_approval_columns())
