from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_
from typing import Optional
from uuid import UUID
from datetime import datetime

from ..database.database import get_db
from ..models.user import User
from ..models.product import Product
from ..models.shop_order import ShopOrder, ShopOrderStatus, ShopOrderCreate, ShopOrderApprovalStatus, ShopOrderReview, ShopOrderSeenByRole
from ..auth.session_auth import employee_required_from_session, strict_admin_required_from_session
from ..utils.firestore_signals import publish_signal

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
        note=order_data.note.strip() if order_data.note and order_data.note.strip() else None,
        status=ShopOrderStatus.PENDING,
        approval_status=ShopOrderApprovalStatus.PENDING_APPROVAL,
        created_by=current_user.id,
    )
    db.add(shop_order)
    await db.commit()
    await db.refresh(shop_order)

    await publish_signal("shop_order_approval")

    return {
        "success": True,
        "id": str(shop_order.id),
        "message": f"Order request sent for approval: {order_data.quantity_ordered} unit(s) of {product.name}"
    }


@router.get("/unseen-count")
async def get_unseen_shop_orders_count(
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Count of newly-approved shop orders not yet viewed by the current user's
    role on the Shop Orders page. Tracked per role so an employee opening the
    page doesn't clear the badge for admins/cashiers, and vice versa."""
    seen_subquery = select(ShopOrderSeenByRole.order_id).where(
        ShopOrderSeenByRole.role == current_user.role.name
    )
    statement = select(func.count(ShopOrder.id)).where(
        ShopOrder.approval_status == ShopOrderApprovalStatus.APPROVED,
        ShopOrder.id.notin_(seen_subquery),
    )
    result = await db.execute(statement)
    return {"count": result.scalar() or 0}


@router.post("/mark-seen")
async def mark_shop_orders_seen(
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Mark all currently-approved shop orders as seen by the current user's
    role (clears the Shop Orders badge only for that role)."""
    role = current_user.role.name
    seen_subquery = select(ShopOrderSeenByRole.order_id).where(ShopOrderSeenByRole.role == role)
    statement = select(ShopOrder.id).where(
        ShopOrder.approval_status == ShopOrderApprovalStatus.APPROVED,
        ShopOrder.id.notin_(seen_subquery),
    )
    result = await db.execute(statement)
    order_ids = result.scalars().all()
    for order_id in order_ids:
        db.add(ShopOrderSeenByRole(order_id=order_id, role=role))

    await db.commit()

    if order_ids:
        # Tell every other browser with this badge open to recount too, so
        # someone viewing Shop Orders on one PC clears it for their role
        # everywhere - not just on the PC that just marked them seen. Each
        # browser recomputes its own role's count, so this is harmless for
        # roles unaffected by this mark-seen call.
        await publish_signal("shop_order_updates")

    return {"success": True, "marked": len(order_ids)}


@router.get("/approval/list")
async def get_approval_orders(
    filter: str = "pending",
    search_string: Optional[str] = None,
    page: int = 1,
    limit: int = 8,
    current_user: User = Depends(strict_admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """List orders awaiting approval, or previously rejected orders, for the admin review screen."""
    if page < 1:
        page = 1
    if limit <= 0 or limit > 100:
        limit = 8
    skip = (page - 1) * limit

    target_status_map = {
        "pending": ShopOrderApprovalStatus.PENDING_APPROVAL,
        "approved": ShopOrderApprovalStatus.APPROVED,
        "rejected": ShopOrderApprovalStatus.REJECTED,
    }

    conditions = []
    if filter != "all":
        target_status = target_status_map.get(filter, ShopOrderApprovalStatus.PENDING_APPROVAL)
        conditions.append(ShopOrder.approval_status == target_status)
    if search_string and search_string.strip():
        pattern = f"%{search_string.strip()}%"
        conditions.append(or_(ShopOrder.product_name.ilike(pattern), ShopOrder.barcode.ilike(pattern)))

    count_statement = select(func.count(ShopOrder.id))
    statement = select(ShopOrder, Product.stock_level).outerjoin(Product, ShopOrder.product_id == Product.id)
    for condition in conditions:
        count_statement = count_statement.where(condition)
        statement = statement.where(condition)

    count_result = await db.execute(count_statement)
    total_count = count_result.scalar() or 0

    statement = statement.order_by(ShopOrder.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(statement)
    rows = result.all()

    data = [
        {
            "id": str(order.id),
            "product_name": order.product_name,
            "barcode": order.barcode or "",
            "category": order.category or "",
            "quantity_ordered": order.quantity_ordered,
            "note": order.note or "",
            "current_stock": current_stock if current_stock is not None else order.stock_at_order_time,
            "approval_status": order.approval_status.value,
            "created_at": order.created_at.isoformat(),
            "approved_at": order.approved_at.isoformat() if order.approved_at else None,
            "rejected_at": order.rejected_at.isoformat() if order.rejected_at else None,
        }
        for order, current_stock in rows
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


@router.get("/approval/count")
async def get_pending_approval_count(
    current_user: User = Depends(strict_admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Unseen count for the sidebar notification badge."""
    statement = select(func.count(ShopOrder.id)).where(
        ShopOrder.approval_status == ShopOrderApprovalStatus.PENDING_APPROVAL,
        ShopOrder.seen_by_admin == False,  # noqa: E712
    )
    result = await db.execute(statement)
    return {"count": result.scalar() or 0}


@router.post("/approval/mark-seen")
async def mark_approval_seen(
    current_user: User = Depends(strict_admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Clear the sidebar badge by marking currently pending orders as seen."""
    statement = select(ShopOrder).where(
        ShopOrder.approval_status == ShopOrderApprovalStatus.PENDING_APPROVAL,
        ShopOrder.seen_by_admin == False,  # noqa: E712
    )
    result = await db.execute(statement)
    orders = result.scalars().all()
    for order in orders:
        order.seen_by_admin = True

    await db.commit()

    if orders:
        # Tell every other admin browser with this badge open to recount too,
        # so one admin opening the page clears it everywhere - not just on
        # the PC that just marked them seen.
        await publish_signal("shop_order_approval")

    return {"success": True, "marked": len(orders)}


@router.put("/approval/{order_id}")
async def review_shop_order(
    order_id: str,
    review: ShopOrderReview,
    current_user: User = Depends(strict_admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Approve or reject an order that is awaiting approval."""
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

    if shop_order.approval_status != ShopOrderApprovalStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="This order has already been reviewed"
        )

    action = (review.action or "").lower()
    if action not in ("approve", "reject"):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Action must be 'approve' or 'reject'"
        )

    now = datetime.now()
    if action == "approve":
        shop_order.approval_status = ShopOrderApprovalStatus.APPROVED
        shop_order.approved_by = current_user.id
        shop_order.approved_at = now
    else:
        shop_order.approval_status = ShopOrderApprovalStatus.REJECTED
        shop_order.rejected_at = now

    shop_order.seen_by_admin = True
    shop_order.updated_at = now
    await db.commit()
    await db.refresh(shop_order)

    # This order just left the pending count - tell every admin browser
    # (not just the one that clicked) to recount its badge/list.
    await publish_signal("shop_order_approval")

    if action == "approve":
        await publish_signal("shop_order_updates")

    return {
        "success": True,
        "id": str(shop_order.id),
        "approval_status": shop_order.approval_status.value,
    }


@router.get("/list")
async def get_shop_orders(
    search_string: Optional[str] = None,
    order_status: Optional[str] = None,
    include_stats: bool = Query(False),
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

    conditions = [ShopOrder.approval_status == ShopOrderApprovalStatus.APPROVED]
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
    statement = select(ShopOrder, Product.stock_level).outerjoin(Product, ShopOrder.product_id == Product.id)
    for condition in conditions:
        count_statement = count_statement.where(condition)
        statement = statement.where(condition)

    count_result = await db.execute(count_statement)
    total_count = count_result.scalar() or 0

    statement = statement.order_by(ShopOrder.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(statement)
    rows = result.all()

    data = [
        {
            "id": str(order.id),
            "product_name": order.product_name,
            "barcode": order.barcode or "",
            "category": order.category or "",
            "quantity_ordered": order.quantity_ordered,
            "note": order.note or "",
            "current_stock": current_stock if current_stock is not None else order.stock_at_order_time,
            "status": order.status.value,
            "created_at": order.created_at.isoformat(),
            "in_production_at": order.in_production_at.isoformat() if order.in_production_at else None,
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
            "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else None,
        }
        for order, current_stock in rows
    ]

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    # Optional heavy stats calculation - only performed if include_stats is True.
    # Mirrors the pending stats on the customer orders page (pending_invoices_count / total_pending_quantity).
    pending_stats = {"pending_orders_count": 0, "total_pending_quantity": 0}

    if include_stats:
        pending_conditions = [
            ShopOrder.approval_status == ShopOrderApprovalStatus.APPROVED,
            ShopOrder.status == ShopOrderStatus.PENDING,
        ]

        pending_count_stmt = select(func.count(ShopOrder.id))
        pending_quantity_stmt = select(func.coalesce(func.sum(ShopOrder.quantity_ordered), 0))
        for condition in pending_conditions:
            pending_count_stmt = pending_count_stmt.where(condition)
            pending_quantity_stmt = pending_quantity_stmt.where(condition)

        pending_count_result = await db.execute(pending_count_stmt)
        pending_quantity_result = await db.execute(pending_quantity_stmt)

        pending_stats = {
            "pending_orders_count": pending_count_result.scalar() or 0,
            "total_pending_quantity": pending_quantity_result.scalar() or 0,
        }

    return {
        "data": data,
        "page": page,
        "limit": limit,
        "total": total_count,
        "total_pages": total_pages,
        "has_more": page < total_pages,
        "pending_stats": pending_stats,
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
            detail="Invalid status. Must be one of: PENDING, IN_PRODUCTION, DELIVERED, CANCEL"
        )

    now = datetime.now()
    if shop_order.status == ShopOrderStatus.IN_PRODUCTION:
        shop_order.in_production_at = now
    elif shop_order.status == ShopOrderStatus.DELIVERED:
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
        "in_production_at": shop_order.in_production_at.isoformat() if shop_order.in_production_at else None,
        "delivered_at": shop_order.delivered_at.isoformat() if shop_order.delivered_at else None,
        "cancelled_at": shop_order.cancelled_at.isoformat() if shop_order.cancelled_at else None,
    }
