#!/usr/bin/env python3
"""
Script to add missing columns for session, company, and biometric functionality to the database
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

async def add_missing_columns():
    """Add missing columns for session, company, and biometric functionality"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Create companies table if it doesn't exist
        companies_table_exists = await conn.fetchval("""
            SELECT EXISTS (
               SELECT FROM information_schema.tables 
               WHERE table_name = 'companies'
            );
        """)
        
        if not companies_table_exists:
            await conn.execute("""
                CREATE TABLE companies (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    branch VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            print("Created companies table")
        else:
            print("Companies table already exists")

        # Create user_sessions table if it doesn't exist
        sessions_table_exists = await conn.fetchval("""
            SELECT EXISTS (
               SELECT FROM information_schema.tables 
               WHERE table_name = 'user_sessions'
            );
        """)
        
        if not sessions_table_exists:
            await conn.execute("""
                CREATE TABLE user_sessions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id),
                    session_token VARCHAR(255) UNIQUE NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    company_id UUID REFERENCES companies(id),
                    biometric_verified BOOLEAN DEFAULT FALSE
                );
            """)
            # Create indexes for performance
            await conn.execute("CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);")
            await conn.execute("CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);")
            await conn.execute("CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);")
            await conn.execute("CREATE INDEX idx_user_sessions_company ON user_sessions(company_id);")
            print("Created user_sessions table with indexes")
        else:
            print("User sessions table already exists")

        # Check if company_id column exists in users table, if not add it
        company_id_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'company_id'
        """)

        if not company_id_exists:
            await conn.execute("ALTER TABLE users ADD COLUMN company_id UUID REFERENCES companies(id) DEFAULT NULL;")
            print("Added company_id column to users table")
        else:
            print("Company_id column already exists")

        # Check if biometric_hash column exists in users table, if not add it
        biometric_hash_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'biometric_hash'
        """)

        if not biometric_hash_exists:
            await conn.execute("ALTER TABLE users ADD COLUMN biometric_hash VARCHAR(255) DEFAULT NULL;")
            print("Added biometric_hash column to users table")
        else:
            print("Biometric_hash column already exists")

        # Check if is_biometric_enabled column exists in users table, if not add it
        is_biometric_enabled_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'is_biometric_enabled'
        """)

        if not is_biometric_enabled_exists:
            await conn.execute("ALTER TABLE users ADD COLUMN is_biometric_enabled BOOLEAN DEFAULT FALSE;")
            print("Added is_biometric_enabled column to users table")
        else:
            print("Is_biometric_enabled column already exists")

        # Check if biometric_device_id column exists in users table, if not add it
        biometric_device_id_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users' AND column_name = 'biometric_device_id'
        """)

        if not biometric_device_id_exists:
            await conn.execute("ALTER TABLE users ADD COLUMN biometric_device_id VARCHAR(255) DEFAULT NULL;")
            print("Added biometric_device_id column to users table")
        else:
            print("Biometric_device_id column already exists")

        await conn.close()
        print("Database schema updated successfully with session, company, and biometric functionality!")

    except Exception as e:
        print(f"Error updating database schema: {e}")

if __name__ == "__main__":
    asyncio.run(add_missing_columns())