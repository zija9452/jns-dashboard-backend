#!/usr/bin/env python3
"""
Script to add created_by tracking to stock_entries:
1. Add created_by column to stock_entries table (nullable UUID FK -> users.id)
   - ON DELETE SET NULL so deleting a user later never breaks/removes their
     historical stock-in / adjustment entries.
2. One-time backfill: every existing row (created before this column existed)
   gets created_by set to the earliest-created admin user, so reports show a
   real username for old entries instead of a blank. New entries always get
   the actual logged-in user's id going forward - no fallback in report code.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("NEON_DATABASE_URL", ""))

# Convert from sqlalchemy asyncpg format to regular postgresql format if needed
if DATABASE_URL.startswith("postgresql+asyncpg"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


async def add_stock_entry_created_by_column():
    """Add created_by column to stock_entries table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'stock_entries'
                AND column_name = 'created_by'
            );
        """)

        if not column_exists:
            await conn.execute("""
                ALTER TABLE stock_entries
                ADD COLUMN created_by UUID REFERENCES users(id) ON DELETE SET NULL;
            """)
            print("Added created_by column to stock_entries table")
        else:
            print("created_by column already exists in stock_entries table")

        # One-time backfill: existing rows have no created_by - attribute them
        # to the earliest-created admin account so reports show a real user.
        admin_id = await conn.fetchval("""
            SELECT u.id
            FROM users u
            JOIN roles r ON u.role_id = r.id
            WHERE r.name = 'admin'
            ORDER BY u.created_at ASC
            LIMIT 1;
        """)

        if admin_id:
            update_result = await conn.execute("""
                UPDATE stock_entries
                SET created_by = $1
                WHERE created_by IS NULL;
            """, admin_id)
            # asyncpg returns a command tag string like "UPDATE 42"
            updated_count = update_result.split()[-1]
            print(f"Backfilled {updated_count} existing stock_entries row(s) to admin user {admin_id}")
        else:
            print("No admin user found - skipped backfill")

        await conn.close()
        print("\nDone.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(add_stock_entry_created_by_column())
