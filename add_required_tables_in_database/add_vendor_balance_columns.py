#!/usr/bin/env python3
"""
Script to add balance and payments_history columns to vendors table
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

async def add_vendor_columns():
    """Add balance and payments_history columns to vendors table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if balance column exists
        balance_exists = await conn.fetchval("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'vendors' AND column_name = 'balance'
        """)
        
        if not balance_exists:
            # Add balance column
            await conn.execute("""
                ALTER TABLE vendors 
                ADD COLUMN balance NUMERIC(10, 2) DEFAULT 0.00
            """)
            print("Added 'balance' column to vendors table")
        else:
            print("'balance' column already exists")

        # Check if payments_history column exists
        payments_history_exists = await conn.fetchval("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'vendors' AND column_name = 'payments_history'
        """)
        
        if not payments_history_exists:
            # Add payments_history column
            await conn.execute("""
                ALTER TABLE vendors 
                ADD COLUMN payments_history TEXT DEFAULT '[]'
            """)
            print("Added 'payments_history' column to vendors table")
        else:
            print("'payments_history' column already exists")

        await conn.close()
        print("Vendor table columns added successfully!")

    except Exception as e:
        print(f"Error adding columns: {e}")
        raise

if __name__ == "__main__":
    print("=" * 60)
    print("Adding Vendor Balance Columns")
    print("=" * 60)
    asyncio.run(add_vendor_columns())
