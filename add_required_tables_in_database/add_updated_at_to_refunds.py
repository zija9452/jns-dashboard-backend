#!/usr/bin/env python3
"""
Script to add updated_at column to the refunds table
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("NEON_DATABASE_URL", ""))
if not DATABASE_URL:
    # Default fallback URL - using the one from docker-compose.yml
    DATABASE_URL = "postgresql+asyncpg://neondb_owner:npg_DSJeaHiRo69W@ep-falling-base-ahj4k5gl-pooler.c-3.us-east-1.aws.neon.tech:5432/neondb"

# Convert from sqlalchemy asyncpg format to regular postgresql format if needed
if DATABASE_URL.startswith("postgresql+asyncpg"):
    # Replace 'postgresql+asyncpg://' with 'postgresql://'
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

print(f"Using database URL: {DATABASE_URL}")

async def add_updated_at_column():
    """Add updated_at column to refunds table"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL.replace("postgresql://", "postgres://"))

        # Check if updated_at column exists
        updated_at_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'refunds' AND column_name = 'updated_at'
        """)

        if not updated_at_exists:
            # Add updated_at column with default value
            await conn.execute("ALTER TABLE refunds ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();")
            print("Added updated_at column to refunds table")
            
            # Update existing records to have updated_at same as created_at
            await conn.execute("UPDATE refunds SET updated_at = created_at WHERE updated_at IS NULL;")
            print("Updated existing refund records with updated_at values")
        else:
            print("updated_at column already exists in refunds table")

        await conn.close()
        print("Successfully updated refunds table schema!")

    except Exception as e:
        print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(add_updated_at_column())