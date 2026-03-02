import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def main():
    url = os.getenv('DATABASE_URL', os.getenv('NEON_DATABASE_URL', ''))
    if url.startswith('postgresql+asyncpg'):
        url = url.replace('postgresql+asyncpg://', 'postgresql://', 1)
    
    conn = await asyncpg.connect(url)
    cols = await conn.fetch("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'daily_cash' 
        ORDER BY ordinal_position
    """)
    
    print("daily_cash table columns:")
    for col in cols:
        print(f"  {col['column_name']}: {col['data_type']}")
    
    await conn.close()

asyncio.run(main())
