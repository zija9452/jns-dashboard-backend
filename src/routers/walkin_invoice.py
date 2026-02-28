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
from ..models.invoice import Invoice, InvoiceRead, InvoiceCreate, InvoiceUpdate, InvoiceStatus
from ..models.product import Product
from ..models.customer import Customer
from ..models.salesman import Salesman
from ..models.user import User
from ..auth.session_auth import get_current_user_from_session, admin_required_from_session, cashier_required_from_session, employee_required_from_session, admin_cashier_employee_required_from_session

router = APIRouter()

@router.post("/walkin-invoices")
async def create_walkin_invoice(
    request_data: dict,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new invoice for walk-in customer with immediate payment
    All products selected and paid in full at time of purchase
    """
    # Extract data from request body
    order_items = request_data.get('items', [])
    customer_id = request_data.get('customer_id')  # Customer ID with foreign key reference
    salesman_id = request_data.get('salesman_id')  # Salesman ID with foreign key reference (optional)
    payment_method = request_data.get('payment_method', 'cash')
    # Parse payment_date - can be string or datetime
    payment_date_str = request_data.get('payment_date', datetime.now().isoformat())
    if isinstance(payment_date_str, str):
        try:
            payment_date = datetime.fromisoformat(payment_date_str)
        except ValueError:
            # Handle date-only strings like "2026-02-26"
            from datetime import date
            payment_date = datetime.combine(date.fromisoformat(payment_date_str), datetime.min.time())
    else:
        payment_date = payment_date_str
    manual_discount = float(request_data.get('manual_discount', 0))  # Additional discount at payment time
    notes = request_data.get('notes', '')

    # Validate that order items exist
    if not order_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order items are required"
        )

    # Validate customer if provided
    customer_name = "Walk-in Customer"
    if customer_id:
        customer_result = await db.execute(select(Customer).where(Customer.id == customer_id))
        customer = customer_result.scalar_one_or_none()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID '{customer_id}' not found"
            )
        customer_name = customer.name  # Use 'name' attribute from Customer model

    # Validate salesman if provided
    if salesman_id:
        salesman_result = await db.execute(select(Salesman).where(Salesman.id == salesman_id))
        salesman = salesman_result.scalar_one_or_none()
        if not salesman:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Salesman with ID '{salesman_id}' not found"
            )

    # Process each order item and update inventory
    items_list = []
    total_amount = Decimal('0')  # Total before discounts (this is the original total)
    total_discount = 0.0  # Total discount amount

    for item in order_items:
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

        # Verify product exists in the database
        product_result = await db.execute(select(Product).where(Product.name == pro_name))
        product = product_result.scalar_one_or_none()
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product '{pro_name}' not found in inventory"
            )

        # Check if sufficient inventory is available
        if product.stock_level < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product '{pro_name}'. Available: {product.stock_level}, Requested: {quantity}"
            )

        # Calculate total for this item (before discount)
        item_total_before_discount = quantity * unit_price
        # Calculate discount for this item
        item_discount = discount
        # Calculate final price after discount
        item_total_after_discount = item_total_before_discount - item_discount
        if item_total_after_discount < 0:
            item_total_after_discount = 0  # Prevent negative totals

        # Create item object
        item_obj = {
            "product_name": str(pro_name),
            "product_id": str(product.id),  # Include product ID for reference
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": item_total_before_discount,  # Price before discount
            "discount": item_discount,
            "cat_name": str(item.get('cat_name', '')),
        }
        items_list.append(item_obj)
        total_amount += Decimal(str(item_total_before_discount))
        total_discount += item_discount

        # Update product inventory - decrease stock by the sold quantity
        new_stock_level = product.stock_level - quantity
        if new_stock_level < 0:
            new_stock_level = 0  # Don't allow negative stock
        product.stock_level = new_stock_level
        await db.commit()

    # Add manual discount to total discount
    total_discount += manual_discount

    # For immediate payment invoices, amount paid equals total amount minus discount
    amount_paid = total_amount - Decimal(str(total_discount))

    # Generate unique invoice number with database-level locking for concurrency safety
    # Use database advisory lock to prevent race conditions
    lock_result = await db.execute(select(func.pg_advisory_lock(123459)))

    try:
        # Find the highest invoice number globally and increment the sequence
        prefix_pattern = "SIN-%"  # Walk-In Invoice prefix
        statement = select(func.max(Invoice.invoice_no)).where(
            Invoice.invoice_no.like(prefix_pattern)
        )
        result = await db.execute(statement)
        max_invoice_no = result.scalar_one_or_none()

        if max_invoice_no:
            # Extract the sequence number from existing format like "SIN-001"
            try:
                parts = max_invoice_no.split("-")
                if len(parts) >= 2:
                    existing_seq = parts[-1]  # Get the last part (sequence number)
                    if existing_seq.isdigit():
                        next_seq = int(existing_seq) + 1
                        seq_number = f"{next_seq:04d}"  # Format as 4-digit sequence (0001, 0002, etc.)
                    else:
                        seq_number = "0001"  # Default if parsing fails
                else:
                    seq_number = "0001"  # Default if format doesn't match expected pattern
            except:
                seq_number = "0001"  # Default if any error
        else:
            seq_number = "0001"  # Start with 001 if no invoices exist

        invoice_no = f"SIN-{seq_number}"

        # Double-check for uniqueness in case of race conditions and increment if needed
        counter = 0
        while counter < 100:  # Safety check to avoid infinite loop
            check_statement = select(Invoice).where(Invoice.invoice_no == invoice_no)
            check_result = await db.execute(check_statement)
            existing_invoice = check_result.scalar_one_or_none()

            if existing_invoice:
                # Invoice number exists, increment and try again
                next_seq_int = int(seq_number) + 1
                seq_number = f"{next_seq_int:04d}"
                invoice_no = f"SIN-{seq_number}"
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
            customer_id=customer_id if customer_id else None,  # Customer ID with foreign key reference
            customer_name=customer_name,  # Customer name
            salesman_id=salesman_id if salesman_id else None,  # Salesman ID with foreign key reference (optional)
            items=json.dumps(items_list),
            totals=json.dumps({
                "subtotal": float(total_amount),  # Original total before discounts
                "tax": 0.0,
                "discount": float(total_discount),  # Total discount amount (item + manual)
                "total": float(total_amount),  # Original total before discount
                "amount_paid": float(amount_paid),  # Amount actually paid (after discount)
                "balance_due": 0.0,  # Always 0 for immediate payment
                "payment_status": "paid"  # Always "paid" for immediate payment
            }),
            total_amount=Decimal(str(total_amount)),  # Original total before discount
            amount_paid=Decimal(str(amount_paid)),  # Amount actually paid
            payment_status="paid",  # Always "paid" for immediate payment
            payments_history=json.dumps([{
                "amount": float(amount_paid),
                "payment_method": payment_method,
                "date": payment_date.isoformat() if hasattr(payment_date, 'isoformat') else str(payment_date),
                "description": "Full payment at invoice creation"
            }]),
            discounts=Decimal(str(total_discount)),  # Total discount amount
            payment_method=payment_method,
            payment_date=payment_date,  # Payment date
            notes=notes,
            created_by=current_user.id
        )

        # Add to database
        db.add(invoice_obj)
        await db.commit()
        await db.refresh(invoice_obj)

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
(Walk-in Invoice Receipt - {invoice_no}) Tj
T* 15 -15 Td
(Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}) Tj
T* 15 -15 Td
(Total Amount: ${float(total_amount):.2f}) Tj
T* 15 -15 Td
(Payment Method: {payment_method}) Tj
T* 15 -15 Td
(Status: PAID) Tj
T* 15 -15 Td
(Thank you for your purchase!) Tj
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
        unlock_result = await db.execute(select(func.pg_advisory_unlock(123459)))


@router.get("/walkin-invoices/{invoice_id}")
async def get_walkin_invoice(
    invoice_id: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific walk-in invoice by ID
    """
    try:
        invoice_uuid = uuid.UUID(invoice_id)
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
        # NOTE: No customer_id for walk-in invoices since they are from walk-in customers without accounts
        "customer_name": invoice.customer_name,  # Name of walk-in customer
        # NOTE: No salesman_id for walk-in invoices since they are direct sales
        "items": items_data,
        "totals": totals_data,
        "total_amount": float(invoice.total_amount),
        "amount_paid": float(invoice.amount_paid),
        "balance_due": float(invoice.balance_due),
        "payment_status": invoice.payment_status,  # Will be "paid" for immediate payment
        "taxes": float(invoice.taxes),
        "discounts": float(invoice.discounts) if invoice.discounts else 0.0,
        "status": invoice.status.value if hasattr(invoice.status, 'value') else invoice.status,
        "payment_method": invoice.payment_method,  # Shows payment method (cash, card, etc.)
        "notes": invoice.notes or "",
        "created_by": str(invoice.created_by),
        "created_at": invoice.created_at.isoformat(),
        "updated_at": invoice.updated_at.isoformat()
        # NOTE: Removed payments_history for simplicity in walk-in invoices
    }


