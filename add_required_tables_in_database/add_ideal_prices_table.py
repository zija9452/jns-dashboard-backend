#!/usr/bin/env python3
"""
Script to create ideal_prices table
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

async def create_ideal_prices_table():
    """Create ideal_prices table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Create ideal_prices table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS ideal_prices (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                category_id UUID NOT NULL,
                options_combination VARCHAR(500) NOT NULL,
                price NUMERIC(10, 2) NOT NULL,
                branch VARCHAR(100) DEFAULT 'European Sports Light House',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Created ideal_prices table")

        # Create indexes
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ideal_prices_category_id 
            ON ideal_prices(category_id);
        """)
        print("Created index on ideal_prices.category_id")

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ideal_prices_options_combination 
            ON ideal_prices(options_combination);
        """)
        print("Created index on ideal_prices.options_combination")

        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ideal_prices_lookup 
            ON ideal_prices(category_id, options_combination);
        """)
        print("Created composite index on ideal_prices(category_id, options_combination)")

        await conn.close()
        print("\nIdeal Prices table created successfully!")
        print("\nTable Structure:")
        print("  - id: UUID (primary key)")
        print("  - category_id: UUID (FK to customer_categories)")
        print("  - options_combination: e.g., 'Round Neck|Half|Polyzone 130gsm'")
        print("  - price: NUMERIC(10, 2)")
        print("  - branch: VARCHAR(100)")
        print("  - created_at: TIMESTAMP")
        print("  - updated_at: TIMESTAMP")

    except Exception as e:
        print(f"Error creating ideal_prices table: {e}")

if __name__ == "__main__":
    asyncio.run(create_ideal_prices_table())
