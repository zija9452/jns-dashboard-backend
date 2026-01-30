"""
Test script to verify the Neon database connection string format
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Original problematic connection string from the compose file
original_url = "postgresql+asyncpg://neondb_owner:npg_DSJeaHiRo69W@ep-falling-base-ahj4k5gl-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# Corrected connection string format for Neon
corrected_url = "postgresql+asyncpg://neondb_owner:npg_DSJeaHiRo69W@ep-falling-base-ahj4k5gl-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require"

print("Testing Neon database connection string formats...")
print(f"Original URL: {original_url}")
print(f"Corrected URL: {corrected_url}")

async def test_connection(connection_string, name):
    """Test if a connection string is valid by attempting to connect."""
    print(f"\nTesting {name}...")
    try:
        engine = create_async_engine(connection_string)

        # Attempt to connect and run a simple query
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"✅ {name}: Connection successful!")

        await engine.dispose()
        return True

    except Exception as e:
        print(f"❌ {name}: Connection failed - {e}")
        return False

async def main():
    print("Starting Neon database connection tests...\n")

    # Test corrected connection string
    success = await test_connection(corrected_url, "Corrected Neon DB URL")

    if success:
        print("\n🎉 The corrected connection string works!")
        print(f"Use this format: {corrected_url}")
    else:
        print("\n⚠️  Neither connection string worked. The issue might be with credentials or network access.")
        print("For local development, consider using a local PostgreSQL instance instead.")

if __name__ == "__main__":
    asyncio.run(main())