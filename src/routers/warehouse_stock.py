from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from datetime import datetime
import logging
import base64

from ..database.database import get_db
from ..models.product import Product
from ..models.stock_entry import StockEntry, StockEntryType
from ..models.user import User
from ..services.product_service import ProductService
from ..auth.session_auth import get_current_user_from_session
from sqlmodel import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/warehouse-stock", tags=["warehouse-stock"])


def warehouse_required():
    """Require warehouse role from session"""
    async def role_checker(current_user: User = Depends(get_current_user_from_session)):
        if current_user.role.name not in ["warehouse", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Warehouse or admin access required"
            )
        return current_user
    return role_checker


class StockInRequest(BaseModel):
    product_id: str
    qty: int
    ref: Optional[str] = None


class StockAdjustRequest(BaseModel):
    product_id: str
    qty: int  # positive for increase, negative for decrease
    ref: Optional[str] = None


@router.post("/in")
async def stock_in(
    request: StockInRequest,
    current_user: User = Depends(warehouse_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Add stock to warehouse_stock column (products where is_warehouse_product = true)
    """
    try:
        product_uuid = UUID(request.product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    product = await ProductService.get_product(db, product_uuid)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    if not product.is_warehouse_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This product is not marked as warehouse product"
        )

    # Update warehouse_stock column
    product.warehouse_stock = (product.warehouse_stock or 0) + request.qty
    db.add(product)

    # Create stock entry
    stock_entry = StockEntry(
        product_id=product_uuid,
        qty=request.qty,
        type=StockEntryType.IN,
        location="warehouse",
        ref=request.ref
    )
    db.add(stock_entry)

    await db.commit()
    await db.refresh(product)

    return {
        "success": True,
        "message": "Stock added successfully",
        "new_stock": product.warehouse_stock
    }


@router.post("/adjust")
async def adjust_stock(
    request: StockAdjustRequest,
    current_user: User = Depends(warehouse_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Adjust warehouse_stock column (increase/decrease)
    """
    try:
        product_uuid = UUID(request.product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    product = await ProductService.get_product(db, product_uuid)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    if not product.is_warehouse_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This product is not marked as warehouse product"
        )

    # Adjust warehouse_stock column
    product.warehouse_stock = (product.warehouse_stock or 0) + request.qty
    db.add(product)

    stock_entry = StockEntry(
        product_id=product_uuid,
        qty=request.qty,
        type=StockEntryType.ADJUST,
        location="warehouse",
        ref=request.ref
    )
    db.add(stock_entry)

    await db.commit()
    await db.refresh(product)

    return {
        "success": True,
        "message": "Stock adjusted successfully",
        "new_stock": product.warehouse_stock
    }


@router.get("/view")
async def view_stock(
    page: int = 1,
    limit: int = 10,
    search: str = None,
    current_user: User = Depends(warehouse_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    View warehouse stock (products where is_warehouse_product = true)
    Shows warehouse_stock column values
    """
    from sqlalchemy import or_

    skip = (page - 1) * limit

    # Build query - only warehouse products with stock > 0
    base_statement = select(
        Product.id,
        Product.name,
        Product.warehouse_stock,
        Product.category,
        Product.branch,
        Product.article_no,
        Product.warehouse_limited_qty,
        Product.barcode,
        Product.sku,
        Product.unit_price,
        Product.cost_price,
        Product.is_warehouse_product
    ).where(
        Product.is_warehouse_product == True,
        Product.warehouse_stock > 0
    )

    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        base_statement = base_statement.where(
            or_(
                Product.name.ilike(search_pattern),
                Product.barcode.ilike(search_pattern),
                Product.article_no.ilike(search_pattern),
                Product.sku.ilike(search_pattern)
            )
        )

    # Get total count - only warehouse products with stock > 0
    count_statement = select(Product.id).where(
        Product.is_warehouse_product == True,
        Product.warehouse_stock > 0
    )
    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        count_statement = count_statement.where(
            or_(
                Product.name.ilike(search_pattern),
                Product.barcode.ilike(search_pattern),
                Product.article_no.ilike(search_pattern),
                Product.sku.ilike(search_pattern)
            )
        )

    count_result = await db.execute(count_statement)
    total_count = len(count_result.scalars().all())

    # Apply pagination
    statement = base_statement.order_by(Product.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(statement)
    products = result.fetchall()

    # Format response
    result_list = [
        {
            "id": str(p[0]),
            "name": p[1],
            "warehouse_stock": p[2] or 0,
            "category": p[3] or "",
            "branch": p[4] or "",
            "article_no": p[5] or "",
            "warehouse_limited_qty": p[6] or 0,
            "barcode": p[7] or "",
            "sku": p[8] or "",
            "unit_price": float(p[9]) if p[9] else 0,
            "cost_price": float(p[10]) if p[10] else 0,
            "is_warehouse_product": p[11] or False
        }
        for p in products
    ]

    total_pages = (total_count + limit - 1) // limit

    return {
        'data': result_list,
        'page': page,
        'limit': limit,
        'total': total_count,
        'total_pages': total_pages,
        'has_more': page < total_pages
    }


@router.post("/out")
async def stock_out(
    request: StockAdjustRequest,
    current_user: User = Depends(warehouse_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Reduce warehouse_stock column (stock out)
    """
    try:
        product_uuid = UUID(request.product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    product = await ProductService.get_product(db, product_uuid)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    if not product.is_warehouse_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This product is not marked as warehouse product"
        )

    # Check if enough stock is available
    current_stock = product.warehouse_stock or 0
    if current_stock < request.qty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {current_stock}, Requested: {request.qty}"
        )

    # Reduce warehouse_stock column
    product.warehouse_stock = current_stock - request.qty
    db.add(product)

    stock_entry = StockEntry(
        product_id=product_uuid,
        qty=-request.qty,  # Negative quantity for stock out
        type=StockEntryType.OUT,
        location="warehouse",
        ref=request.ref
    )
    db.add(stock_entry)

    await db.commit()
    await db.refresh(product)

    return {
        "success": True,
        "message": "Stock removed successfully",
        "new_stock": product.warehouse_stock
    }


@router.get("/entries")
async def get_warehouse_entries(
    page: int = 1,
    limit: int = 10,
    product_id: str = None,
    current_user: User = Depends(warehouse_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get warehouse stock entries with pagination
    """
    skip = (page - 1) * limit

    # Build query
    statement = select(
        StockEntry.id,
        StockEntry.product_id,
        StockEntry.qty,
        StockEntry.type,
        StockEntry.ref,
        StockEntry.created_at,
        Product.name,
        Product.barcode
    ).join(
        Product, StockEntry.product_id == Product.id
    ).where(
        StockEntry.location == "warehouse"
    )

    if product_id:
        try:
            product_uuid = UUID(product_id)
            statement = statement.where(StockEntry.product_id == product_uuid)
        except ValueError:
            pass

    # Get total count
    count_statement = select(StockEntry.id).where(StockEntry.location == "warehouse")
    if product_id:
        try:
            product_uuid = UUID(product_id)
            count_statement = count_statement.where(StockEntry.product_id == product_uuid)
        except ValueError:
            pass

    count_result = await db.execute(count_statement)
    total_count = len(count_result.scalars().all())

    # Apply pagination
    statement = statement.order_by(StockEntry.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(statement)
    entries = result.fetchall()

    # Format response
    result_list = [
        {
            "id": str(e[0]),
            "product_id": str(e[1]),
            "qty": e[2],
            "type": e[3].value if hasattr(e[3], 'value') else str(e[3]),
            "ref": e[4] or "",
            "created_at": e[5].isoformat() if e[5] else None,
            "product_name": e[6],
            "barcode": e[7] or ""
        }
        for e in entries
    ]

    total_pages = (total_count + limit - 1) // limit

    return {
        'data': result_list,
        'page': page,
        'limit': limit,
        'total': total_count,
        'total_pages': total_pages,
        'has_more': page < total_pages
    }


@router.put("/update/{entry_id}")
async def update_stock_entry(
    entry_id: UUID,
    request: StockAdjustRequest,
    current_user: User = Depends(warehouse_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update an existing stock entry and adjust warehouse_stock accordingly
    """
    try:
        product_uuid = UUID(request.product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    # Find the stock entry
    statement = select(StockEntry).where(StockEntry.id == entry_id)
    result = await db.execute(statement)
    stock_entry = result.scalar_one_or_none()

    if not stock_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock entry not found"
        )

    if stock_entry.location != "warehouse":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This entry is not a warehouse stock entry"
        )

    product = await ProductService.get_product(db, product_uuid)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    if not product.is_warehouse_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This product is not marked as warehouse product"
        )

    # Reverse the old entry effect
    old_qty = stock_entry.qty
    product.warehouse_stock = (product.warehouse_stock or 0) - old_qty

    # Apply the new quantity
    product.warehouse_stock = (product.warehouse_stock or 0) + request.qty

    # Update the stock entry
    stock_entry.qty = request.qty
    stock_entry.ref = request.ref
    stock_entry.updated_at = datetime.now()

    db.add(product)
    db.add(stock_entry)

    await db.commit()
    await db.refresh(product)

    return {
        "success": True,
        "message": "Stock entry updated successfully",
        "new_stock": product.warehouse_stock
    }


@router.delete("/delete/{entry_id}")
async def delete_stock_entry(
    entry_id: UUID,
    current_user: User = Depends(warehouse_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a stock entry and reverse its effect on warehouse_stock
    """
    # Find the stock entry
    statement = select(StockEntry).where(StockEntry.id == entry_id)
    result = await db.execute(statement)
    stock_entry = result.scalar_one_or_none()

    if not stock_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock entry not found"
        )

    if stock_entry.location != "warehouse":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This entry is not a warehouse stock entry"
        )

    product = await ProductService.get_product(db, stock_entry.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Reverse the stock entry effect
    product.warehouse_stock = (product.warehouse_stock or 0) - stock_entry.qty

    db.add(product)
    await db.delete(stock_entry)

    await db.commit()
    await db.refresh(product)

    return {
        "success": True,
        "message": "Stock entry deleted successfully",
        "new_stock": product.warehouse_stock
    }


@router.post("/requirement-report")
async def warehouse_requirement_report(
    current_user: User = Depends(warehouse_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate warehouse requirement report in PDF format (base64 encoded)
    Shows products that need restocking in warehouse
    Access: Warehouse, Admin
    """
    # Build query - only warehouse products
    statement = select(Product).where(Product.is_warehouse_product == True)

    result = await db.execute(statement)
    products = result.scalars().all()

    # Generate HTML content for PDF
    current_date = datetime.now().strftime('%d-%m-%Y')
    
    # Build product rows for PDF table
    product_rows = ""
    row_count = 0
    for product in products:
        # Calculate Required Stock (Limited qty - Warehouse stock)
        limited_qty = product.warehouse_limited_qty or 0
        current_stock = product.warehouse_stock or 0
        required_stock = max(0, limited_qty - current_stock)

        # Skip products that don't need restocking
        if required_stock <= 0:
            continue
            
        row_count += 1
        product_rows += f"""
        <tr>
            <td class="border" style="text-align: center;">{row_count}</td>
            <td class="border">{product.name}</td>
            <td class="border">{product.category or '-'}</td>
            <td class="border">{product.article_no or '-'}</td>
            <td class="border" style="text-align: right;">{float(product.cost_price) if product.cost_price else 0.0:.2f}</td>
            <td class="border" style="text-align: right;">{float(product.unit_price) if product.unit_price else 0.0:.2f}</td>
            <td class="border">{product.barcode or '-'}</td>
            <td class="border">{product.brand_action or '-'}</td>
            <td class="border" style="text-align: right;">{limited_qty}</td>
            <td class="border" style="text-align: right;">{current_stock}</td>
            <td class="border" style="text-align: right; font-weight: bold; color: #e11d48;">{required_stock}</td>
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
                margin: 10mm;
            }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 11px;
                margin: 0;
                padding: 0;
            }}
            h1 {{
                text-align: center;
                color: #333;
                margin: 0 0 10px 0;
                font-size: 22px;
                font-weight: bold;
            }}
            .print-date {{
                text-align: right;
                margin-bottom: 10px;
                color: #666;
                font-size: 10px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 5px;
            }}
            th {{
                background-color: #444;
                color: white;
                border: 1px solid #000;
                padding: 8px 5px;
                text-align: left;
                font-weight: bold;
                font-size: 11px;
            }}
            td {{
                border: 1px solid #000;
                padding: 6px 5px;
                font-size: 10px;
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
                margin-top: 15px;
                text-align: center;
                font-size: 10px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <h1>Warehouse Requirement Report</h1>
        <div class="print-date"><strong>Print Date:</strong> {current_date}</div>
        <table>
            <thead>
                <tr>
                    <th style="width: 30px;">#</th>
                    <th>Product Name</th>
                    <th>Category</th>
                    <th>Article No</th>
                    <th style="text-align: right;">Cost</th>
                    <th style="text-align: right;">Price</th>
                    <th>Barcode</th>
                    <th>Brand</th>
                    <th style="text-align: right;">Ltd Qty</th>
                    <th style="text-align: right;">Stock</th>
                    <th style="text-align: right;">Required</th>
                </tr>
            </thead>
            <tbody>
                {product_rows}
            </tbody>
        </table>
        <div class="footer">
            <p>Total Warehouse Products: {len(products)}</p>
        </div>
    </body>
    </html>
    """

    # Generate PDF using weasyprint
    try:
        from weasyprint import HTML
        pdf_doc = HTML(string=html_content)
        pdf_bytes = pdf_doc.write_pdf()
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
    except ImportError:
        # Fallback to simple PDF base64 if weasyprint not available
        fallback_msg = "PDF Generation Error: weasyprint not installed"
        encoded_pdf = base64.b64encode(fallback_msg.encode()).decode()

    return encoded_pdf


@router.post("/shop-requirement-report")
async def shop_requirement_report(
    current_user: User = Depends(warehouse_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate shop requirement report for warehouse products (PDF base64)
    Shows what the shop needs based on its limited_qty and stock_level
    Access: Warehouse, Admin
    """
    # Build query - only warehouse products
    statement = select(Product).where(Product.is_warehouse_product == True)

    result = await db.execute(statement)
    products = result.scalars().all()

    # Generate HTML content for PDF
    current_date = datetime.now().strftime('%d-%m-%Y')
    
    # Build product rows for PDF table
    product_rows = ""
    row_count = 0
    for product in products:
        # Calculate Required Stock (Shop Limited qty - Shop Stock Level)
        limited_qty = product.limited_qty or 0
        stock_level = product.stock_level or 0
        required_stock = max(0, limited_qty - stock_level)

        # Skip products that don't need restocking
        if required_stock <= 0:
            continue
            
        row_count += 1
        product_rows += f"""
        <tr>
            <td class="border" style="text-align: center;">{row_count}</td>
            <td class="border">{product.name}</td>
            <td class="border">{product.category or '-'}</td>
            <td class="border">{product.barcode or '-'}</td>
            <td class="border" style="text-align: right;">{limited_qty}</td>
            <td class="border" style="text-align: right;">{stock_level}</td>
            <td class="border" style="text-align: right; font-weight: bold; color: #e11d48;">{required_stock}</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4 portrait;
                margin: 15mm;
            }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 12px;
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
                font-size: 11px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            th {{
                background-color: #444;
                color: white;
                border: 1px solid #000;
                padding: 10px 8px;
                text-align: left;
                font-weight: bold;
                font-size: 12px;
            }}
            td {{
                border: 1px solid #000;
                padding: 8px 8px;
                font-size: 11px;
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
                font-size: 11px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <h1>Shop Requirement Report</h1>
        <div class="print-date"><strong>Print Date:</strong> {current_date}</div>
        <table>
            <thead>
                <tr>
                    <th style="width: 40px;">#</th>
                    <th>Product Name</th>
                    <th>Category</th>
                    <th>Barcode</th>
                    <th style="text-align: right;">Limited Qty</th>
                    <th style="text-align: right;">Stock Level</th>
                    <th style="text-align: right;">Required</th>
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
        pdf_doc = HTML(string=html_content)
        pdf_bytes = pdf_doc.write_pdf()
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
    except ImportError:
        # Fallback to simple PDF base64 if weasyprint not available
        fallback_msg = "PDF Generation Error: weasyprint not installed"
        encoded_pdf = base64.b64encode(fallback_msg.encode()).decode()

    return encoded_pdf
