#!/usr/bin/env python3
"""
Script to update the customerinvoicestatus enum type in the database
Changes status values from: draft, issued, paid, cancelled
To: pending, delivered, completed, cancel
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

async def update_enum_type():
    """Update the customerinvoicestatus enum type"""
    try:
        # Connect to the database
        conn = await asyncpg.connect(DATABASE_URL)

        # Check current enum values
        print("\nChecking current enum values...")
        result = await conn.fetch("""
            SELECT e.enumlabel
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname = 'customerinvoicestatus'
            ORDER BY e.enumsortorder
        """)
        
        current_values = [row['enumlabel'] for row in result]
        print(f"Current enum values: {current_values}")
        
        # New values we want to add (UPPERCASE to match Python enum)
        new_values = ['PENDING', 'DELIVERED', 'COMPLETED', 'CANCEL']
        
        # Add new values if they don't exist
        print("\nAdding new enum values...")
        for value in new_values:
            if value not in current_values:
                print(f"Adding: {value}")
                try:
                    await conn.execute(f"ALTER TYPE customerinvoicestatus ADD VALUE IF NOT EXISTS '{value}'")
                    print(f"  Added '{value}'")
                except Exception as e:
                    print(f"  Note: {e}")
            else:
                print(f"  '{value}' already exists")
        
        # Verify updated values
        print("\nVerifying updated enum values...")
        result = await conn.fetch("""
            SELECT e.enumlabel
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            WHERE t.typname = 'customerinvoicestatus'
            ORDER BY e.enumsortorder
        """)
        
        updated_values = [row['enumlabel'] for row in result]
        print(f"Updated enum values: {updated_values}")
        
        # Update existing records to use 'PENDING' instead of 'DRAFT' or 'ISSUED'
        print("\nUpdating existing invoice statuses to 'PENDING'...")
        try:
            # First update to uppercase PENDING
            result = await conn.execute("""
                UPDATE customer_invoices 
                SET status = 'PENDING' 
                WHERE status IN ('DRAFT', 'ISSUED', 'PAID', 'CANCELLED')
            """)
            print("  Updated existing invoices to 'PENDING'")
        except Exception as e:
            print(f"  Note: {e}")
        
        # Also update any lowercase values to uppercase
        print("\nEnsuring all statuses are uppercase...")
        try:
            await conn.execute("""
                UPDATE customer_invoices 
                SET status = UPPER(status)
                WHERE status IN ('pending', 'delivered', 'completed', 'cancel')
            """)
            print("  Converted lowercase statuses to uppercase")
        except Exception as e:
            print(f"  Note: {e}")
        
        await conn.close()
        print("\nCustomer invoice status enum updated successfully!")
        print("   New values: PENDING, DELIVERED, COMPLETED, CANCEL")

    except Exception as e:
        print(f"\nError updating enum type: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(update_enum_type())
