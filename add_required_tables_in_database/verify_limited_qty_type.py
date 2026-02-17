#!/usr/bin/env python3
"""
Script to verify limited_qty column type
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

async def verify_column_type():
    """Check limited_qty column type"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Check column type
        result = await conn.fetchrow("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'products' AND column_name = 'limited_qty';
        """)

        print(f"Column: {result['column_name']}, Type: {result['data_type']}")

        # Try to insert a test value
        await conn.execute("""
            UPDATE products SET limited_qty = 0 LIMIT 1;
        """)
        print("Successfully updated limited_qty with integer value!")

        await conn.close()

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_column_type())
