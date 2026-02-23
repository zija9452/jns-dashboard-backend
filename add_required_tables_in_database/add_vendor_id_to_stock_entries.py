#!/usr/bin/env python3
"""
Simple script to add vendor_id column to stock_entries table
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
    # Replace 'postgresql+asyncpg://' with 'postgresql://'
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

print(f"Using database URL: {DATABASE_URL}")

async def add_vendor_id_column():
    """Add vendor_id column to stock_entries table"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if vendor_id column exists
        vendor_id_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'stock_entries' AND column_name = 'vendor_id'
        """)

        if not vendor_id_exists:
            # Add vendor_id column with foreign key to vendors table
            await conn.execute("""
                ALTER TABLE stock_entries 
                ADD COLUMN vendor_id UUID DEFAULT NULL,
                ADD CONSTRAINT fk_stock_entries_vendor 
                FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL;
            """)
            print("Added vendor_id column to stock_entries table with foreign key constraint")
        else:
            print("vendor_id column already exists")

        await conn.close()
        print("Database schema updated successfully!")

    except Exception as e:
        print(f"Error updating database schema: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(add_vendor_id_column())
