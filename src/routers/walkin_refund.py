from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Optional
import uuid
import json
import base64
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import select, func
import logging

from ..database.database import get_db
from ..models.refund import Refund, RefundRead, RefundCreate, RefundUpdate
from ..models.invoice import Invoice
from ..models.product import Product
from ..models.customer import Customer
from ..models.user import User
from ..auth.session_auth import get_current_user_from_session, admin_required_from_session, cashier_required_from_session, employee_required_from_session, admin_cashier_employee_required_from_session

router = APIRouter()


@router.post("/refunds/walkin-invoice")
async def create_walkin_invoice_refund(
    request_data: dict,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a refund for a walk-in invoice
    When a refund is processed, the refunded products are added back to inventory
    """
    # Extract data from request body
    invoice_id = request_data.get('invoice_id')
    refunded_items = request_data.get('refunded_items', [])
    refund_amount = request_data.get('amount', 0.0)
    refund_reason = request_data.get('reason', '')
    customer_id = request_data.get('customer_id')  # Optional

    # Validate required fields
    if not invoice_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice ID is required"
        )

    if not refunded_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refunded items are required"
        )

    # Validate invoice exists
    try:
        invoice_uuid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    invoice_result = await db.execute(select(Invoice).where(Invoice.id == invoice_uuid))
    invoice = invoice_result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Validate customer exists if provided
    customer_id_uuid = None
    if customer_id:
        try:
            customer_id_uuid = uuid.UUID(customer_id)
            customer_result = await db.execute(select(Customer).where(Customer.id == customer_id_uuid))
            customer = customer_result.scalar_one_or_none()
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Customer not found"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid customer ID format"
            )

    # Validate refund amount doesn't exceed the item's total price
    # Get the total price of the refunded items
    total_refund_items_price = sum(
        item.get('quantity_returned', 0) * item.get('unit_price', 0) 
        for item in refunded_items
    )
    
    if Decimal(str(refund_amount)) > Decimal(str(total_refund_items_price)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund amount ({refund_amount}) exceeds the total price of refunded items ({total_refund_items_price})."
        )

    # Check if invoice is already fully refunded
    if invoice.payment_status == 'refunded':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invoice has already been fully refunded."
        )

    # Parse original invoice items to validate refund items
    original_items = []
    try:
        original_items = json.loads(invoice.items)
    except (json.JSONDecodeError, TypeError):
        original_items = []

    # Get all previous refunds for this invoice to calculate already refunded quantities
    from ..models.refund import Refund
    
    refunds_statement = select(Refund).where(Refund.invoice_id == invoice_uuid).order_by(Refund.created_at.desc())
    refunds_result = await db.execute(refunds_statement)
    previous_refunds = refunds_result.scalars().all()
    
    # Calculate already refunded quantities per product
    already_refunded_qty = {}
    for refund in previous_refunds:
        try:
            refund_items = json.loads(refund.items)
            for item in refund_items:
                product_name = item.get('product_name')
                qty_returned = item.get('quantity_returned', 0)
                if product_name in already_refunded_qty:
                    already_refunded_qty[product_name] += qty_returned
                else:
                    already_refunded_qty[product_name] = qty_returned
        except:
            pass
    
    # Validate each refunded item
    for refund_item in refunded_items:
        product_name = refund_item.get('product_name')
        quantity_returned = int(refund_item.get('quantity_returned', 0))

        if quantity_returned <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Quantity for product '{product_name}' must be positive"
            )

        # Find the product in the original invoice
        original_item = None
        for item in original_items:
            if item.get('product_name') == product_name:
                original_item = item
                break

        if not original_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product '{product_name}' not found in original invoice"
            )

        # Check original quantity
        original_qty = int(original_item.get('quantity', 0))
        
        # Check if already refunded
        already_refunded = already_refunded_qty.get(product_name, 0)
        remaining_qty = original_qty - already_refunded
        
        if remaining_qty <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Already refunded! Product '{product_name}' was fully refunded. Original qty: {original_qty}, Already refunded: {already_refunded}"
            )
        
        if quantity_returned > remaining_qty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot refund {quantity_returned} of '{product_name}'. Only {remaining_qty} remaining (Original: {original_qty}, Already refunded: {already_refunded})"
            )

        # Update product inventory (add back the returned quantity)
        product_result = await db.execute(select(Product).where(Product.name == product_name))
        product = product_result.scalar_one_or_none()

        if product:
            # Increase stock level by the returned amount
            product.stock_level += quantity_returned
            await db.commit()

    # Create refund object
    refund_obj = Refund(
        invoice_id=invoice_uuid,
        items=json.dumps(refunded_items),
        amount=Decimal(str(refund_amount)),
        reason=refund_reason,
        processed_by=current_user.id
    )

    # Add to database
    db.add(refund_obj)
    await db.commit()
    await db.refresh(refund_obj)

    # Update the original invoice's payment status
    # Note: We don't reduce amount_paid as it represents the original payment
    # Just update the status based on remaining inventory
    
    # Check if all items have been refunded (compare stock levels)
    # For now, just mark as partial if there was a partial refund
    if invoice.payment_status != 'refunded':
        invoice.payment_status = 'partial'
    
    invoice.updated_at = datetime.now()
    await db.commit()

    # Return success message instead of PDF
    return {
        "success": True,
        "message": "Refund processed successfully",
        "refund_id": str(refund_obj.id),
        "invoice_id": str(invoice_uuid),
        "refunded_amount": float(refund_amount)
    }


@router.get("/refunds/walkin-invoice/{refund_id}")
async def get_walkin_invoice_refund(
    refund_id: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific walk-in invoice refund by ID
    """
    try:
        refund_uuid = uuid.UUID(refund_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refund ID format"
        )

    statement = select(Refund).where(Refund.id == refund_uuid)
    result = await db.execute(statement)
    refund = result.scalar_one_or_none()

    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )

    # Parse JSON fields for response
    try:
        refunded_items = json.loads(refund.items)
    except:
        refunded_items = []

    return {
        "refund_id": str(refund.id),
        "invoice_id": str(refund.invoice_id),
        "refunded_items": refunded_items,
        "refund_amount": float(refund.amount),
        "refund_reason": refund.reason,
        "processed_by": str(refund.processed_by),
        "created_at": refund.created_at.isoformat(),
        "updated_at": refund.updated_at.isoformat()
    }


