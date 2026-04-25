#!/usr/bin/env python3
"""
Script to create customer_categories table with JSONB support
Structure: One row per main category with JSONB array of sub-categories
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

async def create_tables():
    """Create customer_categories table with JSONB column"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Drop existing table if exists (for clean migration)
        await conn.execute("DROP TABLE IF EXISTS customer_categories CASCADE;")
        print("Dropped existing customer_categories table")

        # Create customer_categories table with JSONB
        await conn.execute("""
            CREATE TABLE customer_categories (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                main_category VARCHAR(100) NOT NULL UNIQUE,
                sub_categories JSONB NOT NULL DEFAULT '[]'::jsonb,
                branch VARCHAR(100) DEFAULT 'European Sports Light House',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        print("Created customer_categories table with JSONB column")

        # Create indexes
        await conn.execute("""
            CREATE INDEX idx_customer_categories_main ON customer_categories(main_category);
        """)
        print("Created index on customer_categories.main_category")

        await conn.execute("""
            CREATE INDEX idx_customer_categories_branch ON customer_categories(branch);
        """)
        print("Created index on customer_categories.branch")

        # Create GIN index for JSONB queries
        await conn.execute("""
            CREATE INDEX idx_customer_categories_sub_categories 
            ON customer_categories USING GIN (sub_categories);
        """)
        print("Created GIN index on customer_categories.sub_categories")

        await conn.close()
        
        print("\n[SUCCESS] Customer Categories table created successfully!")
        print("\nTable Structure:")
        print("  - id: UUID (primary key)")
        print("  - main_category: Main category name (unique)")
        print("  - sub_categories: JSONB array of sub-categories with options")
        print("  - branch: Branch name")
        print("  - created_at: Timestamp")
        print("\nExample sub_categories JSONB:")
        print('''
        [
          {
            "sub_category": "Neck",
            "options": ["Round", "V-Neck", "Sherwani", "Polo"]
          },
          {
            "sub_category": "Fabric",
            "options": ["Polyzone", "Mesh", "Other"]
          }
        ]
        ''')

    except Exception as e:
        print(f"[ERROR] Error creating tables: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(create_tables())
