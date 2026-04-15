#!/usr/bin/env python3
"""
Script to add warehouse functionality:
1. Create warehouse_products table
2. Add is_warehouse_product column to products table
3. Add warehouse role to roles table
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

async def add_warehouse_functionality():
    """Add warehouse table, column, and role"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # 1. Create warehouse_products table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS warehouse_products (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) NOT NULL,
                unit_price NUMERIC(10, 2) NOT NULL,
                cost_price NUMERIC(10, 2) NOT NULL,
                stock_level INTEGER DEFAULT 0,
                category VARCHAR(50),
                branch VARCHAR(50),
                article_no VARCHAR(50),
                limited_qty INTEGER DEFAULT 0,
                brand_action VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Created warehouse_products table")

        # Create index on warehouse_products
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_warehouse_products_name ON warehouse_products(name);
        """)
        print("Created index on warehouse_products.name")

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_warehouse_products_article_no ON warehouse_products(article_no);
        """)
        print("Created index on warehouse_products.article_no")

        # 2. Add is_warehouse_product column to products table (if not exists)
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'products'
                AND column_name = 'is_warehouse_product'
            );
        """)

        if not column_exists:
            await conn.execute("""
                ALTER TABLE products
                ADD COLUMN is_warehouse_product BOOLEAN DEFAULT FALSE;
            """)
            print("Added is_warehouse_product column to products table")
        else:
            print("is_warehouse_product column already exists in products table")

        # 3. Add warehouse role to roles table (if not exists)
        role_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1
                FROM roles
                WHERE name = 'warehouse'
            );
        """)

        if not role_exists:
            await conn.execute("""
                INSERT INTO roles (id, name, permissions, created_at)
                VALUES (gen_random_uuid(), 'warehouse', '{}', CURRENT_TIMESTAMP);
            """)
            print("Added warehouse role to roles table")
        else:
            print("Warehouse role already exists in roles table")

        await conn.close()
        print("\nWarehouse functionality added successfully!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(add_warehouse_functionality())
