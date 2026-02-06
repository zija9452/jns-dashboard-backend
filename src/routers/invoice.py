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
from ..models.invoice import Invoice, InvoiceRead, InvoiceCreate, InvoiceUpdate, InvoiceStatus
from ..models.product import Product
from ..models.customer import Customer
from ..models.salesman import Salesman
from ..models.user import User
from ..auth.auth import admin_required

router = APIRouter()


@router.post("/invoices")
async def create_invoice(
    invoice_data: InvoiceCreate,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new invoice for walk-in customer with immediate payment
    All products selected and paid in full at time of purchase
    """
    from sqlalchemy import select
    from decimal import Decimal
    from pydantic import ValidationError

    # Validate that order items exist
    if not invoice_data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order items are required"
        )

    # Validate customer exists if provided
    customer_id_uuid = None
    if invoice_data.customer_id:
        try:
            customer_id_uuid = UUID(invoice_data.customer_id)
            # Verify customer exists
            from ..models.customer import Customer
            customer_exists = await db.execute(select(Customer).where(Customer.id == customer_id_uuid))
            customer = customer_exists.scalar_one_or_none()
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

    # Validate salesman exists if provided
    salesman_id_uuid = None
    if invoice_data.salesman_id:
        try:
            salesman_id_uuid = UUID(invoice_data.salesman_id)
            # Verify salesman exists
            from ..models.salesman import Salesman
            salesman_exists = await db.execute(select(Salesman).where(Salesman.id == salesman_id_uuid))
            salesman = salesman_exists.scalar_one_or_none()
            if not salesman:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Salesman not found"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid salesman ID format"
            )

    # Process each order item and update inventory
    items_list = []
    total_amount = Decimal('0')
    total_discount = 0.0

    # Parse items from the request
    try:
        items_data = json.loads(invoice_data.items)
    except (json.JSONDecodeError, TypeError):
        items_data = []

    for item in items_data:
        try:
            # Validate required fields
            pro_name = item.get('pro_name')
            if not pro_name:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product name is required for each item"
                )

            quantity = int(item.get('pro_quantity', 0))
            if quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Product quantity must be positive"
                )

            unit_price = float(item.get('unit_price', 0))
            if unit_price < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Unit price cannot be negative"
                )

            discount = float(item.get('discount', 0))
            if discount < 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Discount cannot be negative"
                )

            # Calculate total for this item
            item_total = (quantity * unit_price) - discount
            if item_total < 0:
                item_total = 0  # Prevent negative totals

            # Create item object
            item_obj = {
                "product_name": str(pro_name),
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": item_total,
                "discount": discount,
                "cat_name": str(item.get('cat_name', '')),
                "cricktshirt_Neckstyle": str(item.get('cricktshirt_Neckstyle', '')),
                "cricktshirt_sleeve": str(item.get('cricktshirt_sleeve', '')),
                "cricktshirt_bottom": str(item.get('cricktshirt_bottom', '')),
                "cricktshirt_fabric": str(item.get('cricktshirt_fabric', '')),
                "cricktrouser_style": str(item.get('cricktrouser_style', '')),
                "cricktrouser_style2": str(item.get('cricktrouser_style2', '')),
                "cricktrouser_bottom": str(item.get('cricktrouser_bottom', '')),
                "cricktrouser_pocket": str(item.get('cricktrouser_pocket', '')),
                "cricktrouser_fabric": str(item.get('cricktrouser_fabric', '')),
                "foottshirt_neckstyle": str(item.get('foottshirt_neckstyle', '')),
                "foottshirt_sleeves": str(item.get('foottshirt_sleeves', '')),
                "football_fabric": str(item.get('football_fabric', '')),
                "footshorts_style": str(item.get('footshorts_style', '')),
                "footshorts_pocket": str(item.get('footshorts_pocket', '')),
                "footballshort_fabric": str(item.get('footballshort_fabric', '')),
                "trackjack_style": str(item.get('trackjack_style', '')),
                "trackjack_waist": str(item.get('trackjack_waist', '')),
                "trackjack_pocket": str(item.get('trackjack_pocket', '')),
                "trackjack_bottom": str(item.get('trackjack_bottom', '')),
                "trackjack_fabric": str(item.get('trackjack_fabric', '')),
                "tracktrous_style": str(item.get('tracktrous_style', '')),
                "tracktrous_bottom": str(item.get('tracktrous_bottom', '')),
                "tracktrous_pocket": str(item.get('tracktrous_pocket', '')),
                "tracktrous_fabric": str(item.get('tracktrous_fabric', '')),
                "imgfile": str(item.get('imgfile', '')),
                "imgfile2": str(item.get('imgfile2', '')),
                "imgfile3": str(item.get('imgfile3', ''))
            }
            items_list.append(item_obj)
            total_amount += Decimal(str(item_total))
            total_discount += discount

            # Update product inventory - decrease stock by the sold quantity
            product_result = await db.execute(select(Product).where(Product.name == pro_name))
            product = product_result.scalar_one_or_none()

            if product:
                # Decrease stock quantity by the sold amount
                new_stock_quantity = product.stock_quantity - quantity
                if new_stock_quantity < 0:
                    new_stock_quantity = 0  # Don't allow negative stock
                product.stock_quantity = new_stock_quantity
                db.add(product)

        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data format in order item: {str(e)}"
            )

    # Validate payment amounts for immediate payment
    if invoice_data.amount_paid != total_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"For immediate payment invoices, amount paid ({invoice_data.amount_paid}) must equal total amount ({total_amount})"
        )

    if invoice_data.balance_due != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="For immediate payment invoices, balance due must be 0"
        )

    # Generate unique invoice number with database-level locking for concurrency safety
    from sqlalchemy import func

    # Use database advisory lock to prevent race conditions
    lock_result = await db.execute(select(func.pg_advisory_lock(123457)))

    try:
        # Find the highest invoice number globally and increment the sequence
        prefix_pattern = "INV-%"
        statement = select(func.max(Invoice.invoice_no)).where(
            Invoice.invoice_no.like(prefix_pattern)
        )
        result = await db.execute(statement)
        max_invoice_no = result.scalar_one_or_none()

        if max_invoice_no:
            # Extract the sequence number from existing format like "INV-001"
            try:
                parts = max_invoice_no.split("-")
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
            seq_number = "001"  # Start with 001 if no invoices exist

        invoice_no = f"INV-{seq_number}"

        # Double-check for uniqueness in case of race conditions and increment if needed
        counter = 0
        while counter < 100:  # Safety check to avoid infinite loop
            check_statement = select(Invoice).where(Invoice.invoice_no == invoice_no)
            check_result = await db.execute(check_statement)
            existing_invoice = check_result.scalar_one_or_none()

            if existing_invoice:
                # Invoice number exists, increment and try again
                next_seq_int = int(seq_number) + 1
                seq_number = f"{next_seq_int:03d}"
                invoice_no = f"INV-{seq_number}"
                counter += 1
            else:
                break  # Found a unique number

        if counter >= 100:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate unique invoice number"
            )

        # Create invoice object
        invoice_obj = Invoice(
            invoice_no=invoice_no,
            customer_id=customer_id_uuid,
            salesman_id=salesman_id_uuid,
            items=json.dumps(items_list),
            totals=json.dumps({
                "subtotal": float(total_amount),
                "tax": 0.0,
                "discount": total_discount,
                "total": float(total_amount),
                "amount_paid": float(invoice_data.amount_paid),
                "balance_due": 0.0,  # Always 0 for immediate payment
                "payment_status": "paid"  # Always "paid" for immediate payment
            }),
            total_amount=Decimal(str(total_amount)),
            amount_paid=Decimal(str(invoice_data.amount_paid)),
            balance_due=Decimal('0'),  # Always 0 for immediate payment
            payment_status="paid",  # Always "paid" for immediate payment
            payments_history=json.dumps([{
                "amount": float(invoice_data.amount_paid),
                "payment_method": invoice_data.payment_method,
                "date": datetime.now().isoformat(),
                "description": "Full payment at invoice creation"
            }]),
            taxes=Decimal(str(invoice_data.taxes)),
            discounts=Decimal(str(total_discount)),
            status=InvoiceStatus.ISSUED,
            payment_method=invoice_data.payment_method,
            notes=invoice_data.notes,
            created_by=current_user.id
        )

        # Add to database
        db.add(invoice_obj)
        await db.commit()
        await db.refresh(invoice_obj)

        # Generate a simple PDF report as response
        pdf_content = "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        pdf_content += "2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
        pdf_content += "3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
        pdf_content += "4 0 obj\n<<\n/Length 60\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Invoice Receipt - " + datetime.now().strftime("%Y-%m-%d") + ") Tj\nET\nendstream\nendobj\n"
        pdf_content += "xref\n0 5\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n%%EOF"

        encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

        return encoded_pdf
    finally:
        # Release the advisory lock
        unlock_result = await db.execute(select(func.pg_advisory_unlock(123457)))


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: str,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific invoice by ID
    """
    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    statement = select(Invoice).where(Invoice.id == invoice_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Parse JSON fields for response
    try:
        items_data = json.loads(invoice.items)
    except:
        items_data = []

    try:
        totals_data = json.loads(invoice.totals)
    except:
        totals_data = {}

    return {
        "invoice_id": str(invoice.id),
        "invoice_no": invoice.invoice_no,
        "customer_id": str(invoice.customer_id) if invoice.customer_id else None,
        "salesman_id": str(invoice.salesman_id) if invoice.salesman_id else None,
        "items": items_data,
        "totals": totals_data,
        "total_amount": float(invoice.total_amount),
        "amount_paid": float(invoice.amount_paid),
        "balance_due": float(invoice.balance_due),
        "payment_status": invoice.payment_status,
        "payments_history": json.loads(invoice.payments_history),
        "taxes": float(invoice.taxes),
        "discounts": float(invoice.discounts) if invoice.discounts else 0.0,
        "status": invoice.status.value if hasattr(invoice.status, 'value') else invoice.status,
        "payment_method": invoice.payment_method,
        "notes": invoice.notes or "",
        "created_by": str(invoice.created_by),
        "created_at": invoice.created_at.isoformat(),
        "updated_at": invoice.updated_at.isoformat()
    }


@router.put("/invoices/{invoice_id}")
async def update_invoice(
    invoice_id: str,
    invoice_update: InvoiceUpdate,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update existing invoice
    """
    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    statement = select(Invoice).where(Invoice.id == invoice_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Update fields if provided
    update_data = invoice_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if hasattr(invoice, field):
            setattr(invoice, field, value)

    # Update timestamp
    invoice.updated_at = datetime.now()

    await db.commit()
    await db.refresh(invoice)

    return {
        "success": True,
        "message": "Invoice updated successfully",
        "invoice_id": str(invoice.id)
    }


@router.delete("/invoices/{invoice_id}")
async def delete_invoice(
    invoice_id: str,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete invoice by ID
    """
    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    statement = select(Invoice).where(Invoice.id == invoice_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    await db.delete(invoice)
    await db.commit()

    return {
        "success": True,
        "message": "Invoice deleted successfully"
    }


@router.get("/invoices")
async def get_invoices(
    limit: int = Query(100, ge=1, le=200),
    skip: int = Query(0, ge=0),
    customer_id: str = Query(None),
    status: str = Query(None),
    date: str = Query(None),
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of invoices with optional filtering
    """
    statement = select(Invoice)

    # Apply filters
    if customer_id:
        try:
            customer_uuid = UUID(customer_id)
            statement = statement.where(Invoice.customer_id == customer_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid customer ID format"
            )

    if status:
        try:
            status_enum = InvoiceStatus(status.lower())
            statement = statement.where(Invoice.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status value"
            )

    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            statement = statement.where(func.date(Invoice.created_at) == target_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD."
            )

    # Apply pagination and ordering
    statement = statement.offset(skip).limit(limit).order_by(Invoice.created_at.desc())

    result = await db.execute(statement)
    invoices = result.scalars().all()

    invoice_list = []
    for inv in invoices:
        try:
            items_data = json.loads(inv.items)
        except:
            items_data = []

        # Calculate total quantity from items
        total_quantity = 0
        for item in items_data:
            quantity = item.get('quantity', 0)
            total_quantity += int(quantity) if quantity else 0

        invoice_list.append({
            "invoice_id": str(inv.id),
            "invoice_no": inv.invoice_no,
            "customer_id": str(inv.customer_id) if inv.customer_id else None,
            "salesman_id": str(inv.salesman_id) if inv.salesman_id else None,
            "customer_name": getattr(inv, 'customer_name', 'Walk-in Customer'),  # Assuming walk-in customer if no name
            "team_name": getattr(inv, 'team_name', ''),  # Assuming team name if available
            "quantity": total_quantity,
            "total_amount": float(inv.total_amount),
            "date": inv.created_at.strftime("%Y-%m-%d"),
            "status": inv.status.value if hasattr(inv.status, 'value') else inv.status,
            "items": items_data,
            "created_at": inv.created_at.isoformat(),
            "updated_at": inv.updated_at.isoformat()
        })

    return invoice_list


@router.get("/invoices/{invoice_id}/duplicate")
async def get_duplicate_invoice(
    invoice_id: str,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get duplicate invoice/receipt for an existing invoice
    """
    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    statement = select(Invoice).where(Invoice.id == invoice_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Parse JSON fields for the PDF report
    try:
        items_data = json.loads(invoice.items)
    except:
        items_data = []

    try:
        totals_data = json.loads(invoice.totals)
    except:
        totals_data = {}

    # Generate duplicate PDF report
    pdf_content = "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    pdf_content += "2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    pdf_content += "3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
    pdf_content += "4 0 obj\n<<\n/Length 120\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Duplicate Invoice Receipt - " + invoice.invoice_no + ") Tj\nT* 10 -15 Td\n(Invoice Date: " + invoice.created_at.strftime("%Y-%m-%d %H:%M:%S") + ") Tj\nT* 10 -15 Td\n(Total Amount: $" + str(invoice.total_amount) + ") Tj\nET\nendstream\nendobj\n"
    pdf_content += "xref\n0 5\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n%%EOF"

    encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

    return encoded_pdf