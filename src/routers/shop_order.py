from fastapi import APIRouter, Depends, HTTPException, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from typing import Optional
from uuid import UUID
from datetime import datetime

from ..database.database import get_db
from ..models.user import User
from ..models.product import Product
from ..models.shop_order import ShopOrder, ShopOrderStatus, ShopOrderCreate
from ..auth.session_auth import employee_required_from_session

router = APIRouter()

# Matches the "Short Stock" threshold used on the dashboard (salesview/dashboard/stats)
# so the counts on the dashboard cards and this list stay in sync.
SHORT_STOCK_THRESHOLD = 5


@router.get("/stock-list")
async def get_stock_list(
    filter: str = "all",
    search_string: Optional[str] = None,
    page: int = 1,
    limit: int = 8,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    List products for the Stock Order page, filtered by stock condition:
    - zero: stock_level <= 0 (Out of Stock)
    - short: 0 < stock_level < 5 (Short Stock)
    - all: every product
    """
    if page < 1:
        page = 1
    if limit <= 0 or limit > 100:
        limit = 8
    skip = (page - 1) * limit

    conditions = []
    if filter == "zero":
        conditions.append(Product.stock_level <= 0)
    elif filter == "short":
        conditions.append(and_(Product.stock_level > 0, Product.stock_level < SHORT_STOCK_THRESHOLD))
    # filter == "all" -> no stock condition

    if search_string and search_string.strip():
        pattern = f"%{search_string.strip()}%"
        conditions.append(or_(Product.name.ilike(pattern), Product.barcode.ilike(pattern)))

    count_statement = select(func.count(Product.id))
    statement = select(
        Product.id,
        Product.name,
        Product.barcode,
        Product.category,
        Product.stock_level,
    )
    for condition in conditions:
        count_statement = count_statement.where(condition)
        statement = statement.where(condition)

    count_result = await db.execute(count_statement)
    total_count = count_result.scalar() or 0

    statement = statement.order_by(Product.name).offset(skip).limit(limit)
    result = await db.execute(statement)
    rows = result.fetchall()

    data = [
        {
            "id": str(row[0]),
            "name": row[1],
            "barcode": row[2] or "",
            "category": row[3] or "",
            "stock": row[4],
        }
        for row in rows
    ]

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    return {
        "data": data,
        "page": page,
        "limit": limit,
        "total": total_count,
        "total_pages": total_pages,
        "has_more": page < total_pages,
    }


@router.post("/create")
async def create_shop_order(
    order_data: ShopOrderCreate,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Place a shop order (restock request) for a product."""
    if order_data.quantity_ordered <= 0:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Order quantity must be greater than zero"
        )

    product_result = await db.execute(select(Product).where(Product.id == order_data.product_id))
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    shop_order = ShopOrder(
        product_id=product.id,
        product_name=product.name,
        barcode=product.barcode,
        category=product.category,
        stock_at_order_time=product.stock_level,
        quantity_ordered=order_data.quantity_ordered,
        status=ShopOrderStatus.PENDING,
        created_by=current_user.id,
    )
    db.add(shop_order)
    await db.commit()
    await db.refresh(shop_order)

    return {
        "success": True,
        "id": str(shop_order.id),
        "message": f"Order placed for {order_data.quantity_ordered} unit(s) of {product.name}"
    }


@router.get("/list")
async def get_shop_orders(
    search_string: Optional[str] = None,
    order_status: Optional[str] = None,
    page: int = 1,
    limit: int = 8,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """List placed shop orders with optional search/status filtering."""
    if page < 1:
        page = 1
    if limit <= 0 or limit > 100:
        limit = 8
    skip = (page - 1) * limit

    conditions = []
    if search_string and search_string.strip():
        pattern = f"%{search_string.strip()}%"
        conditions.append(or_(ShopOrder.product_name.ilike(pattern), ShopOrder.barcode.ilike(pattern)))

    if order_status:
        try:
            status_enum = ShopOrderStatus(order_status.upper())
            conditions.append(ShopOrder.status == status_enum)
        except ValueError:
            pass

    count_statement = select(func.count(ShopOrder.id))
    statement = select(ShopOrder)
    for condition in conditions:
        count_statement = count_statement.where(condition)
        statement = statement.where(condition)

    count_result = await db.execute(count_statement)
    total_count = count_result.scalar() or 0

    statement = statement.order_by(ShopOrder.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(statement)
    orders = result.scalars().all()

    data = [
        {
            "id": str(order.id),
            "product_name": order.product_name,
            "barcode": order.barcode or "",
            "category": order.category or "",
            "quantity_ordered": order.quantity_ordered,
            "status": order.status.value,
            "created_at": order.created_at.isoformat(),
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
            "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else None,
        }
        for order in orders
    ]

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    return {
        "data": data,
        "page": page,
        "limit": limit,
        "total": total_count,
        "total_pages": total_pages,
        "has_more": page < total_pages,
    }


@router.put("/update-status/{order_id}")
async def update_shop_order_status(
    order_id: str,
    request_data: dict,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Update the status of a placed shop order (PENDING, DELIVERED, CANCEL)."""
    try:
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format"
        )

    result = await db.execute(select(ShopOrder).where(ShopOrder.id == order_uuid))
    shop_order = result.scalar_one_or_none()
    if not shop_order:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Shop order not found"
        )

    new_status = request_data.get("status")
    if not new_status:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Status is required"
        )

    try:
        shop_order.status = ShopOrderStatus(new_status.upper())
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be one of: PENDING, DELIVERED, CANCEL"
        )

    now = datetime.now()
    if shop_order.status == ShopOrderStatus.DELIVERED:
        shop_order.delivered_at = now
    elif shop_order.status == ShopOrderStatus.CANCEL:
        shop_order.cancelled_at = now

    shop_order.updated_at = now
    await db.commit()
    await db.refresh(shop_order)

    return {
        "success": True,
        "id": str(shop_order.id),
        "status": shop_order.status.value,
        "delivered_at": shop_order.delivered_at.isoformat() if shop_order.delivered_at else None,
        "cancelled_at": shop_order.cancelled_at.isoformat() if shop_order.cancelled_at else None,
    }
