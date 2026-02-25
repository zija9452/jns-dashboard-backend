#!/usr/bin/env python3
"""
Script to add expense column to expenses table
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

async def add_expense_column():
    """Add expense column to expenses table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if expense column exists
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'expenses' AND column_name = 'expense'
            );
        """)

        if column_exists:
            print("Expense column already exists in expenses table")
        else:
            # Add expense column
            await conn.execute("""
                ALTER TABLE expenses
                ADD COLUMN expense VARCHAR(100) NOT NULL DEFAULT '';
            """)
            print("Added expense column to expenses table")

        await conn.close()
        print("Expenses table updated successfully!")

    except Exception as e:
        print(f"Error updating expenses table: {e}")

if __name__ == "__main__":
    asyncio.run(add_expense_column())
