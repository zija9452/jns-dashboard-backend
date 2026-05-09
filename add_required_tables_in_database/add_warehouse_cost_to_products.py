#!/usr/bin/env python3
"""
Script to add warehouse_cost column to products table.
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

async def add_warehouse_cost_column():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Check and add warehouse_cost column
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'products'
                AND column_name = 'warehouse_cost'
            );
        """)
        if not column_exists:
            await conn.execute("""
                ALTER TABLE products
                ADD COLUMN warehouse_cost NUMERIC(10, 2) DEFAULT 0.00;
            """)
            print("Added warehouse_cost column to products table")
        else:
            print("warehouse_cost column already exists")

        await conn.close()
        print("\nWarehouse cost column added successfully!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(add_warehouse_cost_column())
