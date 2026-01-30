#!/usr/bin/env python3
"""
Script to fix all router files that have the User import issue.
"""

import os
from pathlib import Path

# List of router files to fix
router_files = [
    "auth.py",
    "admin.py",
    "customers.py",
    "expenses.py",
    "invoices.py",
    "pos.py",
    "products.py",  # Already fixed
    "refunds.py",
    "salesman.py",
    "stock.py",  # Already fixed
    "users.py",  # Already has import at top
    "vendors.py",  # Already fixed
    "custom_orders.py"
]

base_path = Path("src/routers")

for file_name in router_files:
    file_path = base_path / file_name

    if not file_path.exists():
        print(f"File {file_path} does not exist, skipping...")
        continue

    print(f"Processing {file_path}...")

    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Check if User import is already at the top
    lines = content.split('\n')
    user_import_at_top = False
    for line in lines[:20]:  # Check first 20 lines for import
        if line.strip().startswith('from ..models.user import User'):
            user_import_at_top = True
            break

    # Check if there are any 'User =' patterns that indicate missing import
    has_user_usage = 'current_user: User =' in content or 'user: User =' in content

    if has_user_usage and not user_import_at_top:
        print(f"  Adding User import to top of {file_name}")

        # Find where to insert the import (after other imports)
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('router = APIRouter()'):
                insert_pos = i
                break

        # Insert the import before the router definition
        if insert_pos > 0:
            lines.insert(insert_pos, 'from ..models.user import User  # Import User to avoid NameError')

            # Remove any User import from the bottom if it exists
            lines = [line for line in lines if not line.strip().startswith('from ..models.user import User') or 'Import User to avoid NameError' in line]

        # Write the updated content back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"  Fixed {file_name}")
    else:
        print(f"  {file_name} looks good")

print("Done fixing router imports!")