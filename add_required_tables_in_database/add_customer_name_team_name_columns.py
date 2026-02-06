#!/usr/bin/env python3
"""
Script to add customer_name and team_name columns to the customer_invoices table
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("NEON_DATABASE_URL", ""))
if not DATABASE_URL:
    # Default fallback URL
    DATABASE_URL = "postgresql://neondb_owner:npg_DSJeaHiRo69W@ep-falling-base-ahj4k5gl-pooler.c-3.us-east-1.aws.neon.tech:5432/neondb"

# Convert from sqlalchemy asyncpg format to regular postgresql format if needed
if DATABASE_URL.startswith("postgresql+asyncpg"):
    # Replace 'postgresql+asyncpg://' with 'postgresql://'
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

print(f"Using database URL: {DATABASE_URL}")

async def add_customer_name_team_name_columns():
    """Add customer_name and team_name columns to the customer_invoices table"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if customer_name column exists, if not add it
        customer_name_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'customer_invoices' AND column_name = 'customer_name'
        """)

        if not customer_name_exists:
            await conn.execute("ALTER TABLE customer_invoices ADD COLUMN customer_name VARCHAR(255);")
            print("Added customer_name column to customer_invoices table")
        else:
            print("customer_name column already exists")

        # Check if team_name column exists, if not add it
        team_name_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'customer_invoices' AND column_name = 'team_name'
        """)

        if not team_name_exists:
            await conn.execute("ALTER TABLE customer_invoices ADD COLUMN team_name VARCHAR(255);")
            print("Added team_name column to customer_invoices table")
        else:
            print("team_name column already exists")

        await conn.close()
        print("Customer invoice database schema updated successfully with customer_name and team_name columns!")

    except Exception as e:
        print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(add_customer_name_team_name_columns())