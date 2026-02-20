#!/usr/bin/env python3
"""
Script to remove code and commission_rate columns from the salesmen table
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
    # Replace 'postgresql+asyncpg://' with 'postgresql://'
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

print(f"Using database URL: {DATABASE_URL}")

async def remove_salesman_columns():
    """Remove code and commission_rate columns from the salesmen table"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if code column exists, if yes drop it
        code_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'salesmen' AND column_name = 'code'
        """)

        if code_exists:
            await conn.execute("ALTER TABLE salesmen DROP COLUMN IF EXISTS code;")
            print("Dropped code column from salesmen table")
        else:
            print("code column does not exist in salesmen table")

        # Check if commission_rate column exists, if yes drop it
        commission_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'salesmen' AND column_name = 'commission_rate'
        """)

        if commission_exists:
            await conn.execute("ALTER TABLE salesmen DROP COLUMN IF EXISTS commission_rate;")
            print("Dropped commission_rate column from salesmen table")
        else:
            print("commission_rate column does not exist in salesmen table")

        await conn.close()
        print("Salesmen table schema updated successfully!")

    except Exception as e:
        print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(remove_salesman_columns())
