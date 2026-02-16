"""
Migration script to add original_password field to users table
WARNING: This adds a major security vulnerability by storing plain text passwords
"""

import asyncio
from sqlalchemy import Column, String, create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
import os

# Get database URL from environment or use default
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://neondb_owner:npg_DSJeaHiRo69W@ep-falling-base-ahj4k5gl-pooler.c-3.us-east-1.aws.neon.tech:5432/neondb')

async def add_original_password_field():
    """Add original_password field to users table"""
    # Create async engine
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.connect() as conn:
        # Check if the column already exists
        result = await conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'original_password'
        """))
        
        column_exists = result.fetchone()
        
        if not column_exists:
            # Add the original_password column
            await conn.execute(text("""
                ALTER TABLE users ADD COLUMN original_password VARCHAR(255) DEFAULT NULL
            """))
            
            print("Added original_password column to users table")
        else:
            print("original_password column already exists")
        
        await conn.commit()
    
    # Dispose of the engine
    await engine.dispose()

if __name__ == "__main__":
    print("Adding original_password field to users table...")
    print("WARNING: This will store plain text passwords (MAJOR SECURITY RISK!)")
    
    try:
        asyncio.run(add_original_password_field())
        print("Migration completed successfully!")
        print("\nWARNING: The original_password field stores plain text passwords.")
        print("This is a MAJOR SECURITY VULNERABILITY in production environments.")
        print("Plain text passwords should never be stored in production databases.")
    except Exception as e:
        print(f"Error during migration: {e}")