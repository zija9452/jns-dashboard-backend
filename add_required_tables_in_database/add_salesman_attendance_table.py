#!/usr/bin/env python3
"""
Script to create salesman_attendance table for daily salesman in/out timing
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

async def create_salesman_attendance_table():
    """Create salesman_attendance table"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        # Create salesman_attendance table
        # One row per salesman per day - the unique constraint is the consistency
        # guard against duplicate/overlapping check-ins for the same salesman.
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS salesman_attendance (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                salesman_id UUID NOT NULL REFERENCES salesmen(id) ON DELETE CASCADE,
                attendance_date DATE NOT NULL,
                check_in_time TIMESTAMP NOT NULL,
                check_out_time TIMESTAMP,
                checked_in_by UUID NOT NULL REFERENCES users(id),
                checked_out_by UUID REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT uq_salesman_attendance_salesman_date UNIQUE (salesman_id, attendance_date)
            );
        """)
        print("Created salesman_attendance table")

        # Indexes to match model field indexing
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_salesman_attendance_salesman_id ON salesman_attendance(salesman_id);
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_salesman_attendance_date ON salesman_attendance(attendance_date);
        """)
        print("Created indexes on salesman_attendance")

        await conn.close()
        print("salesman_attendance table created successfully!")

    except Exception as e:
        print(f"Error creating salesman_attendance table: {e}")

if __name__ == "__main__":
    asyncio.run(create_salesman_attendance_table())
