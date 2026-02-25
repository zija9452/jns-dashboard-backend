#!/usr/bin/env python3
"""
Script to create expense_types table
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

async def create_expense_types_table():
    """Create expense_types table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Create expense_types table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS expense_types (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(100) NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Created expense_types table")

        # Create index on expense_types
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expense_types_name ON expense_types(name);
        """)
        print("Created index on expense_types.name")

        await conn.close()
        print("Expense Types table created successfully!")

    except Exception as e:
        print(f"Error creating expense_types table: {e}")

if __name__ == "__main__":
    asyncio.run(create_expense_types_table())
