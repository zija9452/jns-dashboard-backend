#!/usr/bin/env python3
"""
Fix-up script: add delivered_at / cancelled_at columns to shop_orders
if the table was already auto-created before these columns existed on the model.
Safe to run multiple times (uses IF NOT EXISTS).
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

async def add_missing_columns():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        await conn.execute("""
            ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMP;
        """)
        print("Ensured shop_orders.delivered_at exists")

        await conn.execute("""
            ALTER TABLE shop_orders ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMP;
        """)
        print("Ensured shop_orders.cancelled_at exists")

        await conn.close()
        print("shop_orders columns fixed successfully!")

    except Exception as e:
        print(f"Error fixing shop_orders columns: {e}")

if __name__ == "__main__":
    asyncio.run(add_missing_columns())
