#!/usr/bin/env python3
"""
Script to remove billing_addr, shipping_addr, and credit_limit columns from the customers table
Note: email is stored in contacts JSON, so no separate column to remove
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

async def remove_customer_columns():
    """Remove billing_addr, shipping_addr, and credit_limit columns from the customers table"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Check and drop billing_addr column
        billing_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'customers' AND column_name = 'billing_addr'
        """)

        if billing_exists:
            await conn.execute("ALTER TABLE customers DROP COLUMN IF EXISTS billing_addr;")
            print("[OK] Dropped billing_addr column from customers table")
        else:
            print("[INFO] billing_addr column does not exist in customers table")

        # Check and drop shipping_addr column
        shipping_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'customers' AND column_name = 'shipping_addr'
        """)

        if shipping_exists:
            await conn.execute("ALTER TABLE customers DROP COLUMN IF EXISTS shipping_addr;")
            print("[OK] Dropped shipping_addr column from customers table")
        else:
            print("[INFO] shipping_addr column does not exist in customers table")

        # Check and drop credit_limit column
        credit_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'customers' AND column_name = 'credit_limit'
        """)

        if credit_exists:
            await conn.execute("ALTER TABLE customers DROP COLUMN IF EXISTS credit_limit;")
            print("[OK] Dropped credit_limit column from customers table")
        else:
            print("[INFO] credit_limit column does not exist in customers table")

        await conn.close()
        print("\n[SUCCESS] Customers table schema updated successfully!")

    except Exception as e:
        print(f"[ERROR] Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(remove_customer_columns())
