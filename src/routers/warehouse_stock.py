from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
import logging

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

    # Build query - only warehouse products
    base_statement = select(
        Product.id,
        Product.name,
        Product.warehouse_stock,
        Product.category,
        Product.branch,
        Product.article_no,
        Product.warehouse_limited_qty
    ).where(
        Product.is_warehouse_product == True
    )

    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        base_statement = base_statement.where(
            or_(
                Product.name.ilike(search_pattern),
                Product.barcode.ilike(search_pattern),
                Product.article_no.ilike(search_pattern)
            )
        )

    # Get total count
    count_statement = select(Product.id).where(Product.is_warehouse_product == True)
    if search and search.strip():
        search_pattern = f"%{search.strip()}%"
        count_statement = count_statement.where(
            or_(
                Product.name.ilike(search_pattern),
                Product.barcode.ilike(search_pattern),
                Product.article_no.ilike(search_pattern)
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
            "warehouse_limited_qty": p[6] or 0
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
