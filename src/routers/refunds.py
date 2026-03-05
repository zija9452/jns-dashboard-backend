from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Optional
from uuid import UUID
import uuid
import json
import base64
from datetime import datetime
from decimal import Decimal
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from ..database.database import get_db
from ..models.refund import Refund, RefundRead, RefundCreate, RefundUpdate
from ..models.invoice import Invoice
from ..models.product import Product
from ..models.customer import Customer
from ..models.user import User
from ..auth.rbac import admin_required

router = APIRouter()


@router.post("/refunds")
async def create_refund(
    refund_data: RefundCreate,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new refund for an existing invoice
    When a refund is processed, the refunded products are added back to inventory
    """
    from sqlalchemy import select
    from decimal import Decimal

    # Validate invoice exists
    try:
        invoice_uuid = UUID(refund_data.invoice_id)
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
    if refund_data.customer_id:
        try:
            customer_id_uuid = UUID(refund_data.customer_id)
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

    # Validate refund amount doesn't exceed amount paid
    if refund_data.amount > float(invoice.amount_paid):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund amount ({refund_data.amount}) exceeds amount paid ({float(invoice.amount_paid)})"
        )

    # Parse original invoice items to validate refund items
    original_items = []
    try:
        original_items = json.loads(invoice.items)
    except (json.JSONDecodeError, TypeError):
        original_items = []

    # Process each refunded item and update inventory
    for refund_item in refund_data.refunded_items:
        product_name = refund_item.get('product_name')
        quantity_returned = int(refund_item.get('quantity_returned', 0))

        if quantity_returned <= 0:
            continue  # Skip items with zero or negative quantity

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

        # Update product inventory (add back the returned quantity)
        product_result = await db.execute(select(Product).where(Product.name == product_name))
        product = product_result.scalar_one_or_none()

        if product:
            # Increase stock quantity by the returned amount
            new_stock_quantity = product.stock_quantity + quantity_returned
            product.stock_quantity = new_stock_quantity
            db.add(product)

    # Generate unique refund number with database-level locking for concurrency safety
    from sqlalchemy import func

    # Use database advisory lock to prevent race conditions
    lock_result = await db.execute(select(func.pg_advisory_lock(123458)))

    try:
        # Find the highest refund number globally and increment the sequence
        prefix_pattern = "REF-%"
        statement = select(func.max(Refund.refund_no)).where(
            Refund.refund_no.like(prefix_pattern)
        )
        result = await db.execute(statement)
        max_refund_no = result.scalar_one_or_none()

        if max_refund_no:
            # Extract the sequence number from existing format like "REF-001"
            try:
                parts = max_refund_no.split("-")
                if len(parts) >= 2:
                    existing_seq = parts[-1]  # Get the last part (sequence number)
                    if existing_seq.isdigit():
                        next_seq = int(existing_seq) + 1
                        seq_number = f"{next_seq:03d}"  # Format as 3-digit sequence (001, 002, etc.)
                    else:
                        seq_number = "001"  # Default if parsing fails
                else:
                    seq_number = "001"  # Default if format doesn't match expected pattern
            except:
                seq_number = "001"  # Default if any error
        else:
            seq_number = "001"  # Start with 001 if no refunds exist

        refund_no = f"REF-{seq_number}"

        # Double-check for uniqueness in case of race conditions and increment if needed
        counter = 0
        while counter < 100:  # Safety check to avoid infinite loop
            check_statement = select(Refund).where(Refund.refund_no == refund_no)
            check_result = await db.execute(check_statement)
            existing_refund = check_result.scalar_one_or_none()

            if existing_refund:
                # Refund number exists, increment and try again
                next_seq_int = int(seq_number) + 1
                seq_number = f"{next_seq_int:03d}"
                refund_no = f"REF-{seq_number}"
                counter += 1
            else:
                break  # Found a unique number

        if counter >= 100:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate unique refund number"
            )

        # Create refund object
        refund_obj = Refund(
            refund_no=refund_no,
            invoice_id=invoice_uuid,
            customer_id=customer_id_uuid,
            items=json.dumps(refund_data.refunded_items),
            amount=Decimal(str(refund_data.amount)),
            reason=refund_data.reason,
            processed_by=current_user.id
        )

        # Add to database
        db.add(refund_obj)
        await db.commit()
        await db.refresh(refund_obj)

        # Update the original invoice's payment status and amounts
        # Calculate new amounts after refund
        remaining_amount_paid = invoice.amount_paid - Decimal(str(refund_data.amount))

        # Update payment status based on remaining amount
        if float(remaining_amount_paid) <= 0 and float(invoice.total_amount) > 0:
            # If all paid amount is refunded, mark as refunded
            invoice.payment_status = "refunded"
        elif remaining_amount_paid > 0:
            # Partial payment remains after refund
            invoice.payment_status = "partial"
        else:
            invoice.payment_status = "paid"  # If there was no payment to refund

        # Update invoice amounts
        invoice.amount_paid = remaining_amount_paid
        invoice.updated_at = datetime.now()

        await db.commit()

        # Generate a simple PDF report as response
        pdf_content = "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        pdf_content += "2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
        pdf_content += "3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
        pdf_content += "4 0 obj\n<<\n/Length 60\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Refund Receipt - " + refund_no + ") Tj\nET\nendstream\nendobj\n"
        pdf_content += "xref\n0 5\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n%%EOF"

        encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

        return encoded_pdf
    finally:
        # Release the advisory lock
        unlock_result = await db.execute(select(func.pg_advisory_unlock(123458)))


@router.get("/refunds/{refund_id}")
async def get_refund(
    refund_id: str,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific refund by ID
    """
    try:
        refund_uuid = UUID(refund_id)
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
        "refund_no": refund.refund_no,
        "invoice_id": str(refund.invoice_id),
        "customer_id": str(refund.customer_id) if refund.customer_id else None,
        "refunded_items": refunded_items,
        "refund_amount": float(refund.amount),
        "refund_reason": refund.reason,
        "processed_by": str(refund.processed_by),
        "created_at": refund.created_at.isoformat(),
        "updated_at": refund.updated_at.isoformat()
    }


