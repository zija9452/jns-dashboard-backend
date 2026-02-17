#!/usr/bin/env python3
"""
Script to create categories and brands tables
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

async def create_tables():
    """Create categories and brands tables"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Create categories table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) NOT NULL UNIQUE,
                branch VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Created categories table")

        # Create index on categories
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name);
        """)
        print("Created index on categories.name")

        # Create brands table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS brands (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Created brands table")

        # Create index on brands
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_brands_name ON brands(name);
        """)
        print("Created index on brands.name")

        await conn.close()
        print("Categories and Brands tables created successfully!")

    except Exception as e:
        print(f"Error creating tables: {e}")

if __name__ == "__main__":
    asyncio.run(create_tables())
