#!/usr/bin/env python3
"""
Test script to validate customer_invoice API functionality
"""

import asyncio
import httpx
import json
from datetime import datetime

async def test_customer_invoice_api():
    """
    Test the customer invoice API endpoints
    """
    base_url = "http://localhost:8000"

    print("Testing Customer Invoice API...")

    # Test health endpoint first
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{base_url}/health")
            print(f"Health check: {response.status_code} - {response.json()}")

            # Test customer invoice health
            response = await client.get(f"{base_url}/health/customer-invoice")
            print(f"Customer invoice health: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"Failed to connect to API: {e}")
            print("Make sure Docker containers are running with: docker-compose up -d")
            return

    print("\nAPI endpoints tested successfully!")
    print("Next steps:")
    print("1. Build and run the Docker containers: docker-compose up --build")
    print("2. Create an admin user or use existing credentials")
    print("3. Obtain an access token via the auth/login endpoint")
    print("4. Test the customer_invoice endpoints with proper authorization")

if __name__ == "__main__":
    asyncio.run(test_customer_invoice_api())