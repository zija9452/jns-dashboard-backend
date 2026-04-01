#!/usr/bin/env python3
"""
Script to clean up old stock_in entries from vendor payment history
"""
import asyncio
import asyncpg
import json
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL", os.getenv("NEON_DATABASE_URL", ""))

# Convert from sqlalchemy asyncpg format to regular postgresql format if needed
if DATABASE_URL.startswith("postgresql+asyncpg"):
    DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)

print(f"Using database URL: {DATABASE_URL}")

async def cleanup_vendor_payment_history():
    """Remove stock_in entries from vendor payment history"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("Connected to database")

        # Get all vendors
        vendors = await conn.fetch("SELECT id, name, payments_history FROM vendors")
        print(f"Found {len(vendors)} vendors")

        updated_count = 0

        for vendor in vendors:
            payments_history = vendor["payments_history"]
            
            if not payments_history or payments_history == "[]":
                continue

            try:
                # Parse payment history
                history_list = json.loads(payments_history)
                
                # Filter out stock_in entries (keep only actual payments)
                filtered_history = [
                    payment for payment in history_list 
                    if payment.get("payment_type") in ["payment", "reverse_payment"]
                ]

                # If entries were removed, update the database
                if len(filtered_history) != len(history_list):
                    removed_count = len(history_list) - len(filtered_history)
                    print(f"Vendor '{vendor['name']}': Removed {removed_count} stock_in entries")
                    
                    # Update vendor record
                    await conn.execute(
                        "UPDATE vendors SET payments_history = $1 WHERE id = $2",
                        json.dumps(filtered_history),
                        vendor["id"]
                    )
                    updated_count += 1

            except json.JSONDecodeError:
                print(f"Vendor '{vendor['name']}': Invalid JSON in payments_history")
                continue

        await conn.close()
        print(f"\n✅ Cleanup complete! Updated {updated_count} vendors")

    except Exception as e:
        print(f"❌ Error: {e}")
        raise

if __name__ == "__main__":
    print("=" * 60)
    print("Cleaning Up Vendor Payment History")
    print("=" * 60)
    asyncio.run(cleanup_vendor_payment_history())
