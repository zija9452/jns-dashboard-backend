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
from ..auth.rbac import admin_required

router = APIRouter()


@router.post("/refunds/walkin-invoice")
async def create_walkin_invoice_refund(
    request_data: dict,
    current_user: User = Depends(admin_required()),
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

    # Validate refund amount doesn't exceed amount paid
    if Decimal(str(refund_amount)) > invoice.amount_paid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund amount ({refund_amount}) exceeds amount paid ({float(invoice.amount_paid)})"
        )

    # Parse original invoice items to validate refund items
    original_items = []
    try:
        original_items = json.loads(invoice.items)
    except (json.JSONDecodeError, TypeError):
        original_items = []

    # Process each refunded item and update inventory
    for refund_item in refunded_items:
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
            # Increase stock level by the returned amount
            product.stock_level += quantity_returned
            await db.commit()

    # Generate unique refund number with database-level locking for concurrency safety
    # Use database advisory lock to prevent race conditions
    lock_result = await db.execute(select(func.pg_advisory_lock(123460)))

    try:
        # Find the highest refund number globally and increment the sequence
        prefix_pattern = "WRF-"  # Walk-in Refund prefix
        statement = select(func.max(Refund.refund_no)).where(
            Refund.refund_no.like(prefix_pattern)
        )
        result = await db.execute(statement)
        max_refund_no = result.scalar_one_or_none()

        if max_refund_no:
            # Extract the sequence number from existing format like "WRF-001"
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

        refund_no = f"WRF-{seq_number}"

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
                refund_no = f"WRF-{seq_number}"
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
            items=json.dumps(refunded_items),
            amount=Decimal(str(refund_amount)),
            reason=refund_reason,
            processed_by=current_user.id
        )

        # Add to database
        db.add(refund_obj)
        await db.commit()
        await db.refresh(refund_obj)

        # Update the original invoice's payment status and amounts
        # Calculate new amounts after refund
        remaining_amount_paid = invoice.amount_paid - Decimal(str(refund_amount))
        new_balance_due = invoice.balance_due + Decimal(str(refund_amount))  # Add refunded amount back to balance due

        # Update payment status based on remaining amount
        if float(remaining_amount_paid) <= 0 and float(invoice.total_amount) > 0:
            # If all paid amount is refunded but there was still a balance, status goes back to unpaid
            if float(new_balance_due) > 0:
                invoice.payment_status = "unpaid"
            else:
                invoice.payment_status = "refunded"
        elif remaining_amount_paid > 0:
            # Partial payment remains after refund
            invoice.payment_status = "partial"
        else:
            invoice.payment_status = "paid"  # If there was no payment to refund

        # Update invoice amounts
        invoice.amount_paid = remaining_amount_paid
        invoice.balance_due = new_balance_due
        invoice.updated_at = datetime.now()
        await db.commit()

        # Generate a PDF receipt as response
        pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 200
>>
stream
BT
/F1 16 Tf
72 750 Td
(Refund Receipt - {refund_no}) Tj
T* 15 -15 Td
(Invoice No: {invoice.invoice_no}) Tj
T* 15 -15 Td
(Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}) Tj
T* 15 -15 Td
(Refund Amount: ${refund_amount:.2f}) Tj
T* 15 -15 Td
(Reason: {refund_reason}) Tj
T* 15 -15 Td
(Processed by: {current_user.username or current_user.id}) Tj
ET
endstream
endobj
xref
0 5
trailer
<<
/Size 5
/Root 1 0 R
>>
%%EOF"""

        encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

        return encoded_pdf
    finally:
        # Release the advisory lock
        unlock_result = await db.execute(select(func.pg_advisory_unlock(123460)))


@router.get("/refunds/walkin-invoice/{refund_id}")
async def get_walkin_invoice_refund(
    refund_id: str,
    current_user: User = Depends(admin_required()),
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


@router.get("/refunds/walkin-invoice/daily/{date_str}")
async def get_daily_walkin_invoice_refunds(
    date_str: str,
    current_user: User = Depends(admin_required()),
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
            "refund_no": refund.refund_no,
            "invoice_id": str(refund.invoice_id),
            "customer_id": str(refund.customer_id) if refund.customer_id else None,
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
    current_user: User = Depends(admin_required()),
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


@router.get("/refunds/walkin-invoice/invoice/{invoice_id}")
async def get_refunds_for_walkin_invoice(
    invoice_id: str,
    current_user: User = Depends(admin_required()),
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
            "refund_no": rf.refund_no,
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