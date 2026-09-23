#!/usr/bin/env python3
"""
Script to add is_admin_only column to expenses table
Expenses marked admin-only are hidden from cashiers in lists, dashboard totals/charts,
and daily cash reconciliation.
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

print(f"Using database URL: {DATABASE_URL}")

async def add_is_admin_only_column():
    """Add is_admin_only column to expenses table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'expenses' AND column_name = 'is_admin_only'
            );
        """)

        if column_exists:
            print("is_admin_only column already exists in expenses table")
        else:
            await conn.execute("""
                ALTER TABLE expenses
                ADD COLUMN is_admin_only BOOLEAN NOT NULL DEFAULT FALSE;
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS ix_expenses_is_admin_only ON expenses (is_admin_only);
            """)
            print("Added is_admin_only column (+ index) to expenses table")

        await conn.close()
        print("Expenses table updated successfully!")

    except Exception as e:
        print(f"Error updating expenses table: {e}")

if __name__ == "__main__":
    asyncio.run(add_is_admin_only_column())
