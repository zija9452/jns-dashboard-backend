#!/usr/bin/env python3
"""
Script to add cnic, sal_id_fk, and branch columns to the customers table
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

async def add_customer_columns():
    """Add cnic, sal_id_fk, and branch columns to the customers table"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if cnic column exists, if not add it
        cnic_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'customers' AND column_name = 'cnic'
        """)

        if not cnic_exists:
            await conn.execute("ALTER TABLE customers ADD COLUMN cnic VARCHAR(20) DEFAULT NULL;")
            print("Added cnic column to customers table")
        else:
            print("cnic column already exists")

        # Check if sal_id_fk column exists, if not add it
        sal_id_fk_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'customers' AND column_name = 'sal_id_fk'
        """)

        if not sal_id_fk_exists:
            await conn.execute("ALTER TABLE customers ADD COLUMN sal_id_fk UUID DEFAULT NULL;")
            print("Added sal_id_fk column to customers table")
        else:
            print("sal_id_fk column already exists")

        # Check if branch column exists, if not add it
        branch_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'customers' AND column_name = 'branch'
        """)

        if not branch_exists:
            await conn.execute("ALTER TABLE customers ADD COLUMN branch VARCHAR(200) DEFAULT NULL;")
            print("Added branch column to customers table")
        else:
            print("branch column already exists")

        await conn.close()
        print("Customers table schema updated successfully!")

    except Exception as e:
        print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(add_customer_columns())
