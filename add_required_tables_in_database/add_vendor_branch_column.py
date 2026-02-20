#!/usr/bin/env python3
"""
Script to add branch column to the vendors table
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

async def add_vendor_branch_column():
    """Add branch column to the vendors table"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if branch column exists, if not add it
        branch_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'vendors' AND column_name = 'branch'
        """)

        if not branch_exists:
            await conn.execute("ALTER TABLE vendors ADD COLUMN branch VARCHAR(200) DEFAULT NULL;")
            print("Added branch column to vendors table")
        else:
            print("branch column already exists in vendors table")

        await conn.close()
        print("Vendors table schema updated successfully!")

    except Exception as e:
        print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(add_vendor_branch_column())
