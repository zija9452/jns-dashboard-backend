#!/usr/bin/env python3
"""
Script to add invoice_no column to refunds table
This improves performance by storing invoice number directly instead of joining with invoices table
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
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

print(f"Using database URL: {DATABASE_URL}")

async def add_invoice_no_to_refunds():
    """Add invoice_no column to refunds table and populate existing records"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # 1. Add invoice_no column if it doesn't exist
        invoice_no_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'refunds' AND column_name = 'invoice_no'
        """)

        if not invoice_no_exists:
            await conn.execute("""
                ALTER TABLE refunds
                ADD COLUMN invoice_no VARCHAR(50)
            """)
            print("Added invoice_no column to refunds table")
        else:
            print("invoice_no column already exists")

        # 2. Populate invoice_no for existing refunds by joining with invoices table
        print("Populating invoice_no for existing refunds...")
        
        # Get all refunds with their invoice_ids
        refunds = await conn.fetch("""
            SELECT id, invoice_id, invoice_no
            FROM refunds
            WHERE invoice_no IS NULL
        """)
        
        updated_count = 0
        for refund in refunds:
            refund_id = refund['id']
            invoice_id = refund['invoice_id']
            
            # Get invoice number from invoices table
            invoice = await conn.fetchrow("""
                SELECT invoice_no
                FROM invoices
                WHERE id = $1
            """, invoice_id)
            
            if invoice:
                await conn.execute("""
                    UPDATE refunds
                    SET invoice_no = $1
                    WHERE id = $2
                """, invoice['invoice_no'], refund_id)
                updated_count += 1
        
        print(f"Updated {updated_count} refund records with invoice_no")

        # 3. Create index on invoice_no for faster lookups
        index_exists = await conn.fetchval("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'refunds' AND indexname = 'idx_refunds_invoice_no'
        """)

        if not index_exists:
            await conn.execute("""
                CREATE INDEX idx_refunds_invoice_no ON refunds(invoice_no)
            """)
            print("Created index on invoice_no column")
        else:
            print("Index on invoice_no already exists")

        await conn.close()
        print("\n[SUCCESS] Refunds table updated successfully!")
        print("\nChanges made:")
        print("  [ADDED] invoice_no column (VARCHAR(50))")
        print("  [POPULATED] Existing refund records with invoice numbers")
        print("  [INDEXED] invoice_no column for faster queries")

    except Exception as e:
        print(f"Error updating database schema: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(add_invoice_no_to_refunds())
