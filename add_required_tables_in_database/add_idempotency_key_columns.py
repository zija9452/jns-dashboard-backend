#!/usr/bin/env python3
"""
Script to add the idempotency_key column to invoices and customer_invoices tables.
Prevents duplicate invoice creation when a client retries a create request
(e.g. after losing internet mid-request, or refreshing the page) by letting the
backend recognize a repeat of the same client-generated key and return the
existing invoice instead of creating a new one.
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
    """Add idempotency_key column (+ unique index) to invoices and customer_invoices tables"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        for table in ("invoices", "customer_invoices"):
            column_exists = await conn.fetchval("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = $1 AND column_name = 'idempotency_key'
            """, table)

            if not column_exists:
                await conn.execute(f"ALTER TABLE {table} ADD COLUMN idempotency_key VARCHAR(64) DEFAULT NULL;")
                print(f"Added idempotency_key column to {table} table")
            else:
                print(f"idempotency_key column already exists on {table}")

            index_name = f"ix_{table}_idempotency_key"
            index_exists = await conn.fetchval("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = $1 AND indexname = $2
            """, table, index_name)

            if not index_exists:
                await conn.execute(
                    f"CREATE UNIQUE INDEX {index_name} ON {table} (idempotency_key) WHERE idempotency_key IS NOT NULL;"
                )
                print(f"Added unique index {index_name} on {table}.idempotency_key")
            else:
                print(f"Index {index_name} already exists on {table}")

        await conn.close()
        print("idempotency_key column added successfully to invoices and customer_invoices!")

    except Exception as e:
        print(f"Error updating database schema: {e}")


if __name__ == "__main__":
    asyncio.run(add_missing_columns())
