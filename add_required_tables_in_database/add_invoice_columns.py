#!/usr/bin/env python3
"""
Script to add essential columns to the invoices table for walk-in invoices
Only adds the necessary fields for immediate payment walk-in invoices
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

async def add_missing_columns():
    """Add essential columns to the invoices table for walk-in invoices"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if invoice_no column exists, if not add it
        invoice_no_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'invoice_no'
        """)

        if not invoice_no_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN invoice_no VARCHAR(50) UNIQUE;")
            print("Added invoice_no column to invoices table")
        else:
            print("invoice_no column already exists")

        # Check if customer_id column exists, if not add it
        customer_id_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'customer_id'
        """)

        if not customer_id_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN customer_id UUID DEFAULT NULL;")
            print("Added customer_id column to invoices table")
        else:
            print("customer_id column already exists")

        # Check if items column exists, if not add it
        items_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'items'
        """)

        if not items_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN items TEXT DEFAULT NULL;")
            print("Added items column to invoices table")
        else:
            print("items column already exists")

        # Check if totals column exists, if not add it
        totals_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'totals'
        """)

        if not totals_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN totals TEXT DEFAULT NULL;")
            print("Added totals column to invoices table")
        else:
            print("totals column already exists")

        # Check if total_amount column exists, if not add it
        total_amount_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'total_amount'
        """)

        if not total_amount_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN total_amount NUMERIC(10, 2) DEFAULT 0.00;")
            print("Added total_amount column to invoices table")
        else:
            print("total_amount column already exists")

        # Check if amount_paid column exists, if not add it
        amount_paid_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'amount_paid'
        """)

        if not amount_paid_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN amount_paid NUMERIC(10, 2) DEFAULT 0.00;")
            print("Added amount_paid column to invoices table")
        else:
            print("amount_paid column already exists")

        # Check if discounts column exists, if not add it
        discounts_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'discounts'
        """)

        if not discounts_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN discounts NUMERIC(10, 2) DEFAULT 0.00;")
            print("Added discounts column to invoices table")
        else:
            print("discounts column already exists")

        # Check if status column exists, if not add it
        status_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'status'
        """)

        if not status_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN status VARCHAR(20) DEFAULT 'issued';")
            print("Added status column to invoices table")
        else:
            print("status column already exists")

        # Check if payment_method column exists, if not add it
        payment_method_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'payment_method'
        """)

        if not payment_method_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN payment_method VARCHAR(20) DEFAULT 'cash';")
            print("Added payment_method column to invoices table")
        else:
            print("payment_method column already exists")

        # Check if notes column exists, if not add it
        notes_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'notes'
        """)

        if not notes_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN notes TEXT DEFAULT NULL;")
            print("Added notes column to invoices table")
        else:
            print("notes column already exists")

        # Check if created_by column exists, if not add it
        created_by_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'created_by'
        """)

        if not created_by_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN created_by UUID DEFAULT NULL;")
            print("Added created_by column to invoices table")
        else:
            print("created_by column already exists")

        # Check if created_at column exists, if not add it
        created_at_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'created_at'
        """)

        if not created_at_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN created_at TIMESTAMP DEFAULT NOW();")
            print("Added created_at column to invoices table")
        else:
            print("created_at column already exists")

        # Check if updated_at column exists, if not add it
        updated_at_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'updated_at'
        """)

        if not updated_at_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN updated_at TIMESTAMP DEFAULT NOW();")
            print("Added updated_at column to invoices table")
        else:
            print("updated_at column already exists")

        # For walk-in invoices, we'll add balance_due (will be 0 for immediate payment)
        balance_due_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'balance_due'
        """)

        if not balance_due_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN balance_due NUMERIC(10, 2) DEFAULT 0.00;")
            print("Added balance_due column to invoices table")
        else:
            print("balance_due column already exists")

        # For walk-in invoices, we'll add payment_status (will be 'paid' for immediate payment)
        payment_status_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'payment_status'
        """)

        if not payment_status_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN payment_status VARCHAR(20) DEFAULT 'paid';")
            print("Added payment_status column to invoices table")
        else:
            print("payment_status column already exists")

        # For walk-in invoices, we'll add taxes column
        taxes_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'taxes'
        """)

        if not taxes_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN taxes NUMERIC(10, 2) DEFAULT 0.00;")
            print("Added taxes column to invoices table")
        else:
            print("taxes column already exists")

        # For walk-in invoices, we'll add payments_history column for consistency
        payments_history_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'payments_history'
        """)

        if not payments_history_exists:
            await conn.execute("ALTER TABLE invoices ADD COLUMN payments_history TEXT DEFAULT '[]';")
            print("Added payments_history column to invoices table")
        else:
            print("payments_history column already exists")

        await conn.close()
        print("Invoice database schema updated successfully with essential columns for walk-in invoices!")

    except Exception as e:
        print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(add_missing_columns())