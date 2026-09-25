#!/usr/bin/env python3
"""
Adds the same rush/deadline columns that Quotation has to customer_invoices, so
orders created directly via Customer Invoice (not through a quotation) also get
required_by_date + auto is_rush/rush_charge. Rush is derived from the deadline vs
rush_pricing_settings, never a manual toggle. Rate/threshold are snapshotted at
save time so a later change to the global rush rule never retroactively changes
an already-created invoice's price.

Idempotent - safe to run multiple times.
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("NEON_DATABASE_URL", ""))

if DATABASE_URL.startswith("postgresql+asyncpg"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

COLUMNS = [
    ("required_by_date", "DATE"),
    ("is_rush", "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("rush_rate_snapshot", "NUMERIC(10, 2)"),
    ("rush_threshold_snapshot", "INTEGER"),
    ("rush_charge", "NUMERIC(10, 2) NOT NULL DEFAULT 0.00"),
]


async def add_customer_invoice_rush_deadline_columns():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        for column_name, column_def in COLUMNS:
            column_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'customer_invoices'
                    AND column_name = $1
                );
            """, column_name)

            if not column_exists:
                await conn.execute(f"""
                    ALTER TABLE customer_invoices
                    ADD COLUMN {column_name} {column_def};
                """)
                print(f"Added {column_name} column to customer_invoices.")
            else:
                print(f"{column_name} column already exists on customer_invoices.")

        await conn.execute("CREATE INDEX IF NOT EXISTS ix_customer_invoices_required_by_date ON customer_invoices(required_by_date);")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_customer_invoices_is_rush ON customer_invoices(is_rush);")

        await conn.close()
        print("Done.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(add_customer_invoice_rush_deadline_columns())
