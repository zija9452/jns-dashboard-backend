#!/usr/bin/env python3
"""
Migrate the Shop Orders / Shop Order Approval "seen" badge tracking from
per-role to per-user.

Accounts are unique, but roles are shared by multiple users (e.g. two admins
share the "admin" role) - tracking "seen" by role meant one admin opening a
page cleared the badge for every other admin too. This backfills the new
per-user tables from the existing role-level/global state so nothing that
was already seen suddenly reappears as a "new order" notification after
deploy:

- shop_order_seen_by_user: for every (order_id, role) already marked seen in
  the old shop_order_seen_by_role table, mark it seen for every user
  currently holding that role.
- shop_order_approval_seen_by_user: for every pending-approval order already
  marked seen_by_admin = TRUE (the old global flag), mark it seen for every
  current admin/production user.

Safe to re-run - table creation is IF NOT EXISTS and inserts use ON CONFLICT
DO NOTHING.
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


async def table_exists(conn, table: str) -> bool:
    return bool(await conn.fetchval(
        "SELECT table_name FROM information_schema.tables WHERE table_name = $1",
        table,
    ))


async def migrate_seen_tracking_to_per_user():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS shop_order_seen_by_user (
                order_id UUID NOT NULL REFERENCES shop_orders(id),
                user_id UUID NOT NULL REFERENCES users(id),
                PRIMARY KEY (order_id, user_id)
            );
        """)
        print("[OK] Ensured shop_order_seen_by_user table exists")

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS shop_order_approval_seen_by_user (
                order_id UUID NOT NULL REFERENCES shop_orders(id),
                user_id UUID NOT NULL REFERENCES users(id),
                PRIMARY KEY (order_id, user_id)
            );
        """)
        print("[OK] Ensured shop_order_approval_seen_by_user table exists")

        if await table_exists(conn, "shop_order_seen_by_role"):
            backfilled = await conn.fetchval("""
                WITH inserted AS (
                    INSERT INTO shop_order_seen_by_user (order_id, user_id)
                    SELECT sbr.order_id, u.id
                    FROM shop_order_seen_by_role sbr
                    JOIN roles r ON r.name = sbr.role
                    JOIN users u ON u.role_id = r.id
                    ON CONFLICT (order_id, user_id) DO NOTHING
                    RETURNING 1
                )
                SELECT count(*) FROM inserted;
            """)
            print(f"[OK] Backfilled {backfilled} shop_order_seen_by_user row(s) from shop_order_seen_by_role")
        else:
            print("[INFO] shop_order_seen_by_role table not found, skipping Shop Orders backfill")

        if await conn.fetchval(
            "SELECT column_name FROM information_schema.columns WHERE table_name = 'shop_orders' AND column_name = 'seen_by_admin'"
        ):
            backfilled = await conn.fetchval("""
                WITH inserted AS (
                    INSERT INTO shop_order_approval_seen_by_user (order_id, user_id)
                    SELECT so.id, u.id
                    FROM shop_orders so
                    CROSS JOIN users u
                    JOIN roles r ON r.id = u.role_id
                    WHERE so.approval_status = 'PENDING_APPROVAL'
                      AND so.seen_by_admin = TRUE
                      AND r.name IN ('admin', 'production')
                    ON CONFLICT (order_id, user_id) DO NOTHING
                    RETURNING 1
                )
                SELECT count(*) FROM inserted;
            """)
            print(f"[OK] Backfilled {backfilled} shop_order_approval_seen_by_user row(s) from seen_by_admin")
        else:
            print("[INFO] shop_orders.seen_by_admin column not found, skipping Approval backfill")

        await conn.close()
        print("\n[SUCCESS] Per-user seen tracking migrated successfully!")

    except Exception as e:
        print(f"[ERROR] Error migrating seen tracking: {e}")


if __name__ == "__main__":
    asyncio.run(migrate_seen_tracking_to_per_user())
