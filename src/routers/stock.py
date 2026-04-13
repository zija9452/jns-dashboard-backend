from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
import uuid
from datetime import datetime
import base64
import os
from pydantic import BaseModel


class StockAdjustItem(BaseModel):
    """Pydantic model for stock adjustment item"""
    product_id: str
    quantity: int
    action: str  # 'increase' or 'decrease'
    reason: Optional[str] = 'Stock count adjustment'

from ..database.database import get_db
from ..models.user import User
from ..models.product import Product
from ..models.vendor import Vendor
from ..models.stock_entry import StockEntry, StockEntryType, StockEntryCreate, StockEntryUpdate, StockEntryRead
from ..services.stock_service import StockService
from ..auth.session_auth import get_current_user_from_session, admin_required_from_session, cashier_required_from_session, employee_required_from_session, admin_cashier_employee_required_from_session

router = APIRouter()

# ============================================================================
# Frontend-Compatible Stock Management Endpoints (Matching Product Page Pattern)
# ============================================================================

@router.get("/viewstock")
async def view_stock(
    search_string: Optional[str] = None,
    branches: Optional[str] = None,
    shelf: Optional[str] = None,
    page: int = 1,
    limit: int = 8,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    View stock with search and branch filtering
    Matches product page pattern with all required fields
    Access: Admin, Cashier, Employee
    Returns: Paginated data + total count for proper frontend pagination
    """
    # Calculate skip from page
    skip = (page - 1) * limit

    # Build base query - ONLY show products with stock > 0
    base_statement = select(
        Product.id,
        Product.name,
        Product.unit_price,
        Product.cost_price,
        Product.barcode,
        Product.category,
        Product.stock_level,
        Product.branch,
        Product.brand_action
    ).where(Product.stock_level > 0)  # Only products with stock

    # Apply branch filter at database level
    if branches:
        base_statement = base_statement.where(Product.branch == branches)

    # Apply search filter at database level (case-insensitive)
    if search_string and search_string.strip():
        search_pattern = f"%{search_string.strip()}%"
        base_statement = base_statement.where(
            or_(
                Product.name.ilike(search_pattern),
                Product.barcode.ilike(search_pattern),
                Product.sku.ilike(search_pattern)
            )
        )

    # Get total count - only products with stock
    count_statement = select(Product.id).where(Product.stock_level > 0)
    if branches:
        count_statement = count_statement.where(Product.branch == branches)
    if search_string and search_string.strip():
        search_pattern = f"%{search_string.strip()}%"
        count_statement = count_statement.where(
            or_(
                Product.name.ilike(search_pattern),
                Product.barcode.ilike(search_pattern),
                Product.sku.ilike(search_pattern)
            )
        )

    count_result = await db.execute(count_statement)
    total_count = len(count_result.scalars().all())

    # Apply pagination at database level
    statement = base_statement.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(statement)
    products = result.fetchall()

    # Format response with vendor names from latest stock entry
    result_list = []
    for p in products:
        product_id = p[0]
        
        # Get latest vendor from stock entries
        vendor_name = ""
        latest_entry_query = select(StockEntry.vendor_id).where(
            StockEntry.product_id == product_id
        ).order_by(StockEntry.created_at.desc()).limit(1)
        
        latest_entry_result = await db.execute(latest_entry_query)
        latest_vendor_id = latest_entry_result.scalar_one_or_none()
        
        if latest_vendor_id:
            vendor = await db.get(Vendor, latest_vendor_id)
            if vendor:
                vendor_name = vendor.name
        
        result_list.append({
            "pro_id": str(product_id),
            "vendor_name": vendor_name,
            "product_name": p[1],
            "category": p[5] or "",
            "stock": p[6],
            "price": float(p[2]) if p[2] else 0.0,
            "cost": float(p[3]) if p[3] else 0.0,
            "barcode": p[4] or "",
            "margin": round(((float(p[2]) - float(p[3])) / float(p[3]) * 100) if p[3] else 0.0, 2),
            "brand": p[8] or "",
            "branch": p[7] or ""
        })

    # Calculate total pages
    total_pages = (total_count + limit - 1) // limit  # Ceiling division

    # Prepare response with pagination info
    response_data = {
        'data': result_list,
        'page': page,
        'limit': limit,
        'total': total_count,
        'total_pages': total_pages,
        'has_more': page < total_pages
    }

    return response_data


@router.get("/searchstock")
async def search_stock(
    branches: Optional[str] = None,
    search_string: Optional[str] = None,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Search stock by branch
    Access: Admin, Cashier, Employee
    """
    # Build query
    statement = select(Product)

    # Apply filters
    if branches:
        statement = statement.where(Product.branch == branches)
    if search_string:
        statement = statement.where(Product.name.ilike(f"%{search_string}%"))

    # Execute query
    result = await db.execute(statement)
    products = result.scalars().all()

    # Format the response
    response = []
    for product in products:
        response.append({
            "stock_id": str(product.id),
            "product_name": product.name,
            "stock": product.stock_level,
            "branch": product.branch or ""
        })

    return response


@router.post("/adjuststock")
async def adjust_stock(
    stock_items: List[StockAdjustItem],
    timezone: Optional[str] = None,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Adjust stock levels for multiple products (increase or decrease)
    Access: Admin, Cashier, Employee
    
    Request Body:
    [
      {
        "product_id": "uuid",
        "quantity": 5,
        "action": "increase" or "decrease",
        "reason": "Stock count adjustment"
      },
      ...
    ]
    """
    from ..models.stock_entry import StockEntry, StockEntryType
    
    results = []
    
    for item in stock_items:
        # Get product
        product = await db.get(Product, UUID(item.product_id))
        if not product:
            results.append({
                "product_id": item.product_id,
                "status": "error",
                "message": "Product not found"
            })
            continue
        
        # Calculate adjustment amount
        if item.action == 'increase':
            adjustment_qty = item.quantity
        elif item.action == 'decrease':
            adjustment_qty = -item.quantity
        else:
            results.append({
                "product_id": item.product_id,
                "status": "error",
                "message": "Invalid action. Use 'increase' or 'decrease'"
            })
            continue
        
        # Create stock entry with ADJUST type
        entry = StockEntry(
            product_id=product.id,
            vendor_id=None,  # No vendor for adjustments
            qty=adjustment_qty,
            type=StockEntryType.ADJUST,
            location="Stock Adjustment",
            ref=f"ADJ_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        )
        db.add(entry)
        
        # Update product stock
        old_stock = product.stock_level
        product.stock_level += adjustment_qty
        
        # Prevent negative stock
        if product.stock_level < 0:
            product.stock_level = 0
        
        results.append({
            "product_id": item.product_id,
            "product_name": product.name,
            "action": item.action,
            "quantity_adjusted": item.quantity,
            "old_stock": old_stock,
            "new_stock": product.stock_level,
            "status": "success"
        })
    
    await db.commit()
    
    return {
        "message": "Stock adjustment completed successfully",
        "results": results
    }


@router.post("/savestockin")
async def save_stock_in(
    items: List[dict],
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Save stock in transactions for multiple products
    Multi-product stock in workflow
    Access: Admin, Cashier, Employee
    
    Request Body:
    [
      {
        "product_id": "uuid",
        "vendor_id": "uuid",
        "quantity": 50,
        "cost_price": 500.00,
        "date": "2026-02-21"
      },
      ...
    ]
    """
    from ..models.stock_entry import StockEntry, StockEntryType
    from ..models.vendor import Vendor
    import json
    from datetime import datetime

    results = []

    for item in items:
        product_id = item.get('product_id')
        vendor_id = item.get('vendor_id')
        quantity = int(item.get('quantity', 0))
        cost_price = float(item.get('cost_price', 0))
        date = item.get('date', datetime.now().strftime('%Y-%m-%d'))

        # Get product
        product = await db.get(Product, UUID(product_id))
        if not product:
            results.append({
                "product_id": product_id,
                "status": "error",
                "message": "Product not found"
            })
            continue

        # Get vendor
        vendor = await db.get(Vendor, UUID(vendor_id))
        if not vendor:
            results.append({
                "product_id": product_id,
                "status": "error",
                "message": "Vendor not found"
            })
            continue

        # Create stock entry
        entry = StockEntry(
            product_id=product.id,
            vendor_id=vendor.id,
            qty=quantity,
            cost_price=cost_price,
            type=StockEntryType.IN,
            location="Stock In",
            ref=f"STOCK_IN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        db.add(entry)

        # Update product stock
        product.stock_level += quantity

        # Update vendor balance (add cost amount to vendor's payable balance)
        total_cost = quantity * cost_price
        vendor.balance = float(vendor.balance) + total_cost

        # NOTE: Stock-In does NOT create payment history entry
        # Only actual payments create payment history entries

        results.append({
            "product_id": product_id,
            "product_name": product.name,
            "quantity_added": quantity,
            "new_stock_level": product.stock_level,
            "vendor_id": vendor_id,
            "vendor_name": vendor.name,
            "amount_added_to_balance": total_cost,
            "status": "success"
        })

    await db.commit()

    # Invalidate stock cache after stock-in
    from ..utils.cache import cache
    await cache.delete_pattern("stock:view:*")
    await cache.delete_pattern("product:barcode:*")

    return {
        "message": "Stock in completed successfully",
        "results": results
    }


@router.post("/savestockinwithbarcode")
async def save_stock_in_with_barcode(
    items: List[dict],
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Save stock in transactions for multiple products AND generate ZPL barcodes
    Multi-product stock in with barcode printing workflow
    Access: Admin, Cashier, Employee

    Request Body:
    [
      {
        "product_id": "uuid",
        "vendor_id": "uuid",
        "quantity": 50,
        "cost_price": 500.00,
        "selling_price": 750.00,
        "date": "2026-02-21"
      },
      ...
    ]

    Response:
    {
      "message": "...",
      "results": [...],
      "zpl_commands": [...]
    }
    """
    from ..models.stock_entry import StockEntry, StockEntryType
    from ..models.vendor import Vendor
    import json

    results = []
    zpl_commands = []

    for item in items:
        product_id = item.get('product_id')
        vendor_id = item.get('vendor_id')
        quantity = int(item.get('quantity', 0))
        cost_price = float(item.get('cost_price', 0))
        selling_price = float(item.get('selling_price', 0))
        date = item.get('date', datetime.now().strftime('%Y-%m-%d'))

        # Get product
        product = await db.get(Product, UUID(product_id))
        if not product:
            results.append({
                "product_id": product_id,
                "status": "error",
                "message": "Product not found"
            })
            continue

        # Get vendor
        vendor = await db.get(Vendor, UUID(vendor_id))
        if not vendor:
            results.append({
                "product_id": product_id,
                "status": "error",
                "message": "Vendor not found"
            })
            continue

        # Create stock entry
        entry = StockEntry(
            product_id=product.id,
            vendor_id=vendor.id,
            qty=quantity,
            cost_price=cost_price,
            type=StockEntryType.IN,
            location="Stock In",
            ref=f"STOCK_IN_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        db.add(entry)

        # Update product stock
        product.stock_level += quantity

        # Update vendor balance (add cost amount to vendor's payable balance)
        total_cost = quantity * cost_price
        vendor.balance = float(vendor.balance) + total_cost

        # NOTE: Stock-In does NOT create payment history entry
        # Only actual payments create payment history entries

        results.append({
            "product_id": product_id,
            "product_name": product.name,
            "quantity_added": quantity,
            "new_stock_level": product.stock_level,
            "vendor_id": vendor_id,
            "vendor_name": vendor.name,
            "amount_added_to_balance": total_cost,
            "status": "success"
        })
        
        # Generate ZPL barcode with new format (barcode lines, number, name, price)
        # Generate one barcode per unit (quantity)
        if product.barcode:
            # Use selling_price from request if provided, otherwise from product
            barcode_price = selling_price if selling_price > 0 else (product.sell_price or 0.0)

            # Generate ZPL for each unit in quantity
            for i in range(quantity):
                # ZPL for Zebra GX420d - 80mm label width (~576 dots @ 203dpi)
                # Center all content horizontally at x=70 (shifted right for better alignment)
                zpl = "^XA"

                # 1. Barcode - with auto human-readable number below (shifted right to 70, reduced width)
                zpl += f"^FO70,40^BY2,2,80^BCN,80,Y,N,N^FD{product.barcode}^FS"

                # 2. Product name - centered with word wrap (wider field block for longer names)
                # Adjusted X position to center the wider FB400 block (font size increased from 18 to 19)
                truncated_name = product.name[:40] if len(product.name) > 40 else product.name
                zpl += f"^FO10,150^A0N,19,19^FB400,2,0,C^FD{truncated_name}^FS"

                # 3. Price - centered, larger font (font size increased from 25 to 30)
                zpl += f"^FO80,175^A0N,30,30^FB250,1,0,C^FDRs. {int(barcode_price)}^FS"

                zpl += "^XZ"

                zpl_commands.append({
                    "product_id": product_id,
                    "product_name": product.name,
                    "barcode": product.barcode,
                    "quantity": quantity,
                    "unit_index": i + 1,  # Track which unit this barcode is for
                    "price": barcode_price,
                    "zpl": zpl
                })

    await db.commit()

    return {
        "message": "Stock in completed successfully with barcodes",
        "results": results,
        "zpl_commands": zpl_commands
    }


@router.post("/stockreport")
async def stock_report(
    cat_name: Optional[str] = None,
    pro_name: Optional[str] = None,
    ven_name: Optional[str] = None,
    timezone: Optional[str] = None,
    branches: Optional[str] = None,
    shelf: Optional[str] = None,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate stock report in PDF format (base64 encoded)
    Matches customer_invoice.py report pattern
    Access: Admin, Cashier, Employee
    """
    # Build query with filters - only products with stock > 0
    statement = select(Product).where(Product.stock_level > 0)

    if cat_name:
        statement = statement.where(Product.category == cat_name)
    if pro_name:
        statement = statement.where(Product.name.ilike(f"%{pro_name}%"))
    if branches:
        statement = statement.where(Product.branch == branches)

    result = await db.execute(statement)
    products = result.scalars().all()

    # Generate HTML content for PDF
    current_date = datetime.now().strftime('%d-%m-%Y')
    
    # Build product rows for PDF table
    product_rows = ""
    for i, product in enumerate(products):
        margin = 0.0
        if product.unit_price and product.cost_price and float(product.unit_price) != 0:
            # Calculate Margin % (Profit / Selling Price × 100)
            margin = ((float(product.unit_price) - float(product.cost_price)) / float(product.unit_price)) * 100

        product_rows += f"""
        <tr>
            <td class="border" style="text-align: center;">{i+1}</td>
            <td class="border">{product.name}</td>
            <td class="border">{product.category or '-'}</td>
            <td class="border" style="text-align: right;">{product.stock_level}</td>
            <td class="border" style="text-align: right;">{float(product.unit_price) if product.unit_price else 0.0:.2f}</td>
            <td class="border" style="text-align: right;">{float(product.cost_price) if product.cost_price else 0.0:.2f}</td>
            <td class="border" style="text-align: right;">{margin:.1f}%</td>
            <td class="border">{product.barcode or '-'}</td>
            <td class="border">{product.brand_action or '-'}</td>
            <td class="border">{product.branch or '-'}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4 landscape;
                margin: 15mm;
            }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 14px;
                margin: 0;
                padding: 0;
            }}
            h1 {{
                text-align: center;
                color: #333;
                margin: 0 0 10px 0;
                font-size: 26px;
                font-weight: bold;
            }}
            .print-date {{
                text-align: right;
                margin-bottom: 15px;
                color: #666;
                font-size: 12px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            th {{
                background-color: #444;
                color: white;
                border: 2px solid #000;
                padding: 12px 10px;
                text-align: left;
                font-weight: bold;
                font-size: 14px;
            }}
            td {{
                border: 1px solid #000;
                padding: 10px;
                font-size: 13px;
            }}
            .border {{
                border: 1px solid #000;
            }}
            .text-right {{
                text-align: right;
            }}
            tr:nth-child(even) {{
                background-color: #f5f5f5;
            }}
            tr:nth-child(odd) {{
                background-color: #fff;
            }}
            .footer {{
                margin-top: 20px;
                text-align: center;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <h1>Stock Report</h1>
        <div class="print-date"><strong>Print Date:</strong> {current_date}</div>
        <table>
            <thead>
                <tr>
                    <th style="width: 40px;">#</th>
                    <th>Product Name</th>
                    <th>Category</th>
                    <th style="text-align: right;">Stock</th>
                    <th style="text-align: right;">Price</th>
                    <th style="text-align: right;">Cost</th>
                    <th style="text-align: right;">Margin (%)</th>
                    <th>Barcode</th>
                    <th>Brand</th>
                    <th>Branch</th>
                </tr>
            </thead>
            <tbody>
                {product_rows}
            </tbody>
        </table>
        <div class="footer">
            <p>Total Products: {len(products)}</p>
        </div>
    </body>
    </html>
    """

    # Generate PDF using weasyprint
    try:
        from weasyprint import HTML
        from io import BytesIO

        pdf_doc = HTML(string=html_content)
        pdf_bytes = pdf_doc.write_pdf()
        encoded_pdf = base64.b64encode(pdf_bytes).decode()

    except ImportError:
        # Fallback to simple PDF
        pdf_content = "%PDF-1.4\n"
        pdf_content += "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        pdf_content += "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        pdf_content += "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 792 612] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        pdf_content += "4 0 obj\n<< /Length 300 >>\nstream\n"
        pdf_content += "BT\n/F1 18 Tf 350 550 Td (Stock Report) Tj ET\n"
        pdf_content += "ET\nendstream\nendobj\n"
        pdf_content += "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        pdf_content += "xref\n0 6\ntrailer\n<< /Size 6 /Root 1 0 R >>\n%%EOF"

        encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

    return encoded_pdf


@router.post("/stockinreport")
async def stock_in_report(
    date_from: str,
    date_to: str,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate date-wise stock-in report (PDF base64)
    Shows quantity added per product within date range (not current stock)
    Access: Admin, Cashier, Employee
    
    Query Params:
    - date_from: Start date (YYYY-MM-DD)
    - date_to: End date (YYYY-MM-DD)
    """
    from datetime import datetime as dt
    
    # Parse dates
    try:
        from_date = dt.strptime(date_from, "%Y-%m-%d")
        to_date = dt.strptime(date_to, "%Y-%m-%d")
        # Set to_date to end of day
        to_date = to_date.replace(hour=23, minute=59, second=59)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Query ALL stock entries with type=IN within date range (not grouped)
    from sqlalchemy import func

    statement = (
        select(StockEntry)
        .where(StockEntry.type == StockEntryType.IN)
        .where(StockEntry.created_at >= from_date)
        .where(StockEntry.created_at <= to_date)
        .order_by(StockEntry.created_at.desc())
    )

    result = await db.execute(statement)
    stock_in_entries = result.scalars().all()

    if not stock_in_entries:
        # Return empty report
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{ size: A4 landscape; margin: 15mm; }}
                body {{ font-family: Arial, sans-serif; font-size: 14px; margin: 0; padding: 0; }}
                h1 {{ text-align: center; color: #333; margin: 0 0 10px 0; font-size: 26px; font-weight: bold; }}
                .date-range {{ text-align: center; margin-bottom: 15px; color: #666; font-size: 12px; }}
                .no-data {{ text-align: center; padding: 50px; color: #999; font-size: 16px; }}
            </style>
        </head>
        <body>
            <h1>Stock In Report</h1>
            <div class="date-range">From: {date_from} | To: {date_to}</div>
            <div class="no-data">No stock entries found for this date range</div>
        </body>
        </html>
        """
    else:
        # Build product rows with individual stock-in entries (with date & time at end)
        product_rows = ""
        for i, entry in enumerate(stock_in_entries):
            product = await db.get(Product, entry.product_id)
            if product:
                # Format date and time
                entry_date = entry.created_at.strftime("%d-%m-%Y")
                entry_time = entry.created_at.strftime("%I:%M %p")
                
                product_rows += f"""
                <tr>
                    <td class="border" style="text-align: center;">{i+1}</td>
                    <td class="border">{product.name}</td>
                    <td class="border">{product.barcode or '-'}</td>
                    <td class="border text-right">{entry.qty}</td>
                    <td class="border text-right">{float(product.unit_price) if product.unit_price else 0.0:.2f}</td>
                    <td class="border text-right">{float(product.cost_price) if product.cost_price else 0.0:.2f}</td>
                    <td class="border">{product.category or '-'}</td>
                    <td class="border">{product.branch or '-'}</td>
                    <td class="border">{entry_date}</td>
                    <td class="border">{entry_time}</td>
                </tr>
                """

        # Calculate total
        total_qty = sum(entry.qty for entry in stock_in_entries)
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{
                    size: A4 landscape;
                    margin: 15mm;
                }}
                body {{
                    font-family: Arial, sans-serif;
                    font-size: 14px;
                    margin: 0;
                    padding: 0;
                }}
                h1 {{
                    text-align: center;
                    color: #333;
                    margin: 0 0 10px 0;
                    font-size: 26px;
                    font-weight: bold;
                }}
                .date-range {{
                    text-align: center;
                    margin-bottom: 15px;
                    color: #666;
                    font-size: 12px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                th {{
                    background-color: #444;
                    color: white;
                    border: 2px solid #000;
                    padding: 12px 10px;
                    text-align: left;
                    font-weight: bold;
                    font-size: 14px;
                }}
                td {{
                    border: 1px solid #000;
                    padding: 10px;
                    font-size: 13px;
                }}
                .border {{
                    border: 1px solid #000;
                }}
                .text-right {{
                    text-align: right;
                }}
                tr:nth-child(even) {{
                    background-color: #f5f5f5;
                }}
                tr:nth-child(odd) {{
                    background-color: #fff;
                }}
                .footer {{
                    margin-top: 20px;
                    text-align: center;
                    font-size: 12px;
                    color: #666;
                }}
            </style>
        </head>
        <body>
            <h1>Stock In Report</h1>
            <div class="date-range">From: {date_from} | To: {date_to}</div>
            <table>
                <thead>
                    <tr>
                        <th>S.No</th>
                        <th>Product Name</th>
                        <th>Barcode</th>
                        <th>Qty In</th>
                        <th>Price</th>
                        <th>Cost</th>
                        <th>Category</th>
                        <th>Branch</th>
                        <th>Date</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody>
                    {product_rows}
                </tbody>
                <tfoot>
                    <tr>
                        <td colspan="3" class="border text-right" style="font-weight: bold;">Total:</td>
                        <td class="border text-right" style="font-weight: bold;">{total_qty}</td>
                        <td colspan="6"></td>
                    </tr>
                </tfoot>
            </table>
        </body>
        </html>
        """
    
    # Generate PDF
    try:
        from weasyprint import HTML
        from io import BytesIO

        pdf_doc = HTML(string=html_content)
        pdf_bytes = pdf_doc.write_pdf()
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
    except ImportError:
        # Fallback
        pdf_content = "%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        pdf_content += "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        pdf_content += "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 792 612] /Contents 4 0 R >>\nendobj\n"
        pdf_content += "4 0 obj\n<< /Length 100 >>\nstream\n"
        pdf_content += "BT\n/F1 18 Tf 350 550 Td (Stock In Report) Tj ET\n"
        pdf_content += "ET\nendstream\nendobj\n"
        pdf_content += "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        pdf_content += "xref\n0 6\ntrailer\n<< /Size 6 /Root 1 0 R >>\n%%EOF"
        encoded_pdf = base64.b64encode(pdf_content.encode()).decode()
    
    return encoded_pdf


@router.post("/stockreportexcel")
async def stock_report_excel(
    cat_name: Optional[str] = None,
    pro_name: Optional[str] = None,
    ven_name: Optional[str] = None,
    timezone: Optional[str] = None,
    branches: Optional[str] = None,
    shelf: Optional[str] = None,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate stock report in Excel format (base64 encoded)
    Access: Admin, Cashier, Employee
    """
    import io
    from openpyxl import Workbook

    # Build query with filters
    statement = select(Product)

    if cat_name:
        statement = statement.where(Product.category == cat_name)
    if pro_name:
        statement = statement.where(Product.name.ilike(f"%{pro_name}%"))
    if branches:
        statement = statement.where(Product.branch == branches)

    result = await db.execute(statement)
    products = result.scalars().all()

    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Stock Report"

    # Add headers
    headers = ["Sr.No", "Product Name", "Category", "Stock", "Price", "Cost", "Margin (%)", "Barcode", "Brand", "Branch"]
    ws.append(headers)

    # Add data
    for idx, product in enumerate(products):
        margin = 0.0
        if product.unit_price and product.cost_price and float(product.unit_price) != 0:
            # Calculate Margin % (Profit / Selling Price × 100)
            margin = ((float(product.unit_price) - float(product.cost_price)) / float(product.unit_price)) * 100

        row = [
            idx + 1,
            product.name,
            product.category or "",
            product.stock_level,
            float(product.unit_price) if product.unit_price else 0.0,
            float(product.cost_price) if product.cost_price else 0.0,
            round(margin, 2),
            product.barcode or "",
            product.brand_action or "",
            product.branch or ""
        ]
        ws.append(row)

    # Save to bytes
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # Return as base64 encoded Excel file
    excel_content = buffer.getvalue()
    encoded_excel = base64.b64encode(excel_content).decode()

    return encoded_excel


@router.post("/dailyinventoryreport")
async def daily_inventory_report(
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate daily inventory report in PDF format (base64 encoded)
    Matches customer_invoice.py report pattern
    Access: Admin, Cashier, Employee
    """
    # Get all products
    statement = select(Product)
    result = await db.execute(statement)
    products = result.scalars().all()

    # Generate HTML content for PDF
    current_date = datetime.now().strftime('%d-%m-%Y')
    
    product_rows = ""
    for i, product in enumerate(products):
        product_rows += f"""
        <tr>
            <td class="border" style="text-align: center;">{i+1}</td>
            <td class="border">{product.name}</td>
            <td class="border" style="text-align: right;">{product.stock_level}</td>
            <td class="border">{product.branch or '-'}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4;
                margin: 15mm;
            }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 14px;
                margin: 0;
                padding: 0;
            }}
            h1 {{
                text-align: center;
                color: #333;
                margin: 0 0 10px 0;
                font-size: 24px;
                font-weight: bold;
            }}
            .print-date {{
                text-align: right;
                margin-bottom: 15px;
                color: #666;
                font-size: 12px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            th {{
                background-color: #444;
                color: white;
                border: 2px solid #000;
                padding: 12px 10px;
                text-align: left;
                font-weight: bold;
                font-size: 14px;
            }}
            td {{
                border: 1px solid #000;
                padding: 10px;
                font-size: 13px;
            }}
            .border {{
                border: 1px solid #000;
            }}
            tr:nth-child(even) {{
                background-color: #f5f5f5;
            }}
            tr:nth-child(odd) {{
                background-color: #fff;
            }}
            .footer {{
                margin-top: 20px;
                text-align: center;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <h1>Daily Inventory Report - {current_date}</h1>
        <div class="print-date"><strong>Print Date:</strong> {current_date}</div>
        <table>
            <thead>
                <tr>
                    <th style="width: 40px;">#</th>
                    <th>Product Name</th>
                    <th style="text-align: right;">Stock Level</th>
                    <th>Branch</th>
                </tr>
            </thead>
            <tbody>
                {product_rows}
            </tbody>
        </table>
        <div class="footer">
            <p>Total Products: {len(products)}</p>
        </div>
    </body>
    </html>
    """

    # Generate PDF
    try:
        from weasyprint import HTML
        pdf_doc = HTML(string=html_content)
        pdf_bytes = pdf_doc.write_pdf()
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
    except ImportError:
        pdf_content = "%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        pdf_content += "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        pdf_content += "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
        pdf_content += "4 0 obj\n<< /Length 60 >>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Daily Inventory Report - " + datetime.now().strftime("%Y-%m-%d") + ") Tj\nET\nendstream\nendobj\n"
        pdf_content += "xref\n0 5\ntrailer\n<< /Size 5 /Root 1 0 R >>\n%%EOF"
        encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

    return encoded_pdf


@router.post("/printbarcodes")
async def print_barcodes(
    pro_name: str,
    quantity: int,
    barcode: Optional[str] = None,
    price: Optional[float] = None,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate ZPL commands for printing barcodes with format:
    1. Barcode lines (Code 128)
    2. Barcode number
    3. Product name
    4. Price
    Access: Admin, Cashier, Employee
    """
    # Get product details if barcode not provided
    if not barcode:
        statement = select(Product).where(Product.name == pro_name)
        result = await db.execute(statement)
        product = result.scalar_one_or_none()

        if product:
            barcode = product.barcode or product.sku or pro_name
            if price is None:
                price = product.sell_price

    if not barcode:
        barcode = pro_name

    if price is None:
        price = 0.0

    # ZPL for Zebra GX420d - 80mm label width (~576 dots @ 203dpi)
    # Center all content horizontally at x=70 (shifted right for better alignment)
    zpl_commands = "^XA"

    for i in range(quantity):
        # Center position: x=70, y=40 (adjusted for better alignment)
        x_center = 70
        y_start = 40

        # 1. Barcode - with auto human-readable number below (reduced width for compact print)
        zpl_commands += f"^FO{x_center},{y_start}^BY2,2,80^BCN,80,Y,N,N^FD{barcode}^FS"

        # 2. Product name - centered with word wrap (font size increased from 18 to 19)
        truncated_name = pro_name[:40] if len(pro_name) > 40 else pro_name
        zpl_commands += f"^FO10,{y_start + 110}^A0N,19,19^FB400,2,0,C^FD{truncated_name}^FS"

        # 3. Price - centered, larger font (font size increased from 25 to 30)
        zpl_commands += f"^FO80,{y_start + 135}^A0N,30,30^FB250,1,0,C^FDRs. {int(price)}^FS"

        # End current label and start new one for next barcode
        if i < quantity - 1:
            zpl_commands += "^XZ"
            zpl_commands += "^XA"

    zpl_commands += "^XZ"

    return {
        "zpl_commands": zpl_commands,
        "product": pro_name,
        "quantity": quantity,
        "barcode": barcode,
        "price": price,
        "message": f"Generated ZPL for {quantity} barcode(s) of {pro_name}"
    }


@router.post("/generatebarcodesonly")
async def generate_barcodes_only(
    items: List[dict],
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate ZPL barcodes for multiple products WITHOUT saving stock-in
    Access: Admin, Cashier, Employee
    """
    zpl_commands = []
    
    for item in items:
        product_id = item.get('product_id')
        quantity = int(item.get('quantity', 0))
        barcode = item.get('barcode', '')
        price = float(item.get('price', 0))
        
        # Get product if not provided
        if not barcode or price == 0:
            product = await db.get(Product, UUID(product_id))
            if product:
                if not barcode:
                    barcode = product.barcode or product.sku or ''
                if price == 0:
                    price = float(product.sell_price or 0)
        
        # Skip if no barcode
        if not barcode:
            continue
        
        # Get product name
        product = await db.get(Product, UUID(product_id))
        pro_name = product.name if product else 'Product'

        # Generate ZPL for each unit
        for i in range(quantity):
            # Complete ZPL label
            zpl = "^XA"

            # 1. Barcode with auto human-readable (shifted right to 70, reduced width)
            zpl += f"^FO70,40^BY2,2,80^BCN,80,Y,N,N^FD{barcode}^FS"

            # 2. Product name - truncated and centered (font size increased from 18 to 19)
            truncated_name = pro_name[:40] if len(pro_name) > 40 else pro_name
            zpl += f"^FO10,150^A0N,19,19^FB400,2,0,C^FD{truncated_name}^FS"

            # 3. Price - centered, larger font (font size increased from 25 to 30)
            zpl += f"^FO80,175^A0N,30,30^FB250,1,0,C^FDRs. {int(price)}^FS"

            # End label
            zpl += "^XZ"

            # Only add if ZPL is valid (has ^XA and ^XZ)
            if zpl.startswith("^XA") and zpl.endswith("^XZ") and len(zpl) > 50:
                zpl_commands.append({
                    "product_id": product_id,
                    "barcode": barcode,
                    "quantity": quantity,
                    "unit_index": i + 1,
                    "price": price,
                    "zpl": zpl
                })
    
    return {
        "message": f"Generated {len(zpl_commands)} barcode(s)",
        "zpl_commands": zpl_commands
    }


@router.post("/savestockinwithbarcodes")
async def save_stock_in_with_barcodes(
    stock_items: Optional[List[dict]] = None,
    timezone: Optional[str] = None,
    Date: Optional[str] = None,
    print_barcodes: bool = False,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Save stock in transactions with optional barcode printing
    Access: Admin, Cashier, Employee
    Note: Full functionality to be implemented later
    """
    # Placeholder - to be implemented
    return {"message": "Save stock in with barcodes endpoint - to be implemented"}


# ============================================================================
# Legacy Stock Entry CRUD Endpoints (For Internal Use)
# ============================================================================

@router.get("/", response_model=List[StockEntryRead])
async def get_stock_entries(
    product_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of stock entries with pagination
    Access: Admin, Cashier, Employee
    """
    product_uuid = None
    if product_id:
        try:
            product_uuid = UUID(product_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid product ID format"
            )

    stock_entries = await StockService.get_stock_entries(db, product_id=product_uuid, skip=skip, limit=limit)
    return stock_entries


@router.post("/", response_model=StockEntryRead)
async def create_stock_entry(
    stock_entry_create: StockEntryCreate,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new stock entry
    Access: Admin, Cashier, Employee
    """
    return await StockService.create_stock_entry(db, stock_entry_create)


@router.get("/{stock_id}", response_model=StockEntryRead)
async def get_stock_entry(
    stock_id: str,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific stock entry by ID
    Access: Admin, Cashier, Employee
    """
    try:
        stock_uuid = UUID(stock_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid stock entry ID format"
        )

    stock_entry = await StockService.get_stock_entry(db, stock_uuid)

    if not stock_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock entry not found"
        )

    return stock_entry


@router.put("/{stock_id}", response_model=StockEntryRead)
async def update_stock_entry(
    stock_id: str,
    stock_entry_update: StockEntryUpdate,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific stock entry by ID
    Access: Admin, Cashier, Employee
    """
    try:
        stock_uuid = UUID(stock_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid stock entry ID format"
        )

    stock_entry = await StockService.get_stock_entry(db, stock_uuid)

    if not stock_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock entry not found"
        )

    return await StockService.update_stock_entry(db, stock_uuid, stock_entry_update)


@router.delete("/{stock_id}")
async def delete_stock_entry(
    stock_id: str,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific stock entry by ID
    Access: Admin, Cashier, Employee
    """
    try:
        stock_uuid = UUID(stock_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid stock entry ID format"
        )

    success = await StockService.delete_stock_entry(db, stock_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock entry not found"
        )

    return {"message": "Stock entry deleted successfully"}