@router.put("/walkin-invoices/{invoice_id}")
async def update_walkin_invoice(
    invoice_id: str,
    invoice_update: InvoiceUpdate,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update existing walk-in invoice
    """
    try:
        invoice_uuid = uuid.UUID(invoice_id)
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


@router.delete("/walkin-invoices/{invoice_id}")
async def delete_walkin_invoice(
    invoice_id: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete walk-in invoice by ID
    This will restore the inventory quantities that were decreased when the invoice was created
    """
    try:
        invoice_uuid = uuid.UUID(invoice_id)
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

    # Restore inventory by increasing stock levels
    try:
        items_data = json.loads(invoice.items)
        for item in items_data:
            product_name = item.get('product_name')
            quantity_sold = item.get('quantity', 0)

            if product_name and quantity_sold:
                # Find and update the product
                product_result = await db.execute(select(Product).where(Product.name == product_name))
                product = product_result.scalar_one_or_none()

                if product:
                    # Increase stock level by the sold amount
                    product.stock_level += quantity_sold
                    await db.commit()
    except Exception as e:
        logging.error(f"Error restoring inventory for invoice {invoice_id}: {str(e)}")

    await db.delete(invoice)
    await db.commit()

    return {
        "success": True,
        "message": "Invoice deleted successfully and inventory restored"
    }


@router.get("/walkin-invoices")
async def get_walkin_invoices(
    limit: int = Query(100, ge=1, le=200),
    skip: int = Query(0, ge=0),
    customer_id: str = Query(None),
    status: str = Query(None),
    date: str = Query(None),
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of walk-in invoices with optional filtering
    """
    statement = select(Invoice)

    # Apply filters
    if customer_id:  # Keep the parameter name for compatibility but filter by customer_name
        # For walk-in invoices, we can search by customer name instead of ID
        statement = statement.where(Invoice.customer_name.ilike(f"%{customer_id}%"))

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
            # NOTE: No customer_id for walk-in invoices since they are from walk-in customers without accounts
            "customer_name": getattr(inv, 'customer_name', 'Walk-in Customer'),  # Name of walk-in customer
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


@router.get("/walkin-invoices/{invoice_id}/receipt")
async def get_walkin_invoice_receipt(
    invoice_id: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get duplicate invoice/receipt for an existing walk-in invoice
    """
    try:
        invoice_uuid = uuid.UUID(invoice_id)
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

    # Generate duplicate PDF receipt
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
(Duplicate Invoice Receipt - {invoice.invoice_no}) Tj
T* 15 -15 Td
(Date: {invoice.created_at.strftime("%Y-%m-%d %H:%M:%S")}) Tj
T* 15 -15 Td
(Total Amount: ${float(invoice.total_amount):.2f}) Tj
T* 15 -15 Td
(Amount Paid: ${float(invoice.amount_paid):.2f}) Tj
T* 15 -15 Td
(Payment Method: {invoice.payment_method}) Tj
T* 15 -15 Td
(Status: {invoice.payment_status.upper()}) Tj
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


@router.get("/walkin-invoices/date/{date_str}")
async def get_walkin_invoices_by_date(
    date_str: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all walk-in invoices for a specific date
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD."
        )

    # Query invoices created on the specific date
    statement = select(Invoice).where(
        func.date(Invoice.created_at) == target_date
    )

    result = await db.execute(statement)
    invoices = result.scalars().all()

    # Calculate total amounts for all invoices on that date
    total_amount = 0.0
    invoice_list = []

    for invoice in invoices:
        try:
            # Parse totals JSON to get the actual total
            totals_data = json.loads(invoice.totals)
            invoice_total = totals_data.get('total', 0.0)
            total_amount += float(invoice_total)

            # Parse items JSON to get product details
            items_data = []
            try:
                items_data = json.loads(invoice.items)
            except (json.JSONDecodeError, TypeError):
                items_data = []

            # Create product details in the requested format
            products_list = []
            for item in items_data:
                product_detail = {
                    "Orderid": str(invoice.id),
                    "Product": str(item.get('product_name', item.get('pro_name', ''))),
                    "Price": float(item.get('unit_price', 0.0)),
                    "Amount Paid": float(item.get('total_price', 0.0)),
                    "Quantity": int(item.get('quantity', item.get('pro_quantity', 0))),
                    "Discount": float(item.get('discount', 0.0)),
                    "Total Discount": float(totals_data.get('discount', 0.0)) if isinstance(totals_data, dict) else 0.0,
                    "Cost": float(item.get('unit_price', 0.0)) * int(item.get('quantity', item.get('pro_quantity', 1))),  # Calculate cost as price * quantity
                    "Time": invoice.created_at.strftime("%H:%M:%S") if invoice.created_at else "",
                    "Date": invoice.created_at.strftime("%Y-%m-%d") if invoice.created_at else ""
                }
                products_list.append(product_detail)

            # Add invoice details to list
            invoice_list.append({
                "invoice_id": str(invoice.id),
                "invoice_no": str(invoice.invoice_no),
                # NOTE: No customer_id for walk-in invoices since they are from walk-in customers without accounts
                "customer_name": invoice.customer_name,  # Name of walk-in customer
                "total_amount": float(invoice_total),
                "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
                "products": products_list
            })
        except (ValueError, TypeError):
            # If parsing fails for this invoice, skip its amount in total
            continue

    return {
        "date": date_str,
        "total_invoices": len(invoice_list),
        "total_amount": total_amount,
        "invoices": invoice_list
    }


@router.get("/products-for-sales")
async def get_products_for_sales(
    search_term: str = Query(None),
    barcode: str = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get products for salesman to select from during sales
    Allows filtering by name, barcode, etc.
    """
    statement = select(Product)

    # Apply search filters
    if search_term:
        search_lower = search_term.lower()
        statement = statement.where(
            (Product.name.ilike(f"%{search_lower}%")) |
            (Product.barcode.ilike(f"%{search_lower}%")) |
            (Product.sku.ilike(f"%{search_lower}%"))
        )

    if barcode:
        statement = statement.where(Product.barcode == barcode)

    # Only include products with stock available
    statement = statement.where(Product.stock_level > 0)

    # Apply limit and ordering
    statement = statement.limit(limit).order_by(Product.name.asc())

    result = await db.execute(statement)
    products = result.scalars().all()

    product_list = []
    for product in products:
        product_list.append({
            "id": str(product.id),
            "sku": product.sku,
            "name": product.name,
            "desc": product.desc,
            "unit_price": float(product.unit_price),
            "cost_price": float(product.cost_price),
            "tax_rate": float(product.tax_rate) if product.tax_rate else 0.0,
            "stock_level": product.stock_level,
            "barcode": product.barcode,
            "discount": float(product.discount) if product.discount else 0.0,
            "category": product.category,
            "attributes": product.attributes
        })

    return product_list


@router.get("/invoices-by-order-id/{order_id}")
async def get_invoice_by_order_id(
    order_id: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific invoice by order ID (invoice ID)
    """
    try:
        invoice_uuid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format"
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
        # NOTE: No customer_id for walk-in invoices since they are from walk-in customers without accounts
        "customer_name": invoice.customer_name,  # Name of walk-in customer
        # NOTE: No salesman_id for walk-in invoices since they are direct sales
        "items": items_data,
        "totals": totals_data,
        "total_amount": float(invoice.total_amount),
        "amount_paid": float(invoice.amount_paid),
        "balance_due": float(invoice.balance_due),
        "payment_status": invoice.payment_status,  # Will be "paid" for immediate payment
        "taxes": float(invoice.taxes),
        "discounts": float(invoice.discounts) if invoice.discounts else 0.0,
        "status": invoice.status.value if hasattr(invoice.status, 'value') else invoice.status,
        "payment_method": invoice.payment_method,  # Shows payment method (cash, card, etc.)
        "notes": invoice.notes or "",
        "created_by": str(invoice.created_by),
        "created_at": invoice.created_at.isoformat(),
        "updated_at": invoice.updated_at.isoformat()
        # NOTE: Removed payments_history for simplicity in walk-in invoices
    }


@router.get("/daily-invoice-report/{date_str}")
async def get_daily_invoice_report(
    date_str: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get daily invoice report showing all invoices and totals for a specific date
    """
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD."
        )

    # Query invoices created on the specific date
    statement = select(Invoice).where(
        func.date(Invoice.created_at) == target_date
    )

    result = await db.execute(statement)
    invoices = result.scalars().all()

    # Calculate total amounts for all invoices on that date
    total_amount = 0.0
    total_paid = 0.0
    total_discount = 0.0
    invoice_list = []

    for invoice in invoices:
        try:
            # Parse totals JSON to get the actual total
            totals_data = json.loads(invoice.totals)
            invoice_total = totals_data.get('total', 0.0)
            total_amount += float(invoice_total)
            
            # Get amount paid
            total_paid += float(invoice.amount_paid)
            
            # Get discount
            total_discount += totals_data.get('discount', 0.0)

            # Parse items JSON to get product details
            items_data = []
            try:
                items_data = json.loads(invoice.items)
            except (json.JSONDecodeError, TypeError):
                items_data = []

            # Create product details in the requested format
            products_list = []
            for item in items_data:
                product_detail = {
                    "Orderid": str(invoice.id),
                    "Product": str(item.get('product_name', item.get('pro_name', ''))),
                    "Price": float(item.get('unit_price', 0.0)),
                    "Amount Paid": float(item.get('total_price', 0.0)),
                    "Quantity": int(item.get('quantity', item.get('pro_quantity', 0))),
                    "Discount": float(item.get('discount', 0.0)),
                    "Total Discount": float(totals_data.get('discount', 0.0)) if isinstance(totals_data, dict) else 0.0,
                    "Cost": float(item.get('unit_price', 0.0)) * int(item.get('quantity', item.get('pro_quantity', 1))),  # Calculate cost as price * quantity
                    "Time": invoice.created_at.strftime("%H:%M:%S") if invoice.created_at else "",
                    "Date": invoice.created_at.strftime("%Y-%m-%d") if invoice.created_at else ""
                }
                products_list.append(product_detail)

            # Add invoice details to list
            invoice_list.append({
                "invoice_id": str(invoice.id),
                "invoice_no": str(invoice.invoice_no),
                "customer_id": str(invoice.customer_id) if invoice.customer_id else None,
                # NOTE: No salesman_id for walk-in invoices since they are direct sales
                "total_amount": float(invoice_total),
                "amount_paid": float(invoice.amount_paid),
                "payment_method": invoice.payment_method,
                "payment_status": invoice.payment_status,
                "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
                "products": products_list
            })
        except (ValueError, TypeError):
            # If parsing fails for this invoice, skip its amount in total
            continue

    return {
        "date": date_str,
        "total_invoices": len(invoice_list),
        "total_amount": total_amount,
        "total_paid": total_paid,
        "total_discount": total_discount,
        "invoices": invoice_list
    }