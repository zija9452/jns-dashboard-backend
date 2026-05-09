#!/usr/bin/env python3
"""
Script to add cost_price and warehouse_vendor_id columns to stock_entries table
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

async def add_columns_to_stock_entries():
    """Add cost_price and warehouse_vendor_id columns to stock_entries table"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # 1. Check if cost_price column exists
        cost_price_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'stock_entries' AND column_name = 'cost_price'
            );
        """)

        if not cost_price_exists:
            await conn.execute("""
                ALTER TABLE stock_entries 
                ADD COLUMN cost_price NUMERIC(10, 2) DEFAULT NULL;
            """)
            print("Added cost_price column to stock_entries table")
        else:
            print("cost_price column already exists")

        # 2. Check if warehouse_vendor_id column exists
        warehouse_vendor_id_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'stock_entries' AND column_name = 'warehouse_vendor_id'
            );
        """)

        if not warehouse_vendor_id_exists:
            # Add warehouse_vendor_id column with foreign key to warehouse_vendors table
            await conn.execute("""
                ALTER TABLE stock_entries 
                ADD COLUMN warehouse_vendor_id UUID DEFAULT NULL,
                ADD CONSTRAINT fk_stock_entries_warehouse_vendor 
                FOREIGN KEY (warehouse_vendor_id) REFERENCES warehouse_vendors(id) ON DELETE SET NULL;
            """)
            print("Added warehouse_vendor_id column to stock_entries table with foreign key constraint")
        else:
            print("warehouse_vendor_id column already exists")

        await conn.close()
        print("Database schema updated successfully!")

    except Exception as e:
        print(f"Error updating database schema: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(add_columns_to_stock_entries())
