#!/usr/bin/env python3
"""
Script to add payment method columns and total columns to daily_cash table
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
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

print(f"Using database URL: {DATABASE_URL}")

async def add_payment_method_columns():
    """Add payment method columns to daily_cash table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        print("Adding payment method columns to daily_cash table...")

        # Add Cash columns (if not exist)
        await conn.execute("""
            ALTER TABLE daily_cash
            ADD COLUMN IF NOT EXISTS cash_opening NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
            ADD COLUMN IF NOT EXISTS cash_closing NUMERIC(10, 2),
            ADD COLUMN IF NOT EXISTS cash_sales NUMERIC(10, 2) NOT NULL DEFAULT 0.00
        """)
        print("  Cash columns OK")

        # Add EasyPaisa Zohaib columns
        await conn.execute("""
            ALTER TABLE daily_cash
            ADD COLUMN IF NOT EXISTS easypaisa_zohaib_opening NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
            ADD COLUMN IF NOT EXISTS easypaisa_zohaib_closing NUMERIC(10, 2),
            ADD COLUMN IF NOT EXISTS easypaisa_zohaib_sales NUMERIC(10, 2) NOT NULL DEFAULT 0.00
        """)
        print("  EasyPaisa Zohaib columns OK")

        # Add EasyPaisa Yasir columns
        await conn.execute("""
            ALTER TABLE daily_cash
            ADD COLUMN IF NOT EXISTS easypaisa_yasir_opening NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
            ADD COLUMN IF NOT EXISTS easypaisa_yasir_closing NUMERIC(10, 2),
            ADD COLUMN IF NOT EXISTS easypaisa_yasir_sales NUMERIC(10, 2) NOT NULL DEFAULT 0.00
        """)
        print("  EasyPaisa Yasir columns OK")

        # Add Bank columns
        await conn.execute("""
            ALTER TABLE daily_cash
            ADD COLUMN IF NOT EXISTS bank_opening NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
            ADD COLUMN IF NOT EXISTS bank_closing NUMERIC(10, 2),
            ADD COLUMN IF NOT EXISTS bank_sales NUMERIC(10, 2) NOT NULL DEFAULT 0.00
        """)
        print("  Bank columns OK")

        # Add Total columns
        await conn.execute("""
            ALTER TABLE daily_cash
            ADD COLUMN IF NOT EXISTS total_opening NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
            ADD COLUMN IF NOT EXISTS total_sales NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
            ADD COLUMN IF NOT EXISTS total_expected NUMERIC(10, 2),
            ADD COLUMN IF NOT EXISTS total_closing NUMERIC(10, 2),
            ADD COLUMN IF NOT EXISTS total_difference NUMERIC(10, 2)
        """)
        print("  Total columns OK")

        await conn.close()
        print("\nAll columns added successfully!")

    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(add_payment_method_columns())
