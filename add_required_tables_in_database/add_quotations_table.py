#!/usr/bin/env python3
"""
Creates the quotations table - pre-sale price offers that can later be converted
into a real Customer Order (customer_invoices row). Rush status/charge is derived
from required_by_date vs rush_pricing_settings, never a manual toggle, and is
snapshotted per-row so later changes to the global rush rule don't retroactively
change an already-sent/approved quotation's price.

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


async def add_quotations_table():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'quotations'
            );
        """)

        if not table_exists:
            await conn.execute("""
                CREATE TABLE quotations (
                    id UUID PRIMARY KEY,
                    quotation_no VARCHAR NOT NULL UNIQUE,
                    customer_id UUID REFERENCES customers(id),
                    customer_name VARCHAR,
                    team_name VARCHAR,
                    salesman_id UUID REFERENCES salesmen(id),

                    items TEXT NOT NULL,
                    totals TEXT NOT NULL,

                    total_amount NUMERIC(10, 2) NOT NULL,
                    taxes NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
                    discounts NUMERIC(10, 2) DEFAULT 0.00,

                    required_by_date DATE,
                    is_rush BOOLEAN NOT NULL DEFAULT FALSE,
                    rush_rate_snapshot NUMERIC(10, 2),
                    rush_threshold_snapshot INTEGER,
                    rush_charge NUMERIC(10, 2) NOT NULL DEFAULT 0.00,

                    valid_until DATE,
                    status VARCHAR NOT NULL DEFAULT 'DRAFT',
                    revision INTEGER NOT NULL DEFAULT 1,
                    notes TEXT,

                    converted_invoice_id UUID REFERENCES customer_invoices(id),

                    created_by UUID NOT NULL REFERENCES users(id),
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                );
            """)
            await conn.execute("CREATE INDEX ix_quotations_customer_id ON quotations(customer_id);")
            await conn.execute("CREATE INDEX ix_quotations_salesman_id ON quotations(salesman_id);")
            await conn.execute("CREATE INDEX ix_quotations_status ON quotations(status);")
            await conn.execute("CREATE INDEX ix_quotations_is_rush ON quotations(is_rush);")
            await conn.execute("CREATE INDEX ix_quotations_required_by_date ON quotations(required_by_date);")
            await conn.execute("CREATE INDEX ix_quotations_created_by ON quotations(created_by);")
            await conn.execute("CREATE INDEX ix_quotations_created_at ON quotations(created_at);")
            await conn.execute("CREATE INDEX ix_quotations_quotation_no ON quotations(quotation_no);")
            await conn.execute("CREATE INDEX ix_quotations_customer_name ON quotations(customer_name);")
            await conn.execute("CREATE INDEX ix_quotations_total_amount ON quotations(total_amount);")
            await conn.execute("CREATE INDEX ix_quotations_updated_at ON quotations(updated_at);")
            print("Created quotations table (with indexes).")
        else:
            print("quotations table already exists.")

        await conn.close()
        print("\nDone.")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(add_quotations_table())
