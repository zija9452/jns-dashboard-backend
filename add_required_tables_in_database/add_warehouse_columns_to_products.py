#!/usr/bin/env python3
"""
Script to add warehouse columns to products table:
- article_no
- warehouse_stock
- warehouse_limited_qty
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

async def add_warehouse_columns():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Check and add article_no column
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'products'
                AND column_name = 'article_no'
            );
        """)
        if not column_exists:
            await conn.execute("""
                ALTER TABLE products
                ADD COLUMN article_no VARCHAR(50);
            """)
            print("Added article_no column to products table")
        else:
            print("article_no column already exists")

        # Check and add warehouse_stock column
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
            print("warehouse_stock column already exists")

        # Check and add warehouse_limited_qty column
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'products'
                AND column_name = 'warehouse_limited_qty'
            );
        """)
        if not column_exists:
            await conn.execute("""
                ALTER TABLE products
                ADD COLUMN warehouse_limited_qty INTEGER DEFAULT 0;
            """)
            print("Added warehouse_limited_qty column to products table")
        else:
            print("warehouse_limited_qty column already exists")

        await conn.close()
        print("\nWarehouse columns added successfully!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(add_warehouse_columns())