@router.get("/refunds/walkin-invoice/daily/{date_str}")
async def get_daily_walkin_invoice_refunds(
    date_str: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all walk-in invoice refunds processed on a specific date with totals
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD."
        )

    # Query refunds created on the specific date
    statement = select(Refund).where(
        func.date(Refund.created_at) == target_date
    )

    result = await db.execute(statement)
    refunds = result.scalars().all()

    # Calculate total refund amounts
    total_refund_amount = 0.0
    refund_count = len(refunds)

    refund_list = []
    for refund in refunds:
        try:
            items_data = json.loads(refund.items)
        except:
            items_data = []

        refund_list.append({
            "refund_id": str(refund.id),
            "invoice_id": str(refund.invoice_id),
            "refunded_items": items_data,
            "refund_amount": float(refund.amount),
            "refund_reason": refund.reason,
            "processed_by": str(refund.processed_by),
            "created_at": refund.created_at.isoformat()
        })

        total_refund_amount += float(refund.amount)

    return {
        "date": date_str,
        "total_refunds": refund_count,
        "total_refund_amount": total_refund_amount,
        "refunds": refund_list
    }


@router.get("/refunds/walkin-invoice")
async def get_walkin_invoice_refunds(
    limit: int = Query(100, ge=1, le=200),
    skip: int = Query(0, ge=0),
    customer_id: str = Query(None),
    invoice_id: str = Query(None),
    date: str = Query(None),
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of walk-in invoice refunds with optional filtering
    """
    statement = select(Refund)

    # Apply filters
    if customer_id:
        try:
            customer_uuid = uuid.UUID(customer_id)
            statement = statement.where(Refund.customer_id == customer_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid customer ID format"
            )

    if invoice_id:
        try:
            invoice_uuid = uuid.UUID(invoice_id)
            statement = statement.where(Refund.invoice_id == invoice_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid invoice ID format"
            )

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            statement = statement.where(func.date(Refund.created_at) == target_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD."
            )

    # Apply pagination and ordering
    statement = statement.offset(skip).limit(limit).order_by(Refund.created_at.desc())

    result = await db.execute(statement)
    refunds = result.scalars().all()

    refund_list = []
    for rf in refunds:
        try:
            items_data = json.loads(rf.items)
        except:
            items_data = []

        refund_list.append({
            "refund_id": str(rf.id),
            "invoice_id": str(rf.invoice_id),
            "refunded_items": items_data,
            "refund_amount": float(rf.amount),
            "refund_reason": rf.reason,
            "processed_by": str(rf.processed_by),
            "created_at": rf.created_at.isoformat(),
            "updated_at": rf.updated_at.isoformat()
        })

    return refund_list


@router.get("/refunds/walkin-invoice/invoice/{invoice_id}")
async def get_refunds_for_walkin_invoice(
    invoice_id: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all refunds for a specific walk-in invoice
    """
    try:
        invoice_uuid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    statement = select(Refund).where(Refund.invoice_id == invoice_uuid).order_by(Refund.created_at.desc())
    result = await db.execute(statement)
    refunds = result.scalars().all()

    refund_list = []
    total_refund_amount = 0.0

    for rf in refunds:
        try:
            items_data = json.loads(rf.items)
        except:
            items_data = []

        refund_list.append({
            "refund_id": str(rf.id),
            "invoice_id": str(rf.invoice_id),
            "refunded_items": items_data,
            "refund_amount": float(rf.amount),
            "refund_reason": rf.reason,
            "processed_by": str(rf.processed_by),
            "created_at": rf.created_at.isoformat()
        })

        total_refund_amount += float(rf.amount)

    return {
        "invoice_id": invoice_id,
        "refunds": refund_list,
        "total_refund_amount": total_refund_amount,
        "refund_count": len(refund_list)
    }


@router.put("/refunds/walkin-invoice/{refund_id}")
async def update_walkin_invoice_refund(
    refund_id: str,
    refund_update: RefundUpdate,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific walk-in invoice refund
    Allows updating refund details including date and amount
    """
    from uuid import UUID
    from sqlalchemy import select
    from ..models.refund import Refund
    
    try:
        refund_uuid = UUID(refund_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refund ID format"
        )

    # Get the existing refund
    statement = select(Refund).where(Refund.id == refund_uuid)
    result = await db.execute(statement)
    refund = result.scalar_one_or_none()

    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )

    # Update fields if provided
    update_data = refund_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(refund, field):
            setattr(refund, field, value)

    # Update the timestamp
    refund.updated_at = datetime.now()

    await db.commit()
    await db.refresh(refund)

    return {
        "success": True,
        "message": "Refund updated successfully",
        "refund_id": str(refund.id)
    }


@router.delete("/refunds/walkin-invoice/{refund_id}")
async def delete_walkin_invoice_refund(
    refund_id: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific walk-in invoice refund
    Also restores the inventory quantities that were refunded
    """
    from uuid import UUID
    from sqlalchemy import select
    from ..models.refund import Refund
    from ..models.product import Product
    
    try:
        refund_uuid = UUID(refund_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refund ID format"
        )

    # Get the existing refund
    statement = select(Refund).where(Refund.id == refund_uuid)
    result = await db.execute(statement)
    refund = result.scalar_one_or_none()

    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )

    # Parse refunded items to restore inventory
    try:
        refunded_items = json.loads(refund.items)
        for item in refunded_items:
            product_name = item.get('product_name')
            quantity_returned = item.get('quantity_returned', 0)
            
            if product_name and quantity_returned:
                # Find and update the product
                product_result = await db.execute(
                    select(Product).where(Product.name == product_name)
                )
                product = product_result.scalar_one_or_none()

                if product:
                    # Reduce stock level by the refunded amount (since refund meant adding back to stock)
                    # If we're deleting the refund, we need to remove those items from stock again
                    product.stock_level -= quantity_returned
                    if product.stock_level < 0:
                        product.stock_level = 0  # Don't allow negative stock
    except Exception as e:
        # If there's an error parsing items or updating inventory, continue with deletion
        pass

    # Delete the refund
    await db.delete(refund)
    await db.commit()

    return {
        "success": True,
        "message": "Refund deleted successfully",
        "refund_id": str(refund.id)
    }