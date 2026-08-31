#!/usr/bin/env python3
"""
Script to create shop_orders table
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

async def create_shop_orders_table():
    """Create shop_orders table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Create enum type for shop order status
        await conn.execute("""
            DO $$ BEGIN
                CREATE TYPE shoporderstatus AS ENUM ('PENDING', 'DELIVERED', 'CANCEL');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        print("Ensured shoporderstatus enum exists")

        # Create shop_orders table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS shop_orders (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                product_id UUID NOT NULL REFERENCES products(id),
                product_name VARCHAR(100) NOT NULL,
                barcode VARCHAR(50),
                category VARCHAR(50),
                stock_at_order_time INTEGER NOT NULL DEFAULT 0,
                quantity_ordered INTEGER NOT NULL,
                status shoporderstatus NOT NULL DEFAULT 'PENDING',
                delivered_at TIMESTAMP,
                cancelled_at TIMESTAMP,
                created_by UUID NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Created shop_orders table")

        # Indexes to match model field indexing
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_shop_orders_product_id ON shop_orders(product_id);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_shop_orders_status ON shop_orders(status);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_shop_orders_created_by ON shop_orders(created_by);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_shop_orders_created_at ON shop_orders(created_at);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_shop_orders_updated_at ON shop_orders(updated_at);
        """)
        print("Created indexes on shop_orders")

        await conn.close()
        print("shop_orders table created successfully!")

    except Exception as e:
        print(f"Error creating shop_orders table: {e}")

if __name__ == "__main__":
    asyncio.run(create_shop_orders_table())
