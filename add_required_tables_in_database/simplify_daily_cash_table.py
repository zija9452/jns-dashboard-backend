#!/usr/bin/env python3
"""
Script to simplify daily_cash table to cash-only tracking
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("NEON_DATABASE_URL", ""))

if DATABASE_URL.startswith("postgresql+asyncpg"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

print(f"Using database URL: {DATABASE_URL}")

async def simplify_daily_cash_table():
    """Simplify daily_cash table to cash-only columns"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Drop payment method columns one by one
        print("Removing payment method columns...")
        
        columns_to_drop = [
            'easypaisa_zohaib_opening', 'easypaisa_zohaib_closing', 'easypaisa_zohaib_sales', 'easypaisa_zohaib_notes',
            'easypaisa_yasir_opening', 'easypaisa_yasir_closing', 'easypaisa_yasir_sales', 'easypaisa_yasir_notes',
            'bank_opening', 'bank_closing', 'bank_sales', 'bank_notes', 'cash_notes'
        ]
        
        for col in columns_to_drop:
            try:
                await conn.execute(f"ALTER TABLE daily_cash DROP COLUMN IF EXISTS {col}")
            except:
                pass
        
        # Add cash_expected and cash_difference if not exist
        await conn.execute("""
            ALTER TABLE daily_cash
            ADD COLUMN IF NOT EXISTS cash_expected NUMERIC(10, 2),
            ADD COLUMN IF NOT EXISTS cash_difference NUMERIC(10, 2)
        """)
        
        # Rename old columns if they exist
        old_col_exists = await conn.fetchval("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'daily_cash' AND column_name = 'opening_amount'
        """)
        
        if old_col_exists:
            # Check if cash_opening already exists
            cash_opening_exists = await conn.fetchval("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'daily_cash' AND column_name = 'cash_opening'
            """)
            
            if not cash_opening_exists:
                await conn.execute("ALTER TABLE daily_cash RENAME COLUMN opening_amount TO cash_opening")
                await conn.execute("ALTER TABLE daily_cash RENAME COLUMN closing_amount TO cash_closing")
                await conn.execute("ALTER TABLE daily_cash RENAME COLUMN sales_amount TO cash_sales")
                print("Renamed old columns to new names")
            else:
                print("Columns already renamed")
        
        await conn.close()
        print("Daily cash table simplified successfully!")

    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(simplify_daily_cash_table())
