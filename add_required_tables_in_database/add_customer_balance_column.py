#!/usr/bin/env python3
"""
Script to add cus_balance column to the customers table
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

async def add_customer_balance_column():
    """Add cus_balance column to the customers table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if cus_balance column exists
        balance_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'customers' AND column_name = 'cus_balance'
        """)

        if balance_exists:
            print("[INFO] cus_balance column already exists in customers table")
        else:
            await conn.execute("ALTER TABLE customers ADD COLUMN cus_balance DECIMAL(10,2) DEFAULT 0.00;")
            print("[OK] Added cus_balance column to customers table")

        await conn.close()
        print("\n[SUCCESS] Customers table schema updated successfully!")

    except Exception as e:
        print(f"[ERROR] Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(add_customer_balance_column())
