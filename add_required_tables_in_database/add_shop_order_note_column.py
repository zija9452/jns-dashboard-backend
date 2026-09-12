#!/usr/bin/env python3
"""
Script to add note column to the shop_orders table
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

async def add_shop_order_note_column():
    """Add note column to the shop_orders table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if note column exists
        note_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'shop_orders' AND column_name = 'note'
        """)

        if note_exists:
            print("[INFO] note column already exists in shop_orders table")
        else:
            await conn.execute("ALTER TABLE shop_orders ADD COLUMN note VARCHAR(255);")
            print("[OK] Added note column to shop_orders table")

        await conn.close()
        print("\n[SUCCESS] shop_orders table schema updated successfully!")

    except Exception as e:
        print(f"[ERROR] Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(add_shop_order_note_column())
