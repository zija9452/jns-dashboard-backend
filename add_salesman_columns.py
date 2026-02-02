#!/usr/bin/env python3
"""
Simple script to add missing columns to the salesman table
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment or use default
DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("NEON_DATABASE_URL", "postgresql://neondb_owner:npg_DSJeaHiRo69W@ep-falling-base-ahj4k5gl-pooler.c-3.us-east-1.aws.neon.tech:5432/neondb"))

async def add_missing_columns():
    """Add missing columns to the salesman table"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if phone column exists, if not add it
        phone_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'salesmen' AND column_name = 'phone'
        """)

        if not phone_exists:
            await conn.execute("ALTER TABLE salesmen ADD COLUMN phone VARCHAR(20) DEFAULT NULL;")
            print("Added phone column to salesmen table")
        else:
            print("Phone column already exists")

        # Check if address column exists, if not add it
        address_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'salesmen' AND column_name = 'address'
        """)

        if not address_exists:
            await conn.execute("ALTER TABLE salesmen ADD COLUMN address VARCHAR(200) DEFAULT NULL;")
            print("Added address column to salesmen table")
        else:
            print("Address column already exists")

        # Check if branch column exists, if not add it
        branch_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'salesmen' AND column_name = 'branch'
        """)

        if not branch_exists:
            await conn.execute("ALTER TABLE salesmen ADD COLUMN branch VARCHAR(50) DEFAULT NULL;")
            print("Added branch column to salesmen table")
        else:
            print("Branch column already exists")

        await conn.close()
        print("Database schema updated successfully!")

    except Exception as e:
        print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(add_missing_columns())