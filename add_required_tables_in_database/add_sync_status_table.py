#!/usr/bin/env python3
"""
Script to create sync_status table - tracks last-run status of each
tournament data source (cricket/football) for the admin status strip.
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

async def create_sync_status_table():
    """Create sync_status table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Reuses the tournamentsource enum created by add_tournaments_table.py
        await conn.execute("""
            DO $$ BEGIN
                CREATE TYPE tournamentsource AS ENUM ('CRICAPI', 'API_FOOTBALL', 'MANUAL');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source tournamentsource NOT NULL,
                last_run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN NOT NULL DEFAULT true,
                items_synced INTEGER NOT NULL DEFAULT 0,
                error_message VARCHAR(500)
            );
        """)
        print("Created sync_status table")

        await conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_sync_status_source ON sync_status(source);
        """)
        print("Created unique index on sync_status(source)")

        await conn.close()
        print("sync_status table created successfully!")

    except Exception as e:
        print(f"Error creating sync_status table: {e}")

if __name__ == "__main__":
    asyncio.run(create_sync_status_table())
