#!/usr/bin/env python3
"""
Payment proofs (screenshots of online payments - Easypaisa / bank):
- payment_proofs: one row per online payment of an invoice, status
  MISSING / PENDING / APPROVED / REJECTED (plain VARCHAR, not an enum).
- payment_proof_images: screenshots of a proof (max 3).

Runs on every branch database (schemas must stay identical). Idempotent - safe to run
multiple times. The backend's create_all may already have made the tables on the
default DB. invoice_id has no FK (customized or walk-in invoice).
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DB_ENVS = ["DATABASE_URL", "DATABASE_URL_KARIMABAD"]

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS payment_proofs (
        id UUID PRIMARY KEY,
        source VARCHAR(20) NOT NULL DEFAULT 'CUSTOMIZED',
        invoice_id UUID NOT NULL,
        invoice_no VARCHAR(50) NOT NULL,
        customer_name VARCHAR(255) NULL,
        payment_id VARCHAR(36) NOT NULL,
        amount NUMERIC(12, 2) NOT NULL,
        payment_method VARCHAR(50) NOT NULL,
        payment_date TIMESTAMP NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'MISSING',
        recorded_by UUID NOT NULL REFERENCES users(id),
        recorded_at TIMESTAMP NOT NULL,
        uploaded_by UUID NULL REFERENCES users(id),
        uploaded_at TIMESTAMP NULL,
        reviewed_by UUID NULL REFERENCES users(id),
        reviewed_at TIMESTAMP NULL,
        reject_reason VARCHAR(500) NULL,
        branch VARCHAR(100) NOT NULL
    );
    """,
    # 2026-10-09: invoice_id is a customized invoice (customer_invoices) or a walk-in
    # bill (invoices), so it has no FK; the delete endpoints remove the proofs themselves.
    "ALTER TABLE payment_proofs DROP CONSTRAINT IF EXISTS fk_payment_proofs_customer_invoice;",
    # rejection_seen_at was added then dropped on 2026-10-09 (rejected now stays until resubmitted)
    "ALTER TABLE payment_proofs DROP COLUMN IF EXISTS rejection_seen_at;",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_payment_proofs_invoice_payment ON payment_proofs (invoice_id, payment_id);",
    "CREATE INDEX IF NOT EXISTS ix_payment_proofs_source ON payment_proofs (source);",
    "CREATE INDEX IF NOT EXISTS ix_payment_proofs_invoice_id ON payment_proofs (invoice_id);",
    "CREATE INDEX IF NOT EXISTS ix_payment_proofs_invoice_no ON payment_proofs (invoice_no);",
    "CREATE INDEX IF NOT EXISTS ix_payment_proofs_status ON payment_proofs (status);",
    "CREATE INDEX IF NOT EXISTS ix_payment_proofs_recorded_at ON payment_proofs (recorded_at);",
    "CREATE INDEX IF NOT EXISTS ix_payment_proofs_branch ON payment_proofs (branch);",
    """
    CREATE TABLE IF NOT EXISTS payment_proof_images (
        id UUID PRIMARY KEY,
        proof_id UUID NOT NULL REFERENCES payment_proofs(id) ON DELETE CASCADE,
        file_url VARCHAR(500) NOT NULL,
        public_id VARCHAR(255) NULL
    );
    """,
    "CREATE INDEX IF NOT EXISTS ix_payment_proof_images_proof_id ON payment_proof_images (proof_id);",
]


async def migrate(env: str, url: str):
    if url.startswith("postgresql+asyncpg"):
        url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(url)
    try:
        async with conn.transaction():
            for sql in STATEMENTS:
                await conn.execute(sql)
        print(f"[{env}] payment_proofs + payment_proof_images ready")
    finally:
        await conn.close()


async def main():
    for env in DB_ENVS:
        url = os.getenv(env)
        if not url:
            print(f"[{env}] not set - skipped")
            continue
        try:
            await migrate(env, url)
        except Exception as e:
            print(f"[{env}] Error: {e}")
            import traceback
            traceback.print_exc()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
