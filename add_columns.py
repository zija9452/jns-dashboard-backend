#!/usr/bin/env python3
"""
Script to manually add new columns to the customer_invoices table
"""

import asyncio
import asyncpg
import os
from decimal import Decimal

async def add_columns():
    # Connect to PostgreSQL database
    connection = await asyncpg.connect(
        host="localhost",
        port=5432,
        user="postgres",
        password="yourpassword",  # This might be different
        database="postgres"  # Default database to establish initial connection
    )

    try:
        # Switch to the backend database (assuming it has the same name as the project)
        await connection.execute("USE regal_pos_db")  # Or whatever your database name is
    except:
        # If USE fails, try to create and connect to the specific database
        try:
            await connection.execute("CREATE DATABASE regal_pos_db")
        except:
            pass  # Database might already exist

        # Close current connection and reconnect to specific DB
        await connection.close()

        connection = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="postgres",
            password="yourpassword",
            database="regal_pos_db"
        )

    # Add the new columns if they don't exist
    columns_to_add = [
        ("total_amount", "NUMERIC(10, 2) DEFAULT 0.00"),
        ("amount_paid", "NUMERIC(10, 2) DEFAULT 0.00"),
        ("balance_due", "NUMERIC(10, 2) DEFAULT 0.00"),
        ("payment_status", "VARCHAR(20) DEFAULT 'unpaid'"),
        ("payments_history", "TEXT DEFAULT '[]'")
    ]

    for col_name, col_def in columns_to_add:
        try:
            alter_query = f"ALTER TABLE customer_invoices ADD COLUMN IF NOT EXISTS {col_name} {col_def};"
            await connection.execute(alter_query)
            print(f"Column {col_name} added successfully or already exists.")
        except Exception as e:
            print(f"Error adding column {col_name}: {str(e)}")

    await connection.close()
    print("Columns addition process completed.")

if __name__ == "__main__":
    asyncio.run(add_columns())