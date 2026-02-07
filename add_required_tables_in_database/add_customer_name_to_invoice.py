#!/usr/bin/env python3
"""
Script to add customer_name column to the invoices table for walk-in invoices
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("NEON_DATABASE_URL", ""))
if not DATABASE_URL:
    # Default fallback URL - using the one from docker-compose.yml
    DATABASE_URL = "postgresql+asyncpg://neondb_owner:npg_DSJeaHiRo69W@ep-falling-base-ahj4k5gl-pooler.c-3.us-east-1.aws.neon.tech:5432/neondb"

# Convert from sqlalchemy asyncpg format to regular postgresql format if needed
if DATABASE_URL.startswith("postgresql+asyncpg"):
    # Replace 'postgresql+asyncpg://' with 'postgresql://'
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

print(f"Using database URL: {DATABASE_URL}")

async def add_customer_name_column():
    """Add customer_name column to the invoices table"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if customer_name column exists, if not add it
        customer_name_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'customer_name'
        """)

        if not customer_name_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN customer_name VARCHAR(100) DEFAULT 'Walk-in Customer';")
            print("Added customer_name column to invoices table")
        else:
            print("customer_name column already exists")

        # Also remove the customer_id column if it exists (optional, for cleanup)
        # Note: We'll keep it for now to avoid breaking existing functionality
        print("Database schema updated successfully with customer_name column!")

        await conn.close()

    except Exception as e:
        print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(add_customer_name_column())