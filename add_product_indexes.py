"""
Add indexes to products table for better query performance
Run this script to optimize product search queries
"""
import asyncio
import os
from dotenv import load_dotenv
import asyncpg

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Convert asyncpg URL format if needed
if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


async def add_product_indexes():
    """Add performance indexes to products table"""
    try:
        print("Connecting to database...")
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Enable pg_trgm extension for trigram indexes (if not exists)
        print("Enabling pg_trgm extension...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        
        print("Creating indexes on products table...")
        
        indexes = [
            # Index for name search (used in view-product endpoint)
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_name_search 
            ON products USING gin (name gin_trgm_ops)
            """,
            
            # Index for barcode search
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_barcode 
            ON products (barcode)
            """,
            
            # Index for SKU search
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_sku 
            ON products (sku)
            """,
            
            # Index for branch filtering
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_branch 
            ON products (branch)
            """,
            
            # Composite index for common query pattern (branch + name)
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_product_branch_name 
            ON products (branch, name)
            """,
        ]
        
        for idx, query in enumerate(indexes, 1):
            try:
                print(f"Creating index {idx}/{len(indexes)}...")
                await conn.execute(query)
                print(f"[OK] Index {idx} created successfully")
            except Exception as e:
                print(f"[WARN] Index {idx} skipped or already exists: {e}")
        
        print("\n[OK] All indexes created successfully!")
        print("\nNote: CONCURRENTLY option allows index creation without locking tables")
        print("This may take a few minutes depending on data size")
        
        await conn.close()
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        raise


if __name__ == "__main__":
    print("=" * 60)
    print("Adding Performance Indexes to Products Table")
    print("=" * 60)
    asyncio.run(add_product_indexes())
