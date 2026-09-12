#!/usr/bin/env python3
"""
Script to add IN_PRODUCTION status to shoporderstatus enum
and the matching in_production_at column on shop_orders.
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

async def add_in_production_status():
    """Add IN_PRODUCTION value to shoporderstatus enum and in_production_at column"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # ALTER TYPE ... ADD VALUE cannot run inside a transaction block,
        # so this must execute as its own statement (asyncpg runs it standalone).
        await conn.execute("""
            ALTER TYPE shoporderstatus ADD VALUE IF NOT EXISTS 'IN_PRODUCTION';
        """)
        print("[OK] Ensured IN_PRODUCTION value exists on shoporderstatus enum")

        in_production_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'shop_orders' AND column_name = 'in_production_at'
        """)

        if in_production_exists:
            print("[INFO] in_production_at column already exists in shop_orders table")
        else:
            await conn.execute("ALTER TABLE shop_orders ADD COLUMN in_production_at TIMESTAMP;")
            print("[OK] Added in_production_at column to shop_orders table")

        await conn.close()
        print("\n[SUCCESS] shop_orders IN_PRODUCTION status added successfully!")

    except Exception as e:
        print(f"[ERROR] Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(add_in_production_status())
