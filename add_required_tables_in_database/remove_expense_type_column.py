#!/usr/bin/env python3
"""
Script to remove expense_type column from expenses table
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

async def remove_expense_type_column():
    """Remove expense_type column from expenses table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if expense_type column exists
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'expenses' AND column_name = 'expense_type'
            );
        """)

        if column_exists:
            # Drop expense_type column
            await conn.execute("""
                ALTER TABLE expenses DROP COLUMN expense_type;
            """)
            print("Removed expense_type column from expenses table")
        else:
            print("expense_type column does not exist in expenses table")

        await conn.close()
        print("Expenses table updated successfully!")

    except Exception as e:
        print(f"Error updating expenses table: {e}")

if __name__ == "__main__":
    asyncio.run(remove_expense_type_column())
