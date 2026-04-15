#!/usr/bin/env python3
"""
Script to remove warehouse_products table and add warehouse_stock column to products table
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

async def update_schema():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # 1. Drop warehouse_products table
        await conn.execute("DROP TABLE IF EXISTS warehouse_products CASCADE;")
        print("Dropped warehouse_products table")

        # 2. Add warehouse_stock column to products table (if not exists)
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'products'
                AND column_name = 'warehouse_stock'
            );
        """)

        if not column_exists:
            await conn.execute("""
                ALTER TABLE products
                ADD COLUMN warehouse_stock INTEGER DEFAULT 0;
            """)
            print("Added warehouse_stock column to products table")
        else:
            print("warehouse_stock column already exists in products table")

        await conn.close()
        print("\nSchema updated successfully!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(update_schema())
