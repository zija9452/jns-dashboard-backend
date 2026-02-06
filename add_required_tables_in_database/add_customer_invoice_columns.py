#!/usr/bin/env python3
"""
Script to add missing payment tracking columns to the customer_invoices table
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

async def add_missing_columns():
    """Add missing payment tracking columns to the customer_invoices table"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if total_amount column exists, if not add it
        total_amount_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'customer_invoices' AND column_name = 'total_amount'
        """)

        if not total_amount_exists:
            await conn.execute("ALTER TABLE customer_invoices ADD COLUMN total_amount NUMERIC(10, 2) DEFAULT 0.00;")
            print("Added total_amount column to customer_invoices table")
        else:
            print("total_amount column already exists")

        # Check if amount_paid column exists, if not add it
        amount_paid_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'customer_invoices' AND column_name = 'amount_paid'
        """)

        if not amount_paid_exists:
            await conn.execute("ALTER TABLE customer_invoices ADD COLUMN amount_paid NUMERIC(10, 2) DEFAULT 0.00;")
            print("Added amount_paid column to customer_invoices table")
        else:
            print("amount_paid column already exists")

        # Check if balance_due column exists, if not add it
        balance_due_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'customer_invoices' AND column_name = 'balance_due'
        """)

        if not balance_due_exists:
            await conn.execute("ALTER TABLE customer_invoices ADD COLUMN balance_due NUMERIC(10, 2) DEFAULT 0.00;")
            print("Added balance_due column to customer_invoices table")
        else:
            print("balance_due column already exists")

        # Check if payment_status column exists, if not add it
        payment_status_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'customer_invoices' AND column_name = 'payment_status'
        """)

        if not payment_status_exists:
            await conn.execute("ALTER TABLE customer_invoices ADD COLUMN payment_status VARCHAR(20) DEFAULT 'unpaid';")
            print("Added payment_status column to customer_invoices table")
        else:
            print("payment_status column already exists")

        # Check if payments_history column exists, if not add it
        payments_history_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'customer_invoices' AND column_name = 'payments_history'
        """)

        if not payments_history_exists:
            await conn.execute("ALTER TABLE customer_invoices ADD COLUMN payments_history TEXT DEFAULT '[]';")
            print("Added payments_history column to customer_invoices table")
        else:
            print("payments_history column already exists")

        await conn.close()
        print("Customer invoice database schema updated successfully!")

    except Exception as e:
        print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(add_missing_columns())