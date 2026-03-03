"""
Migration script to add role_name column to users table
This allows storing the role name for easier display and lookup
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def add_role_name_column():
    """Add role_name column to users table"""
    
    # Get database connection details from environment
    database_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/regal_pos")
    
    # Convert SQLAlchemy URL to asyncpg URL
    if database_url.startswith("postgresql+asyncpg://"):
        db_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    else:
        db_url = database_url
    
    # Connect to database
    print(f"Connecting to database: {database_url}")
    conn = await asyncpg.connect(db_url)
    
    try:
        # Check if role_name column already exists
        check_column = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'role_name'
            )
        """)
        
        if not check_column:
            # Add role_name column
            await conn.execute("""
                ALTER TABLE users
                ADD COLUMN role_name VARCHAR(50) DEFAULT NULL
            """)
            print("Added role_name column to users table")
            
            # Create index for faster lookups
            await conn.execute("""
                CREATE INDEX idx_users_role_name ON users(role_name)
            """)
            print("Created index on role_name column")
        else:
            print("role_name column already exists in users table")
        
    except Exception as e:
        print(f"Error adding role_name column: {e}")
        raise
    finally:
        await conn.close()
    
    print("Migration completed successfully!")

if __name__ == "__main__":
    print("Adding role_name column to users table...")
    asyncio.run(add_role_name_column())
