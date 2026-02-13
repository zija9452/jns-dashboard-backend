#!/usr/bin/env python3
"""
Script to update the invoices table schema for walk-in invoices
Changes the database schema to match the updated Invoice model
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

async def update_invoice_schema():
    """Update the invoices table schema to match the new model for walk-in invoices"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Add customer_name column if it doesn't exist
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

        # Make customer_id column optional (allow NULL) if it exists
        customer_id_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'customer_id'
        """)

        if customer_id_exists:
            # Change customer_id to allow NULL values
            await conn.execute("ALTER TABLE invoices ALTER COLUMN customer_id DROP NOT NULL;")
            print("Made customer_id column optional (NULL allowed)")
        else:
            print("customer_id column does not exist")

        # Check if salesman_id column exists and remove it if needed
        salesman_id_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'salesman_id'
        """)

        if salesman_id_exists:
            # Remove salesman_id column as it's not needed for walk-in invoices
            await conn.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS salesman_id;")
            print("Removed salesman_id column from invoices table (not needed for walk-in invoices)")
        else:
            print("salesman_id column does not exist")

        await conn.close()
        print("Invoice database schema updated successfully for walk-in invoices!")

    except Exception as e:
        print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(update_invoice_schema())