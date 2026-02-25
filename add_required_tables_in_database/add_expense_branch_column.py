#!/usr/bin/env python3
"""
Script to add branch column to expenses table
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

async def add_branch_column_to_expenses():
    """Add branch column to expenses table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if branch column already exists
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'expenses' AND column_name = 'branch'
            );
        """)

        if column_exists:
            print("Branch column already exists in expenses table")
        else:
            # Add branch column with default value
            await conn.execute("""
                ALTER TABLE expenses
                ADD COLUMN branch VARCHAR(100) DEFAULT 'European Sports Light House';
            """)
            print("Added branch column to expenses table")

            # Create index on branch
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expenses_branch ON expenses(branch);
            """)
            print("Created index on expenses.branch")

        await conn.close()
        print("Expenses table updated successfully!")

    except Exception as e:
        print(f"Error updating expenses table: {e}")

if __name__ == "__main__":
    asyncio.run(add_branch_column_to_expenses())
