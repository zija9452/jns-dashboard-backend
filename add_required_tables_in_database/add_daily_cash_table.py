#!/usr/bin/env python3
"""
Script to add daily_cash table for tracking daily opening and closing balances by payment method
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

async def add_daily_cash_table():
    """Add daily_cash table to the database"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if daily_cash table exists
        table_exists = await conn.fetchval("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'daily_cash'
        """)

        if not table_exists:
            # Create daily_cash table with payment method columns
            await conn.execute("""
                CREATE TABLE daily_cash (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    date DATE UNIQUE NOT NULL,
                    
                    -- Cash
                    cash_opening NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                    cash_closing NUMERIC(10, 2),
                    cash_sales NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                    cash_notes TEXT,
                    
                    -- Easypaisa Zohaib
                    easypaisa_zohaib_opening NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                    easypaisa_zohaib_closing NUMERIC(10, 2),
                    easypaisa_zohaib_sales NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                    easypaisa_zohaib_notes TEXT,
                    
                    -- Easypaisa Yasir
                    easypaisa_yasir_opening NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                    easypaisa_yasir_closing NUMERIC(10, 2),
                    easypaisa_yasir_sales NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                    easypaisa_yasir_notes TEXT,
                    
                    -- Bank
                    bank_opening NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                    bank_closing NUMERIC(10, 2),
                    bank_sales NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                    bank_notes TEXT,
                    
                    -- General
                    opening_notes TEXT,
                    closing_notes TEXT,
                    created_at DATE DEFAULT CURRENT_DATE,
                    updated_at DATE DEFAULT CURRENT_DATE
                )
            """)
            
            await conn.execute("CREATE INDEX idx_daily_cash_date ON daily_cash(date)")
            print("Created daily_cash table with payment method columns")
        else:
            print("daily_cash table already exists")
            
            # Check if we need to add new columns (migration from old schema)
            await migrate_daily_cash_table(conn)

        await conn.close()
        print("Daily cash table setup completed successfully!")

    except Exception as e:
        print(f"Error setting up daily cash table: {e}")
        raise

async def migrate_daily_cash_table(conn):
    """Migrate existing daily_cash table to new schema with payment method columns"""
    try:
        # Check if cash_opening column exists
        column_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'daily_cash' AND column_name = 'cash_opening'
        """)
        
        if not column_exists:
            print("Adding payment method columns to daily_cash table...")
            
            # Add Cash columns
            await conn.execute("""
                ALTER TABLE daily_cash
                ADD COLUMN cash_opening NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                ADD COLUMN cash_closing NUMERIC(10, 2),
                ADD COLUMN cash_sales NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                ADD COLUMN cash_notes TEXT
            """)
            print("  Added Cash columns")
            
            # Add Easypaisa Zohaib columns
            await conn.execute("""
                ALTER TABLE daily_cash
                ADD COLUMN easypaisa_zohaib_opening NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                ADD COLUMN easypaisa_zohaib_closing NUMERIC(10, 2),
                ADD COLUMN easypaisa_zohaib_sales NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                ADD COLUMN easypaisa_zohaib_notes TEXT
            """)
            print("  Added Easypaisa Zohaib columns")
            
            # Add Easypaisa Yasir columns
            await conn.execute("""
                ALTER TABLE daily_cash
                ADD COLUMN easypaisa_yasir_opening NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                ADD COLUMN easypaisa_yasir_closing NUMERIC(10, 2),
                ADD COLUMN easypaisa_yasir_sales NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                ADD COLUMN easypaisa_yasir_notes TEXT
            """)
            print("  Added Easypaisa Yasir columns")
            
            # Add Bank columns
            await conn.execute("""
                ALTER TABLE daily_cash
                ADD COLUMN bank_opening NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                ADD COLUMN bank_closing NUMERIC(10, 2),
                ADD COLUMN bank_sales NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                ADD COLUMN bank_notes TEXT
            """)
            print("  Added Bank columns")
            
            # Migrate old data if exists
            old_column_exists = await conn.fetchval("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'daily_cash' AND column_name = 'opening_amount'
            """)
            
            if old_column_exists:
                await conn.execute("""
                    UPDATE daily_cash
                    SET 
                        cash_opening = opening_amount,
                        cash_closing = closing_amount,
                        cash_sales = sales_amount
                """)
                print("  Migrated old data to new columns")
            
            print("Migration completed successfully!")
        else:
            print("Table already has payment method columns")
            
    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    asyncio.run(add_daily_cash_table())
