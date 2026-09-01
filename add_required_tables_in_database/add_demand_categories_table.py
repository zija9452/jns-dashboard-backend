#!/usr/bin/env python3
"""
Script to create demand_categories table
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

async def create_demand_categories_table():
    """Create demand_categories table and widen demands.category to match"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Create demand_categories table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS demand_categories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Created demand_categories table")

        # Create index on demand_categories
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_demand_categories_name ON demand_categories(name);
        """)
        print("Created index on demand_categories.name")

        # Widen demands.category so it can hold the same length as demand_categories.name
        await conn.execute("""
            ALTER TABLE demands ALTER COLUMN category TYPE VARCHAR(100);
        """)
        print("Widened demands.category to VARCHAR(100)")

        await conn.close()
        print("demand_categories table created successfully!")

    except Exception as e:
        print(f"Error creating demand_categories table: {e}")

if __name__ == "__main__":
    asyncio.run(create_demand_categories_table())
