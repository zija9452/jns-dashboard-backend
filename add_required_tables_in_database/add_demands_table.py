#!/usr/bin/env python3
"""
Script to create demands table
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

async def create_demands_table():
    """Create demands table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Create enum type for demand status
        await conn.execute("""
            DO $$ BEGIN
                CREATE TYPE demandstatus AS ENUM ('PENDING', 'FULFILLED', 'CANCELLED');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        print("Ensured demandstatus enum exists")

        # Create demands table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS demands (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                demand_text VARCHAR(255) NOT NULL,
                category VARCHAR(50),
                customer_name VARCHAR(100),
                customer_phone VARCHAR(20),
                status demandstatus NOT NULL DEFAULT 'PENDING',
                fulfilled_at TIMESTAMP,
                cancelled_at TIMESTAMP,
                created_by UUID NOT NULL REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Created demands table")

        # Indexes to match model field indexing
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_demands_status ON demands(status);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_demands_created_by ON demands(created_by);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_demands_created_at ON demands(created_at);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_demands_updated_at ON demands(updated_at);
        """)
        print("Created indexes on demands")

        await conn.close()
        print("demands table created successfully!")

    except Exception as e:
        print(f"Error creating demands table: {e}")

if __name__ == "__main__":
    asyncio.run(create_demands_table())
