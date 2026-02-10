#!/usr/bin/env python3
"""
Script to fix the user_sessions table by removing the problematic foreign key constraint
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("NEON_DATABASE_URL", ""))
if not DATABASE_URL:
    # Default fallback URL
    DATABASE_URL = "postgresql://neondb_owner:npg_DSJeaHiRo69W@ep-falling-base-ahj4k5gl-pooler.c-3.us-east-1.aws.neon.tech:5432/neondb"

# Convert from sqlalchemy asyncpg format to regular postgresql format if needed
if DATABASE_URL.startswith("postgresql+asyncpg"):
    # Replace 'postgresql+asyncpg://' with 'postgresql://'
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

print(f"Using database URL: {DATABASE_URL}")

async def fix_user_sessions_table():
    """Fix the user_sessions table by removing the problematic foreign key constraint"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Check if the foreign key constraint exists
        fk_query = """
            SELECT con.conname AS constraint_name
            FROM pg_constraint con
            JOIN pg_class tbl ON tbl.oid = con.conrelid
            JOIN pg_class ref_tbl ON ref_tbl.oid = con.confrelid
            WHERE tbl.relname = 'user_sessions'
              AND ref_tbl.relname = 'companies'
              AND con.contype = 'f';
        """
        
        constraint_rows = await conn.fetch(fk_query)
        
        if constraint_rows:
            constraint_name = constraint_rows[0]['constraint_name']
            print(f"Found foreign key constraint: {constraint_name}")
            
            # Drop the foreign key constraint
            drop_fk_sql = f"ALTER TABLE user_sessions DROP CONSTRAINT IF EXISTS {constraint_name};"
            await conn.execute(drop_fk_sql)
            print(f"Dropped foreign key constraint: {constraint_name}")
        else:
            print("No foreign key constraint found between user_sessions and companies")

        await conn.close()
        print("Database schema updated successfully!")

    except Exception as e:
        print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(fix_user_sessions_table())