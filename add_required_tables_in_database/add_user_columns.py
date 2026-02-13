#!/usr/bin/env python3
"""
Script to add missing columns to the user table
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

async def add_missing_columns():
    """Add missing columns to the user table"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if phone column exists, if not add it
        phone_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'phone'
        """)

        if not phone_exists:
            await conn.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(20) DEFAULT NULL;")
            print("Added phone column to users table")
        else:
            print("Phone column already exists")

        # Check if address column exists, if not add it
        address_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'address'
        """)

        if not address_exists:
            await conn.execute("ALTER TABLE users ADD COLUMN address VARCHAR(200) DEFAULT NULL;")
            print("Added address column to users table")
        else:
            print("Address column already exists")

        # Check if cnic column exists, if not add it
        cnic_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'cnic'
        """)

        if not cnic_exists:
            await conn.execute("ALTER TABLE users ADD COLUMN cnic VARCHAR(20) DEFAULT NULL;")
            print("Added cnic column to users table")
        else:
            print("CNIC column already exists")

        # Check if branch column exists, if not add it
        branch_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'branch'
        """)

        if not branch_exists:
            await conn.execute("ALTER TABLE users ADD COLUMN branch VARCHAR(50) DEFAULT NULL;")
            print("Added branch column to users table")
        else:
            print("Branch column already exists")

        await conn.close()
        print("Database schema updated successfully!")

    except Exception as e:
        print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(add_missing_columns())