@router.put("/refunds/{refund_id}")
async def update_refund(
    refund_id: str,
    refund_update: RefundUpdate,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update existing refund
    """
    try:
        refund_uuid = UUID(refund_id)
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

    # Update fields if provided
    update_data = refund_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(refund, field):
            setattr(refund, field, value)

    # Update timestamp
    refund.updated_at = datetime.now()

    await db.commit()
    await db.refresh(refund)

    return {
        "success": True,
        "message": "Refund updated successfully",
        "refund_id": str(refund.id)
    }


@router.delete("/refunds/{refund_id}")
async def delete_refund(
    refund_id: str,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete refund by ID
    """
    try:
        refund_uuid = UUID(refund_id)
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

    await db.delete(refund)
    await db.commit()

    return {
        "success": True,
        "message": "Refund deleted successfully"
    }


@router.get("/refunds")
async def get_refunds(
    limit: int = Query(100, ge=1, le=200),
    skip: int = Query(0, ge=0),
    customer_id: str = Query(None),
    invoice_id: str = Query(None),
    date: str = Query(None),
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of refunds with optional filtering
    """
    statement = select(Refund)

    # Apply filters
    if customer_id:
        try:
            customer_uuid = UUID(customer_id)
            statement = statement.where(Refund.customer_id == customer_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid customer ID format"
            )

    if invoice_id:
        try:
            invoice_uuid = UUID(invoice_id)
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
            "refund_no": rf.refund_no,
            "invoice_id": str(rf.invoice_id),
            "customer_id": str(rf.customer_id) if rf.customer_id else None,
            "refunded_items": items_data,
            "refund_amount": float(rf.amount),
            "refund_reason": rf.reason,
            "processed_by": str(rf.processed_by),
            "created_at": rf.created_at.isoformat(),
            "updated_at": rf.updated_at.isoformat()
        })

    return refund_list


@router.get("/refunds/daily-refunds/{date}")
async def get_daily_refunds(
    date: str,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all refunds processed on a specific date with totals
    """
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
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
            "refund_no": refund.refund_no,
            "invoice_id": str(refund.invoice_id),
            "customer_id": str(refund.customer_id) if refund.customer_id else None,
            "refunded_items": items_data,
            "refund_amount": float(refund.amount),
            "refund_reason": refund.reason,
            "created_at": refund.created_at.isoformat()
        })

        total_refund_amount += float(refund.amount)

    return {
        "date": date,
        "total_refunds": refund_count,
        "total_refund_amount": total_refund_amount,
        "refunds": refund_list
    }