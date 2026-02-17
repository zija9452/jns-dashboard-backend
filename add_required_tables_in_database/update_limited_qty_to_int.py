#!/usr/bin/env python3
"""
Script to change limited_qty column from boolean to integer in products table
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

async def update_limited_qty_column():
    """Change limited_qty from boolean to integer"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Step 1: Add a new temporary column with integer type
        print("Adding temporary column limited_qty_int...")
        await conn.execute("""
            ALTER TABLE products 
            ADD COLUMN IF NOT EXISTS limited_qty_int INTEGER DEFAULT 0;
        """)

        # Step 2: Copy data from old boolean column to new integer column
        # (FALSE -> 0, TRUE -> 1)
        print("Converting boolean values to integers...")
        await conn.execute("""
            UPDATE products 
            SET limited_qty_int = CASE 
                WHEN limited_qty = TRUE THEN 1 
                ELSE 0 
            END;
        """)

        # Step 3: Drop the old boolean column
        print("Dropping old limited_qty column...")
        await conn.execute("""
            ALTER TABLE products 
            DROP COLUMN limited_qty;
        """)

        # Step 4: Rename the new column to limited_qty
        print("Renaming limited_qty_int to limited_qty...")
        await conn.execute("""
            ALTER TABLE products 
            RENAME COLUMN limited_qty_int TO limited_qty;
        """)

        # Step 5: Set default value
        print("Setting default value...")
        await conn.execute("""
            ALTER TABLE products 
            ALTER COLUMN limited_qty SET DEFAULT 0;
        """)

        await conn.close()
        print("limited_qty column successfully changed from boolean to integer!")

    except Exception as e:
        print(f"Error updating column: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(update_limited_qty_column())
