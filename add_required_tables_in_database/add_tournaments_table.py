#!/usr/bin/env python3
"""
Script to create tournaments table
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

async def create_tournaments_table():
    """Create tournaments table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Create enum types
        await conn.execute("""
            DO $$ BEGIN
                CREATE TYPE tournamentsport AS ENUM ('CRICKET', 'FOOTBALL', 'TENNIS');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        print("Ensured tournamentsport enum exists")

        await conn.execute("""
            DO $$ BEGIN
                CREATE TYPE tournamentsource AS ENUM ('CRICAPI', 'API_FOOTBALL', 'MANUAL');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        print("Ensured tournamentsource enum exists")

        # Create tournaments table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tournaments (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name VARCHAR(150) NOT NULL,
                sport tournamentsport NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE,
                source tournamentsource NOT NULL DEFAULT 'MANUAL',
                external_id VARCHAR(100),
                is_active BOOLEAN NOT NULL DEFAULT true,
                created_by UUID REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Created tournaments table")

        # Indexes to match model field indexing
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tournaments_sport ON tournaments(sport);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tournaments_start_date ON tournaments(start_date);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tournaments_external_id ON tournaments(external_id);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_tournaments_created_at ON tournaments(created_at);
        """)
        # Dedup guard so the daily sync can upsert by (source, external_id) without
        # creating duplicate rows every run; manual entries have external_id = NULL
        # and are intentionally excluded (NULLs never conflict in a partial unique index).
        await conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_tournaments_source_external_id
            ON tournaments(source, external_id) WHERE external_id IS NOT NULL;
        """)
        print("Created indexes on tournaments")

        await conn.close()
        print("tournaments table created successfully!")

    except Exception as e:
        print(f"Error creating tournaments table: {e}")

if __name__ == "__main__":
    asyncio.run(create_tournaments_table())
