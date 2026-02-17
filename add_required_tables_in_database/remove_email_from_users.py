"""
Remove email column from users table

This migration removes the email field from the User model and database table
as authentication is now handled via username only.
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from src.database.database import AsyncSessionLocal, engine


async def remove_email_column():
    """Remove email column from users table"""
    async with AsyncSessionLocal() as session:
        try:
            # Check if column exists before dropping
            result = await session.execute(
                text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' AND column_name = 'email'
                """)
            )
            column_exists = result.scalar_one_or_none()
            
            if column_exists:
                # Drop the email column
                await session.execute(text("ALTER TABLE users DROP COLUMN email"))
                print("[OK] Email column dropped from users table")
                
                # Drop the email index if it exists
                await session.execute(
                    text("DROP INDEX IF EXISTS idx_user_email")
                )
                print("[OK] Email index dropped")
                
                await session.commit()
                print("[OK] Migration completed successfully")
            else:
                print("[INFO] Email column does not exist in users table")
                
        except Exception as e:
            await session.rollback()
            print(f"[ERROR] Error removing email column: {e}")
            raise


if __name__ == "__main__":
    print("Starting migration: Remove email from users table...")
    asyncio.run(remove_email_column())
    print("Migration completed!")
