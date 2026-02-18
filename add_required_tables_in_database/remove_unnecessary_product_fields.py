"""
Remove unnecessary columns from products table

This migration removes the desc, tax_rate, and limited_qty fields from the Product model
and database table to reduce data transfer and improve API performance.
"""
import asyncio
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from src.database.database import AsyncSessionLocal, engine


async def remove_unnecessary_product_columns():
    """Remove unnecessary columns from products table"""
    async with AsyncSessionLocal() as session:
        try:
            # Check if columns exist before dropping
            columns_to_check = ['desc', 'tax_rate', 'vendor_id', 'limited_qty_int']  # Added vendor_id, keeping limited_qty but removing duplicate limited_qty_int
            columns_exist = {}

            for col in columns_to_check:
                result = await session.execute(
                    text(f"""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = 'products' AND column_name = '{col}'
                    """)
                )
                columns_exist[col] = result.scalar_one_or_none() is not None

            for col, exists in columns_exist.items():
                if exists:
                    # Drop the column - use quotes around column name in case it's a reserved keyword
                    await session.execute(text(f'ALTER TABLE products DROP COLUMN "{col}"'))
                    print(f"[OK] {col} column dropped from products table")
                else:
                    print(f"[INFO] {col} column does not exist in products table")

            await session.commit()
            print("[OK] Migration completed successfully")

        except Exception as e:
            await session.rollback()
            print(f"[ERROR] Error removing columns: {e}")
            raise


if __name__ == "__main__":
    print("Starting migration: Remove unnecessary columns from products table...")
    asyncio.run(remove_unnecessary_product_columns())
    print("Migration completed!")