#!/usr/bin/env python3
"""
Script to update invoices table for walk-in invoice enhancements
Adds: customer_id FK, salesman_id FK, payment_date, payment_method
Removes: status (uses payment_status instead), balance_due (always 0 for walk-in), taxes (always 0)
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

async def update_walkin_invoice_schema():
    """Update invoices table schema for walk-in invoice enhancements"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # 1. Add customer_id column with FK reference if it doesn't exist
        customer_id_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'customer_id'
        """)

        if not customer_id_exists:
            await conn.execute("""
                ALTER TABLE invoices 
                ADD COLUMN customer_id UUID REFERENCES customers(id) ON DELETE SET NULL
            """)
            print("Added customer_id column with FK reference to customers table")
        else:
            # Make sure it has FK constraint
            fk_exists = await conn.fetchval("""
                SELECT 1
                FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage AS ccu
                    ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_name = 'invoices' 
                    AND tc.constraint_type = 'FOREIGN KEY'
                    AND ccu.table_name = 'customers'
            """)
            if not fk_exists:
                await conn.execute("""
                    ALTER TABLE invoices 
                    ALTER COLUMN customer_id TYPE UUID USING customer_id::UUID,
                    ADD CONSTRAINT invoices_customer_id_fkey 
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
                """)
                print("Added FK constraint to customer_id column")
            else:
                print("customer_id column with FK already exists")

        # 2. Add salesman_id column with FK reference if it doesn't exist
        salesman_id_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'salesman_id'
        """)

        if not salesman_id_exists:
            # Check if salesman table exists (might be named 'salesman' not 'salesmans')
            salesman_table = await conn.fetchval("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('salesman', 'salesmans', 'salesmen')
                LIMIT 1
            """)
            
            if salesman_table:
                await conn.execute(f"""
                    ALTER TABLE invoices 
                    ADD COLUMN salesman_id UUID REFERENCES {salesman_table}(id) ON DELETE SET NULL
                """)
                print(f"Added salesman_id column with FK reference to {salesman_table} table")
            else:
                print("Salesman table does not exist, skipping salesman_id FK")
        else:
            # Make sure it has FK constraint
            salesman_table = await conn.fetchval("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('salesman', 'salesmans', 'salesmen')
                LIMIT 1
            """)
            
            if salesman_table:
                fk_exists = await conn.fetchval("""
                    SELECT 1
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON tc.constraint_name = ccu.constraint_name
                    WHERE tc.table_name = 'invoices' 
                        AND tc.constraint_type = 'FOREIGN KEY'
                        AND ccu.table_name = $1
                """, salesman_table)
                if not fk_exists:
                    await conn.execute(f"""
                        ALTER TABLE invoices 
                        ALTER COLUMN salesman_id TYPE UUID USING salesman_id::UUID,
                        ADD CONSTRAINT invoices_salesman_id_fkey 
                        FOREIGN KEY (salesman_id) REFERENCES {salesman_table}(id) ON DELETE SET NULL
                    """)
                    print(f"Added FK constraint to salesman_id column")
                else:
                    print(f"salesman_id column with FK already exists")
            else:
                print("Salesman table does not exist, skipping FK constraint")

        # 3. Add payment_date column if it doesn't exist
        payment_date_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'payment_date'
        """)

        if not payment_date_exists:
            await conn.execute("""
                ALTER TABLE invoices 
                ADD COLUMN payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """)
            print("Added payment_date column to invoices table")
        else:
            print("payment_date column already exists")

        # 4. Add payment_method column if it doesn't exist
        payment_method_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'payment_method'
        """)

        if not payment_method_exists:
            await conn.execute("""
                ALTER TABLE invoices 
                ADD COLUMN payment_method VARCHAR(50) DEFAULT 'cash'
            """)
            print("Added payment_method column to invoices table")
        else:
            print("payment_method column already exists")

        # 5. Remove status column if it exists (we use payment_status instead)
        status_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'status'
        """)

        if status_exists:
            await conn.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS status;")
            print("Removed status column (using payment_status)")
        else:
            print("status column does not exist")

        # 6. Remove balance_due column if it exists (always 0 for walk-in)
        balance_due_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'balance_due'
        """)

        if balance_due_exists:
            await conn.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS balance_due;")
            print("Removed balance_due column (always 0 for walk-in)")
        else:
            print("balance_due column does not exist")

        # 7. Remove taxes column if it exists (always 0 for walk-in)
        taxes_exists = await conn.fetchval("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'invoices' AND column_name = 'taxes'
        """)

        if taxes_exists:
            await conn.execute("ALTER TABLE invoices DROP COLUMN IF EXISTS taxes;")
            print("Removed taxes column (always 0 for walk-in)")
        else:
            print("taxes column does not exist")

        await conn.close()
        print("\n[SUCCESS] Walk-in invoice schema updated successfully!")
        print("\nChanges made:")
        print("  [ADDED] customer_id (UUID, FK to customers)")
        print("  [ADDED] salesman_id (UUID, FK to salesman)")
        print("  [ADDED] payment_date (TIMESTAMP)")
        print("  [EXISTS] payment_method already exists")
        print("  [REMOVED] status (using payment_status)")
        print("  [REMOVED] balance_due (always 0)")
        print("  [REMOVED] taxes (always 0)")

    except Exception as e:
        print(f"Error updating database schema: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(update_walkin_invoice_schema())
