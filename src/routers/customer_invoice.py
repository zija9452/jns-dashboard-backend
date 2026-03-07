from fastapi import APIRouter, Depends, HTTPException, status as http_status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from uuid import UUID
import uuid
from datetime import datetime, date
import json
import base64

from ..database.database import get_db
from ..models.user import User  # Import User at the top to avoid NameError
from ..models.customer import Customer
from ..models.salesman import Salesman
from ..models.customer_invoice import CustomerInvoice, CustomerInvoiceCreate, CustomerInvoiceUpdate, CustomerInvoiceRead, CustomerInvoiceStatus
from ..models.invoice import Invoice
from ..models.product import Product
from ..auth.session_auth import get_current_user_from_session, admin_required_from_session, cashier_required_from_session, employee_required_from_session, admin_cashier_employee_required_from_session
from ..services.customer_service import CustomerService
from ..services.salesman_service import SalesmanService
from ..models.customer import CustomerCreate

router = APIRouter()


@router.post("/GetCustomerDetails")
async def get_customer_details(
    request_data: dict,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get customer details by name
    Required by JavaScript frontend
    """
    cus_name = request_data.get('cus_name')
    if not cus_name:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Customer name is required"
        )

    # Find customer by name - use parameterized queries to prevent SQL injection
    from sqlalchemy import select
    statement = select(Customer).where(Customer.name.ilike(f"%{cus_name}%")).limit(1)
    result = await db.execute(statement)
    customer = result.scalar_one_or_none()

    if customer:
        # Parse contacts JSON to extract phone and other details
        contacts_data = {}
        try:
            contacts_data = json.loads(customer.contacts)
        except (json.JSONDecodeError, TypeError):
            contacts_data = {"phone": "", "email": ""}

        return {
            "cus_id": str(customer.id),
            "cus_name": customer.name,
            "cus_phone": contacts_data.get("phone", ""),
            "cus_address": customer.billing_addr or "",
            "cus_cnic": "",  # Customer model doesn't have CNIC field
            "cus_balance": float(customer.credit_limit) if customer.credit_limit else 0.0
        }
    else:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )


@router.post("/Getsalesmandetail")
async def get_salesman_detail(
    request_data: dict,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get salesman details by name
    Required by JavaScript frontend
    """
    sal_name = request_data.get('sal_name')
    if not sal_name:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Salesman name is required"
        )

    # Find salesman by name - use parameterized queries to prevent SQL injection
    from sqlalchemy import select
    statement = select(Salesman).where(Salesman.name.ilike(f"%{sal_name}%"))
    result = await db.execute(statement)
    salesman = result.scalar_one_or_none()

    if salesman:
        return {
            "sal_id": str(salesman.id),
            "sal_name": salesman.name,
            "sal_phone": salesman.phone or "",
            "sal_address": salesman.address or "",
            "branch": salesman.branch or ""
        }
    else:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Salesman not found"
        )


@router.post("/SaveCustomerOrders")
async def save_customer_orders(
    request_data: dict = None,
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Save customer orders (customer invoice creation)
    Required by JavaScript frontend
    All parameters now come from request body for better security and best practices
    """
    from sqlalchemy import select, func
    from decimal import Decimal
    from uuid import UUID
    import json
    import uuid
    from datetime import datetime
    import base64

    # Extract data from request body
    order_items = request_data.get('items', []) if request_data else []
    customer_id = request_data.get('customer_id') if request_data else None
    customer_name = request_data.get('customer_name') if request_data else None
    team_name = request_data.get('team_name') if request_data else None
    payment_method = request_data.get('payment_method', 'cash') if request_data else 'cash'
    initial_paid_amount = request_data.get('initial_paid_amount', 0.0) if request_data else 0.0
    remarks = request_data.get('remarks', '') if request_data else ''
    salesman_id = request_data.get('salesman_id') if request_data else None
    timezone = request_data.get('timezone') if request_data else None
    date = request_data.get('date') if request_data else None

    # Validate that order items exist
    if not order_items:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Order items are required"
        )

    # Validate customer ID from request body
    customer_id_uuid = None
    if customer_id:
        try:
            customer_id_uuid = UUID(customer_id)
            # Verify customer exists
            customer_exists = await db.execute(select(Customer).where(Customer.id == customer_id_uuid))
            customer = customer_exists.scalar_one_or_none()
            if not customer:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail="Customer not found"
                )
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invalid customer ID format"
            )

    # Validate and handle customer name if provided
    if customer_name:
        # Find customer by name if customer_id is not provided
        if not customer_id:
            from sqlalchemy import func
            customer_by_name = await db.execute(select(Customer).where(Customer.name == customer_name))
            customer = customer_by_name.scalar_one_or_none()
            if customer:
                customer_id_uuid = customer.id
            else:
                raise HTTPException(
                    status_code=http_status.HTTP_404_NOT_FOUND,
                    detail=f"Customer with name '{customer_name}' not found"
                )

    # Handle team name if provided
    if team_name:
        # You can use team_name for additional processing if needed
        pass  # Currently just accepting the parameter

    # Create customer invoice ID
    invoice_id = uuid.uuid4()

    # Process each order item
    items_list = []
    total_subtotal = Decimal('0')  # Total before discounts
    total_discount = 0.0  # Total discount amount
    total_amount = Decimal('0')  # Total after discounts

    # Validate and process each order item
    for item in order_items:
        try:
            # Validate required fields
            pro_name = item.get('pro_name')
            if not pro_name:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Product name is required for each item"
                )

            quantity = int(item.get('pro_quantity', 0))
            if quantity <= 0:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Product quantity must be positive"
                )

            unit_price = float(item.get('unit_price', 0))
            if unit_price < 0:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Unit price cannot be negative"
                )

            discount = float(item.get('discount', 0))
            if discount < 0:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Discount cannot be negative"
                )

            # Calculate total for this item (before discount)
            item_subtotal = quantity * unit_price
            # Calculate final price after discount
            item_total = item_subtotal
            if item_total < 0:
                item_total = 0  # Prevent negative totals

            # Create item object
            item_obj = {
                "product_name": str(pro_name),
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": item_subtotal,  # Price before discount
                "discount": discount,
                "total_price": item_total,  # Price after discount
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
                "imgfile3": str(item.get('imgfile3', '')),
            }
            items_list.append(item_obj)
            total_amount += Decimal(str(item_subtotal))  # Add original price before discount
            total_discount += discount
        except (ValueError, TypeError) as e:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid data format in order item: {str(e)}"
            )

    # Calculate net amount (total after all discounts)
    net_amount = total_amount

    # Generate unique sequential invoice number with database-level locking for concurrency safety
    from datetime import datetime

    # Use database-level locking to prevent race conditions
    lock_statement = select(func.pg_advisory_lock(123456))  # PostgreSQL advisory lock
    await db.execute(lock_statement)

    try:
        # Find the highest invoice number globally and increment the sequence
        prefix_pattern = "CIN-%"
        statement = select(func.max(CustomerInvoice.invoice_no)).where(
            CustomerInvoice.invoice_no.like(prefix_pattern)
        )
        result = await db.execute(statement)
        max_invoice_no = result.scalar_one_or_none()

        if max_invoice_no:
            # Extract the sequence number from existing format like "CIN-001"
            try:
                # Split by dash and get the sequence part (last part)
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

        invoice_no = f"CIN-{seq_number}"

        # Double-check for uniqueness in case of race conditions and increment if needed
        counter = 0
        while counter < 100:  # Safety check to avoid infinite loop
            check_statement = select(CustomerInvoice).where(CustomerInvoice.invoice_no == invoice_no)
            check_result = await db.execute(check_statement)
            existing_invoice = check_result.scalar_one_or_none()

            if existing_invoice:
                # Invoice number exists, increment and try again
                next_seq_int = int(seq_number) + 1
                seq_number = f"{next_seq_int:03d}"
                invoice_no = f"CIN-{seq_number}"
                counter += 1
            else:
                break  # Found a unique number

        if counter >= 100:
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not generate unique invoice number"
            )

        # Get salesman ID from query parameter if provided
        salesman_id_uuid = None
        if salesman_id:
            try:
                salesman_id_uuid = UUID(salesman_id)
            except ValueError:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail="Invalid salesman ID format"
                )

        # Calculate initial payment values
        initial_paid_decimal = Decimal(str(initial_paid_amount))
        initial_balance_due = net_amount - initial_paid_decimal

        # Determine payment status based on initial payment
        if initial_balance_due <= 0:
            payment_status = "paid"
        elif initial_paid_decimal > 0:
            payment_status = "partial"
        else:
            payment_status = "unpaid"

        # Create initial payment history if an initial payment was made
        initial_payment_history = []
        if initial_paid_amount > 0:
            from datetime import datetime
            initial_payment_history.append({
                "amount": float(initial_paid_amount),
                "payment_method": payment_method,
                "date": datetime.now().isoformat(),
                "description": f"Initial payment at order creation: {initial_paid_amount}"
            })

        # Use the initial_paid_amount from request (what user actually paid)
        calculated_amount_paid = initial_paid_decimal

        # Create customer invoice data
        invoice_data = {
            "id": invoice_id,
            "invoice_no": invoice_no,
            "customer_id": customer_id_uuid,  # Use the validated customer_id from query parameter
            "customer_name": customer_name,  # Use customer name from query parameter
            "team_name": team_name,  # Use team name from query parameter
            "salesman_id": salesman_id_uuid,  # Use salesman ID from query parameter
            "items": json.dumps(items_list),
            "totals": json.dumps({
                "subtotal": float(total_amount),  # Original total before discounts
                "tax": 0.0,
                "discount": total_discount,
                "total": float(total_amount),  # Original total before discount
                "amount_paid": float(calculated_amount_paid),  # Amount actually paid (after discount)
                "balance_due": float(initial_balance_due),  # Calculate remaining balance
                "payment_status": payment_status  # Set status based on payment
            }),
            "total_amount": Decimal(str(total_amount)),  # Original total before discount
            "amount_paid": calculated_amount_paid,  # Amount actually paid (after discount)
            "balance_due": initial_balance_due,  # Calculate remaining balance
            "payment_status": payment_status,  # Set status based on payment
            "payments_history": json.dumps(initial_payment_history),  # Include initial payment in history
            "taxes": Decimal('0'),
            "discounts": Decimal(str(total_discount)),  # Total discount amount
            "status": CustomerInvoiceStatus.PENDING,  # Default order status
            "payment_method": payment_method,  # Use payment method from query parameter
            "notes": remarks,  # Use remarks from query parameter
            "created_by": current_user.id,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        # Add to database - include all fields that exist in the model including total_amount, amount_paid, balance_due, and payment_status
        db_customer_invoice = CustomerInvoice(**{k: v for k, v in invoice_data.items()})
        db.add(db_customer_invoice)
        await db.commit()
        await db.refresh(db_customer_invoice)  # Refresh to get the created record

        # Return invoice_id for fetching receipt (consistent with customer details pattern)
        return {
            "success": True,
            "invoice_id": str(db_customer_invoice.id),
            "invoice_no": invoice_no
        }
    finally:
        # Release the advisory lock
        unlock_statement = select(func.pg_advisory_unlock(123456))
        await db.execute(unlock_statement)


@router.post("/receipt/{invoice_id}")
async def get_invoice_receipt(
    invoice_id: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate and return invoice receipt PDF (consistent with customer report pattern)
    Required by JavaScript frontend
    """
    from sqlalchemy import select
    import json
    from uuid import UUID

    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    # Get the invoice
    statement = select(CustomerInvoice).where(CustomerInvoice.id == invoice_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Parse invoice data
    items_list = json.loads(invoice.items)
    totals = json.loads(invoice.totals)

    # Generate PDF
    pdf_content = generate_simple_receipt_pdf(
        invoice_no=invoice.invoice_no,
        customer_name=invoice.customer_name or "N/A",
        team_name=invoice.team_name,
        items=items_list,
        total_amount=float(invoice.total_amount),
        total_discount=float(invoice.discounts or 0),
        amount_paid=float(invoice.amount_paid),
        balance_due=float(invoice.balance_due),
        payment_method=invoice.payment_method,
        payment_status=invoice.payment_status,
        created_at=invoice.created_at
    )

    # generate_simple_receipt_pdf already returns base64-encoded string, use directly
    return {"pdf": pdf_content}


def generate_simple_receipt_pdf(invoice_no, customer_name, team_name, items, total_amount,
                                  total_discount, amount_paid, balance_due, payment_method,
                                  payment_status, created_at, bill_type: str = "SALE RECEIPT"):
    """Generate thermal receipt style PDF using weasyprint (same as customers.py)"""
    
    # Simplify payment method name (e.g., "EasyPaisa Sir Yasir" -> "EasyPaisa")
    display_payment_method = payment_method or "Cash"
    if "easypaisa" in display_payment_method.lower():
        display_payment_method = "EasyPaisa"
    elif "faysal" in display_payment_method.lower():
        display_payment_method = "Faysal Bank"
    elif "cash" in display_payment_method.lower():
        display_payment_method = "Cash"
    elif "credit" in display_payment_method.lower():
        display_payment_method = "Credit"

    # Format date
    date_str = created_at.strftime("%m-%d-%Y %I:%M %p")
    
    # Build items rows
    items_rows = ""
    for item in items[:12]:  # Limit to 12 items
        name = str(item.get('product_name', ''))[:15]
        qty = int(item.get('quantity', 0))
        price = float(item.get('unit_price', 0))
        total = float(item.get('total_price', 0))
        
        items_rows += f"""
        <tr>
            <td class="item-name">{name}</td>
            <td class="text-center">{qty}</td>
            <td class="text-right">{price:.0f}</td>
            <td class="text-right">{total:.0f}</td>
        </tr>
        """
    
    # Calculate grand total
    grand_total = total_amount - total_discount
    
    # Team name row (if exists)
    team_row = f'<p class="team">Team: {team_name}</p>' if team_name else ""
    
    # Create simple HTML for PDF (same pattern as customers.py)
    items_rows = ""
    for item in items[:10]:
        name = str(item.get('product_name', ''))[:30]
        qty = int(item.get('quantity', 0))
        price = float(item.get('unit_price', 0))
        disc = float(item.get('discount', 0))
        total = float(item.get('total_price', 0))
        items_rows += f'<tr><td style="width: 40%; border-bottom: 1px dashed #000; padding: 2px;"><div style="font-weight: bold; margin-bottom: 3px;">{name}</div></td><td style="width: 15%; border-bottom: 1px dashed #000; padding: 2px; text-align: center;">{price:.0f}</td><td style="width: 12%; border-bottom: 1px dashed #000; padding: 2px; text-align: center;">{qty}</td><td style="width: 13%; border-bottom: 1px dashed #000; padding: 2px; text-align: center;">{disc:.0f}</td><td style="width: 20%; border-bottom: 1px dashed #000; padding: 2px; text-align: center;">{total:.0f}</td></tr>\n'

    current_date = created_at.strftime('%d-%m-%Y %I:%M %p')
    team_line = f"<p>Team: {team_name}</p>" if team_name else ""

    # Logo - use SVG for better WeasyPrint compatibility
    import os
    logo_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'Images',
        'European Sports.svg'
    )
    
    logo_html = '🏆'  # Default fallback
    try:
        if os.path.exists(logo_path):
            with open(logo_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
                # Embed SVG directly in HTML
                logo_html = f'<div style="text-align:center;margin:5px 0;">{svg_content}</div>'
                print(f"✓ SVG Logo loaded ({len(svg_content)} chars)")
        else:
            print(f"✗ SVG Logo file not found: {logo_path}")
    except Exception as e:
        print(f"✗ Logo load error: {e}")
        logo_html = '🏆'

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: 300px 1000px;
                margin: 0;
            }}
            body {{
                width: 300px;
                font-family: Arial, Helvetica, sans-serif;
                font-size: 12px;
                margin: 0;
                padding: 8px 5px;
                box-sizing: border-box;
                line-height: 1.5;
            }}
            .header {{
                text-align: center;
                margin-bottom: 10px;
                border-bottom: 2px solid #000;
                padding-bottom: 10px;
                padding-top: 5px;
            }}
            .header h1 {{
                font-size: 16px;
                margin: 2px 0;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .logo {{
                margin: 8px 0;
                text-align: center;
            }}
            .logo svg {{
                max-width: 70px;
                max-height: 70px;
                width: auto;
                height: auto;
                display: block;
                margin: 0 auto;
            }}
            .contact {{
                font-size: 10px;
                margin: 3px 0;
                text-align: center;
            }}
            .info {{
                font-size: 10px;
                margin: 8px 0;
                border-bottom: 2px solid #000;
                padding-bottom: 8px;
                padding-top: 5px;
            }}
            .info p {{
                margin: 3px 0;
                font-weight: normal;
            }}
            .info strong {{
                font-weight: 600;
            }}
            .duplicate {{
                text-align: center;
                font-size: 14px;
                font-weight: bold;
                margin: 8px 0;
                border-bottom: 2px solid #000;
                padding-bottom: 6px;
                padding-top: 3px;
                letter-spacing: 1px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 10px;
                margin: 8px 0;
            }}
            th {{
                border-top: 2px solid #000;
                border-bottom: 2px solid #000;
                font-size: 10px;
                font-weight: 600;
                padding: 5px 2px;
                text-align: left;
                font-weight: 500;
            }}
            td {{
                font-size: 10px;
                padding: 5px 2px;
                vertical-align: top;
                text-align: center;
                border-bottom: 1px dashed #000;
            }}
            td:first-child {{
                text-align: left;
            }}
            .item-name {{
                font-weight: bold;
                display: block;
                width: 100%;
            }}
            .item-values {{
                display: flex;
                justify-content: space-around;
                width: 100%;
                margin-top: 2px;
                padding-top: 2px;
                border-top: 1px dashed #000;
            }}
            .item-value {{
                text-align: center;
                min-width: 45px;
                flex: 1;
            }}
            .text-center {{ text-align: center; }}
            .text-right {{ text-align: right; }}
            .totals {{
                border-top: 2px solid #000;
                margin-top: 10px;
                padding-top: 8px;
                padding-bottom: 5px;
            }}
            .total-row {{
                font-weight: bold;
                font-size: 11px;
                margin: 3px 0;
            }}
            .total-label {{
                display: inline-block;
                min-width: 160px;
                font-weight: bold;
            }}
            .total-value {{
                font-weight: bold;
                text-align: right;
            }}
            .payment {{
                border-top: 2px solid #000;
                margin-top: 8px;
                padding-top: 2px;
                padding-bottom: 0px;
                text-align: center;
                font-size: 10px;
                font-weight: bold;
            }}
            .footer {{
                border-top: 2px solid #000;
                margin-top: 8px;
                padding-top: 8px;
                padding-bottom: 8px;
                text-align: center;
                font-size: 9px;
            }}
            .footer p {{
                margin: 4px 0;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo">
                {logo_html}
            </div>
            <h1>EUROPEAN SPORTS</h1>
            <p class="contact">Contact: 0315-2263745</p>
            <p class="contact">Shop#8, Mazar Wali Gali, Light House, Khi</p>
        </div>
        <div class="info">
            <p><strong>Date:</strong> {current_date}</p>
            <p><strong>Bill No:</strong> {invoice_no}</p>
            <p><strong>User:</strong> Admin | <strong>Name:</strong> {customer_name}</p>
            <p><strong>Ph:</strong> 00 | <strong>Remarks:</strong> 0</p>
        </div>
        <div class="duplicate">*** {bill_type} ***</div>
        <table>
            <thead>
                <tr>
                    <th style="width: 35%;">Item</th>
                    <th style="width: 15%;" class="text-right">Price</th>
                    <th style="width: 12%;" class="text-center">Qty</th>
                    <th style="width: 13%;" class="text-right">Disc</th>
                    <th style="width: 25%;" class="text-right">Amount</th>
                </tr>
            </thead>
            <tbody>
                {items_rows}
            </tbody>
        </table>
        <div class="totals">
            <p class="total-row"><span class="total-label">Total Bill:</span><span class="total-value">{total_amount:.0f}</span></p>
            <p class="total-row"><span class="total-label">Item Discount:</span><span class="total-value">0</span></p>
            <p class="total-row"><span class="total-label">Total Discount(Rs):</span><span class="total-value">{total_discount:.0f}</span></p>
            <p class="total-row"><span class="total-label">Grand Total:</span><span class="total-value">{total_amount:.0f}</span></p>
            <p class="total-row"><span class="total-label">Amount Paid:</span><span class="total-value">{amount_paid:.0f}</span></p>
            <p class="total-row"><span class="total-label">Balance:</span><span class="total-value">-{balance_due:.0f}</span></p>
            
        </div>
        <div class="payment">
            <p>Payment Mode: {display_payment_method}</p>
        </div>
        <div class="footer">
            <p>Thankyou For Shopping. Come Again.</p>
            <p>No Return No Exchange Without Bill</p>
        </div>
    </body>
    </html>
    """

    # Generate PDF using weasyprint
    try:
        from weasyprint import HTML, CSS
        
        # Create HTML document
        html_doc = HTML(string=html_content)
        
        # Write PDF with custom page size (57mm = 216 CSS pixels at 96 DPI)
        pdf_bytes = html_doc.write_pdf()
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
        print(f"PDF generated, length: {len(encoded_pdf)}")
    except Exception as e:
        print(f"weasyprint failed: {e}")
        # Fallback - narrow page (57mm approx = 216px width, height auto)
        encoded_pdf = base64.b64encode(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 216 400] >>\nendobj\nxref\n0 4\ntrailer\n<< /Size 4 /Root 1 0 R >>\n%%EOF").decode()

    return encoded_pdf  # Return string, NOT Response


@router.post("/GetCustomerInvoiceBalance")
async def get_customer_invoice_balance(
    customer_id: str = None,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get customer invoice balance
    Required by JavaScript frontend
    """
    from sqlalchemy import select
    import json

    if customer_id:
        try:
            customer_uuid = UUID(customer_id)
            # Get all invoices for this customer that are not paid
            statement = select(CustomerInvoice).where(
                CustomerInvoice.customer_id == customer_uuid,
                CustomerInvoice.status != CustomerInvoiceStatus.PAID
            )
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invalid customer ID format"
            )
    else:
        # Get all unpaid invoices for all customers
        statement = select(CustomerInvoice).where(
            CustomerInvoice.status != CustomerInvoiceStatus.PAID
        )

    result = await db.execute(statement)
    invoices = result.scalars().all()

    # Calculate total balance by parsing the totals JSON for each invoice
    total_balance = 0.0
    for invoice in invoices:
        try:
            # Parse the totals JSON to get the total amount
            totals_data = json.loads(invoice.totals)
            invoice_total = totals_data.get('total', 0.0)
            total_balance += float(invoice_total)
        except (json.JSONDecodeError, TypeError, ValueError):
            # If parsing fails, skip this invoice
            continue

    return {
        "cus_balance": total_balance
    }


@router.put("/UpdateCustomerInvoice/{invoice_id}")
async def update_customer_invoice(
    invoice_id: str,
    e_name: str = None,
    e_amount: float = None,
    note: str = None,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a customer invoice by ID
    Required by JavaScript frontend
    """
    from sqlalchemy import select
    import json
    from uuid import UUID

    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    # Get the invoice to update
    statement = select(CustomerInvoice).where(CustomerInvoice.id == invoice_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Update fields if provided
    if e_name is not None:
        invoice.invoice_no = e_name
    if e_amount is not None:
        if e_amount < 0:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Amount cannot be negative"
            )
        # Update totals JSON with new amount
        try:
            totals_data = json.loads(invoice.totals)
        except (json.JSONDecodeError, TypeError):
            totals_data = {}

        totals_data['total'] = e_amount
        totals_data['subtotal'] = e_amount  # Simplified calculation
        invoice.totals = json.dumps(totals_data)
    if note is not None:
        # Validate note length
        if len(note) > 1000:  # Example limit
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Note too long"
            )
        invoice.notes = note

    # Update timestamp
    invoice.updated_at = datetime.now()

    await db.commit()
    await db.refresh(invoice)

    # Parse items and totals for response
    try:
        items_data = json.loads(invoice.items)
    except (json.JSONDecodeError, TypeError):
        items_data = []

    try:
        totals_data = json.loads(invoice.totals)
    except (json.JSONDecodeError, TypeError):
        totals_data = {}

    # Format the response
    return {
        "invoice_id": str(invoice.id),
        "invoice_no": invoice.invoice_no,
        "customer_id": str(invoice.customer_id) if invoice.customer_id else None,
        "salesman_id": str(invoice.salesman_id) if invoice.salesman_id else None,
        "items": items_data,
        "totals": totals_data,
        "taxes": float(invoice.taxes) if invoice.taxes else 0.0,
        "discounts": float(invoice.discounts) if invoice.discounts else 0.0,
        "status": invoice.status.value if hasattr(invoice.status, 'value') else invoice.status,
        "payment_method": invoice.payment_method,
        "notes": invoice.notes or "",
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "updated_at": invoice.updated_at.isoformat() if invoice.updated_at else None
    }


# Customer Order Endpoints (specifically for the JavaScript content provided)

@router.get("/Getorder/{id}")
async def get_order(
    id: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve specific order details by ID (customer invoice)
    Required by JavaScript frontend
    """
    from uuid import UUID
    from ..models.customer_invoice import CustomerInvoice
    from sqlalchemy import select
    import json

    try:
        order_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format"
        )

    # Get the customer invoice from the database
    statement = select(CustomerInvoice).where(CustomerInvoice.id == order_id)
    result = await db.execute(statement)
    invoice_record = result.scalar_one_or_none()

    if not invoice_record:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Parse the items JSON to extract order details
    items_data = []
    try:
        items_data = json.loads(invoice_record.items)
    except:
        items_data = []

    # Parse the totals JSON
    totals_data = {}
    try:
        totals_data = json.loads(invoice_record.totals)
    except:
        totals_data = {}

    # Include the new payment tracking fields in the response
    # Update totals to include actual payment status from database fields
    updated_totals = {
        "subtotal": totals_data.get('subtotal', 0.0),
        "tax": totals_data.get('tax', 0.0),
        "discount": totals_data.get('discount', 0.0),
        "total": float(invoice_record.total_amount) if invoice_record.total_amount else 0.0,
        "amount_paid": float(invoice_record.amount_paid) if invoice_record.amount_paid else 0.0,
        "balance_due": float(invoice_record.balance_due) if invoice_record.balance_due else 0.0,
        "payment_status": invoice_record.payment_status
    }

    # Map to the expected frontend fields
    order_data = {
        "orderid": str(invoice_record.id),
        "status": invoice_record.status.value if hasattr(invoice_record.status, 'value') else invoice_record.status,
        "fields": {
            "items": items_data,
            "totals": updated_totals,
            "taxes": float(invoice_record.taxes) if invoice_record.taxes else 0.0,
            "discounts": float(invoice_record.discounts) if invoice_record.discounts else 0.0,
            "payment_method": invoice_record.payment_method,
            "notes": invoice_record.notes or ""
        }
    }

    return order_data


@router.get("/viewcustomerorder")
async def view_customer_order(
    searchString: str = None,
    order_status: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    View customer orders (customer invoices) with optional search and status filtering
    Required by JavaScript frontend
    """
    from ..models.customer_invoice import CustomerInvoice
    from sqlalchemy import select, func
    import json

    # Validate pagination parameters
    if skip < 0:
        skip = 0
    if limit <= 0:
        limit = 100
    elif limit > 200:  # Set maximum limit for security
        limit = 200

    # Build query with filters - now using CustomerInvoice instead of CustomOrder
    count_statement = select(func.count()).select_from(CustomerInvoice)

    # Apply search filter if provided - searching in items JSON or invoice details
    if searchString:
        # Use parameterized queries to prevent SQL injection - sanitize input
        sanitized_search = searchString.replace('%', '\\%').replace('_', '\\_')
        count_statement = count_statement.where(CustomerInvoice.items.ilike(f"%{sanitized_search}%"))

    # Apply status filter if provided - using the status field from CustomerInvoice
    if order_status:
        from ..models.customer_invoice import CustomerInvoiceStatus
        try:
            status_enum = CustomerInvoiceStatus(order_status.upper())
            count_statement = count_statement.where(CustomerInvoice.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invalid status value"
            )

    # Get total count
    total_count_result = await db.execute(count_statement)
    total_count = total_count_result.scalar() or 0

    # Build query for fetching data
    statement = select(CustomerInvoice)

    # Apply same filters as count query
    if searchString:
        sanitized_search = searchString.replace('%', '\\%').replace('_', '\\_')
        statement = statement.where(CustomerInvoice.items.ilike(f"%{sanitized_search}%"))

    if order_status:
        try:
            status_enum = CustomerInvoiceStatus(order_status.upper())
            statement = statement.where(CustomerInvoice.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Invalid status value"
            )

    # Apply pagination
    statement = statement.offset(skip).limit(limit).order_by(CustomerInvoice.created_at.desc())

    result = await db.execute(statement)
    invoices = result.scalars().all()

    # Format the response to match expected frontend structure with required fields
    result = []
    for invoice in invoices:
        items_data = []
        try:
            items_data = json.loads(invoice.items)
        except (json.JSONDecodeError, TypeError):
            items_data = []

        # Calculate total quantity across all items
        total_quantity = 0
        for item in items_data:
            quantity = item.get('quantity', 0)
            total_quantity += int(quantity) if quantity else 0

        # Extract the first item's product name as the order name for simplicity
        order_name = ""
        if items_data and len(items_data) > 0:
            first_item = items_data[0]
            order_name = first_item.get('product_name', first_item.get('pro_name', ''))

        # Get customer name associated with this invoice
        customer_name = getattr(invoice, 'customer_name', 'Unknown Customer')
        if not customer_name:
            # If customer name is not directly in the invoice, we can get it from the customer table
            from sqlalchemy import select
            from ..models.customer import Customer
            customer_stmt = select(Customer).where(Customer.id == invoice.customer_id)
            customer_result = await db.execute(customer_stmt)
            customer = customer_result.scalar_one_or_none()
            customer_name = customer.name if customer else 'Unknown Customer'

        # Get team name associated with this invoice
        team_name = getattr(invoice, 'team_name', 'No Team')

        result.append({
            "orderid": str(invoice.id),
            "invoice_no": invoice.invoice_no,
            "status": invoice.status.value if hasattr(invoice.status, 'value') else invoice.status,
            "customer": customer_name,
            "teamname": team_name,
            "quantity": total_quantity,
            "total_amount": float(invoice.total_amount) if invoice.total_amount else 0.0,
            "date": invoice.created_at.isoformat().split('T')[0] if invoice.created_at else None,  # Date only (YYYY-MM-DD)
            "fields": {
                "order_name": order_name,
                "items": items_data,
                "total_amount": float(invoice.total_amount) if invoice.total_amount else 0.0  # Use actual field instead of parsed JSON
            },
            "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
            "updated_at": invoice.updated_at.isoformat() if invoice.updated_at else None
        })

    # Calculate total pages (ceiling division)
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 0
    current_page = (skip // limit) + 1 if limit > 0 else 1

    return {
        "data": result,
        "page": current_page,
        "limit": limit,
        "total": total_count,
        "total_pages": total_pages,
        "has_more": current_page < total_pages
    }


@router.get("/customerorderreport")
async def customer_order_report(
    orderid: str = None,
    timezone: str = None,
    printoption: str = None,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate customer order report in PDF format
    Required by JavaScript frontend
    """
    from sqlalchemy import select
    import base64
    import json

    # If order ID is provided, get specific order details
    order_details = None
    if orderid:
        try:
            from uuid import UUID
            order_uuid = UUID(orderid)

            statement = select(CustomerInvoice).where(CustomerInvoice.id == order_uuid)
            result = await db.execute(statement)
            order = result.scalar_one_or_none()

            if order:
                fields_data = {}
                try:
                    fields_data = json.loads(order.fields)
                except:
                    fields_data = {}

                order_details = {
                    "orderid": str(order.id),
                    "status": order.status.value if hasattr(order.status, 'value') else order.status,
                    "fields": fields_data,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                    "updated_at": order.updated_at.isoformat() if order.updated_at else None
                }
        except:
            pass  # If order ID is invalid, continue with general report

    # Generate a simple PDF report (base64 encoded)
    pdf_content = "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    pdf_content += "2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    pdf_content += "3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
    pdf_content += "4 0 obj\n<<\n/Length 60\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Customer Order Report) Tj\nET\nendstream\nendobj\n"
    pdf_content += "xref\n0 5\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n%%EOF"

    # Encode to base64
    encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

    return encoded_pdf


@router.post("/Deletecustomorder/{id}")
async def delete_custom_order_endpoint(
    id: str,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a customer invoice by ID (mapped to work with customer invoices)
    Required by JavaScript frontend
    """
    from sqlalchemy import select
    from uuid import UUID
    from ..models.customer_invoice import CustomerInvoice

    try:
        invoice_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    # Get the customer invoice to delete
    statement = select(CustomerInvoice).where(CustomerInvoice.id == invoice_id)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Delete the invoice
    await db.delete(invoice)
    await db.commit()

    return {
        "success": True,
        "message": "Customer invoice deleted successfully"
    }


@router.put("/UpdateCustomerInvoice/{id}")
async def update_customer_invoice(
    id: str,
    request_data: dict,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update customer invoice details
    Required by JavaScript frontend
    """
    from sqlalchemy import select
    from uuid import UUID
    from ..models.customer_invoice import CustomerInvoice
    import json

    try:
        invoice_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    # Get the customer invoice to update
    statement = select(CustomerInvoice).where(CustomerInvoice.id == invoice_id)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Update fields from request
    e_name = request_data.get('e_name')
    e_amount = request_data.get('e_amount')
    note = request_data.get('note')

    if e_name:
        invoice.customer_name = e_name
    if e_amount:
        invoice.total_amount = float(e_amount)
    if note:
        # Update fields JSON
        try:
            fields_data = json.loads(invoice.fields)
        except:
            fields_data = {}
        fields_data['note'] = note
        invoice.fields = json.dumps(fields_data)

    await db.commit()
    await db.refresh(invoice)

    return {
        "success": True,
        "message": "Customer invoice updated successfully",
        "invoice_id": str(invoice.id)
    }


# Additional endpoints required by the JavaScript frontend

@router.post("/Customers")
async def create_customer_from_modal(
    request_data: dict,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new customer from the modal
    Required by JavaScript frontend
    """
    from ..services.customer_service import CustomerService
    from ..models.customer import CustomerCreate
    import json

    # Extract data from request body
    cus_name = request_data.get('cus_name')
    cus_phone = request_data.get('cus_phone')
    cus_address = request_data.get('cus_address')
    cus_cnic = request_data.get('cus_cnic')
    cus_sal_id_fk = request_data.get('cus_sal_id_fk')
    branch = request_data.get('branch')

    # Validate required fields
    if not cus_name:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Customer name is required"
        )
    if not cus_phone:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Customer phone is required"
        )
    if not cus_address:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Customer address is required"
        )
    if not cus_cnic:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Customer CNIC is required"
        )

    # Create contact information
    contacts = {
        "phone": cus_phone,
        "email": "",
        "address": cus_address
    }

    # Convert sal_id_fk to UUID if provided
    sal_id_uuid = None
    if cus_sal_id_fk:
        try:
            sal_id_uuid = uuid.UUID(cus_sal_id_fk)
        except ValueError:
            sal_id_uuid = None

    # Create customer data - match CustomerCreate model fields
    customer_data = CustomerCreate(
        name=cus_name,
        contacts=json.dumps(contacts),
        cnic=cus_cnic,
        sal_id_fk=sal_id_uuid,
        branch=branch
    )

    # Create the customer
    created_customer = await CustomerService.create_customer(db, customer_data, str(current_user.id))

    return {
        "success": True,
        "cus_id": str(created_customer.id),
        "cus_name": created_customer.name,
        "cus_phone": cus_phone,
        "cus_address": cus_address,
        "cus_cnic": cus_cnic,
        "cus_sal_id_fk": cus_sal_id_fk,
        "branch": branch
    }


@router.post("/GetSalesmanDetails")
async def get_salesman_details(
    request_data: dict,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get salesman details by name
    Required by JavaScript frontend
    """
    sal_name = request_data.get('sal_name')
    if not sal_name:
        return {"error": "Salesman name is required"}

    # Find salesman by name
    from sqlalchemy import select
    from ..models.salesman import Salesman

    statement = select(Salesman).where(Salesman.name.ilike(f"%{sal_name}%"))
    result = await db.execute(statement)
    salesman = result.scalar_one_or_none()

    if salesman:
        return {
            "sal_id": str(salesman.id),
            "sal_name": salesman.name,
            "sal_phone": salesman.phone or "",
            "sal_address": salesman.address or "",
            "branch": salesman.branch or ""
        }
    else:
        return {"error": "Salesman not found"}


@router.post("/customerbalance")
async def customer_balance(
    request_data: dict,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get customer balance by name
    Required by JavaScript frontend
    """
    from sqlalchemy import select
    import json

    cus_name = request_data.get('cus_name')
    if not cus_name:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Customer name is required"
        )

    # Find customer by name (exact match first, then partial if needed)
    from ..models.customer import Customer
    # First try exact match - use scalars().first() instead of scalar_one_or_none()
    statement = select(Customer).where(Customer.name == cus_name)
    result = await db.execute(statement)
    customer = result.scalars().first()

    # If no exact match, try partial match - sanitize input to prevent SQL injection
    if not customer:
        sanitized_name = cus_name.replace('%', '\\%').replace('_', '\\_')
        statement = select(Customer).where(Customer.name.ilike(f"%{sanitized_name}%"))
        result = await db.execute(statement)
        customer = result.scalars().first()

    if customer:
        # In the current model, we're using credit_limit as a proxy for balance
        balance = float(customer.credit_limit) if customer.credit_limit else 0.0

        return {
            "cus_id": str(customer.id),
            "cus_balance": balance
        }
    else:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )


@router.get("/customerbalance/{customer_id}")
async def get_customer_balance(
    customer_id: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get customer balance across all orders
    """
    from sqlalchemy import select
    import json
    from uuid import UUID

    try:
        customer_uuid = UUID(customer_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer ID format"
        )

    # Get all invoices for this customer
    statement = select(CustomerInvoice).where(
        CustomerInvoice.customer_id == customer_uuid
    )

    result = await db.execute(statement)
    invoices = result.scalars().all()

    # Calculate total balance and prepare orders list
    total_balance = 0.0
    total_orders = len(invoices)
    orders_list = []

    for invoice in invoices:
        # Parse totals JSON to get the actual total
        try:
            totals_data = json.loads(invoice.totals)
            invoice_total = totals_data.get('total', 0.0)
        except:
            invoice_total = 0.0

        order_info = {
            "order_id": str(invoice.id),
            "invoice_no": invoice.invoice_no,
            "order_total": float(invoice.total_amount) if invoice.total_amount else 0.0,
            "amount_paid": float(invoice.amount_paid) if invoice.amount_paid else 0.0,
            "balance_due": float(invoice.balance_due) if invoice.balance_due else 0.0,
            "status": invoice.payment_status,
            "created_date": invoice.created_at.isoformat() if invoice.created_at else None
        }

        total_balance += float(invoice.balance_due) if invoice.balance_due else 0.0
        orders_list.append(order_info)

    # Get customer name
    from ..models.customer import Customer
    customer_stmt = select(Customer).where(Customer.id == customer_uuid)
    customer_result = await db.execute(customer_stmt)
    customer = customer_result.scalar_one_or_none()
    customer_name = customer.name if customer else ""

    return {
        "customer_id": customer_id,
        "customer_name": customer_name,
        "total_balance": total_balance,
        "total_orders": total_orders,
        "orders": orders_list
    }


@router.get("/customerorders/{customer_id}")
async def get_customer_orders(
    customer_id: str,
    skip: int = 0,
    limit: int = 10,
    searchString: str = None,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all orders for a specific customer with pagination
    """
    from sqlalchemy import select, func
    from uuid import UUID
    import json

    try:
        customer_uuid = UUID(customer_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer ID format"
        )

    # Validate pagination parameters
    if skip < 0:
        skip = 0
    if limit <= 0:
        limit = 10
    elif limit > 200:
        limit = 200

    # Get total count
    count_statement = select(func.count()).select_from(CustomerInvoice).where(
        CustomerInvoice.customer_id == customer_uuid
    )
    
    # Apply search filter if provided
    if searchString:
        sanitized_search = searchString.replace('%', '\\%').replace('_', '\\_')
        count_statement = count_statement.where(CustomerInvoice.items.ilike(f"%{sanitized_search}%"))
    
    total_count_result = await db.execute(count_statement)
    total_count = total_count_result.scalar() or 0

    # Get invoices for this customer with pagination
    statement = select(CustomerInvoice).where(
        CustomerInvoice.customer_id == customer_uuid
    )
    
    # Apply search filter if provided
    if searchString:
        sanitized_search = searchString.replace('%', '\\%').replace('_', '\\_')
        statement = statement.where(CustomerInvoice.items.ilike(f"%{sanitized_search}%"))
    
    statement = statement.order_by(CustomerInvoice.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(statement)
    invoices = result.scalars().all()

    # Prepare orders list
    orders_list = []
    from ..models.customer import Customer
    customer_stmt = select(Customer).where(Customer.id == customer_uuid)
    customer_result = await db.execute(customer_stmt)
    customer = customer_result.scalar_one_or_none()
    customer_name = customer.name if customer else ""

    for invoice in invoices:
        # Parse items to get quantity
        items_data = []
        try:
            items_data = json.loads(invoice.items)
        except (json.JSONDecodeError, TypeError):
            items_data = []

        total_quantity = sum(item.get('quantity', 0) for item in items_data)

        order_info = {
            "orderid": str(invoice.id),
            "invoice_no": invoice.invoice_no,
            "status": invoice.status.value if hasattr(invoice.status, 'value') else invoice.status,
            "customer": customer_name,
            "teamname": getattr(invoice, 'team_name', 'No Team'),
            "quantity": total_quantity,
            "total_amount": float(invoice.total_amount) if invoice.total_amount else 0.0,
            "amount_paid": float(invoice.amount_paid) if invoice.amount_paid else 0.0,
            "balance_due": float(invoice.balance_due) if invoice.balance_due else 0.0,
            "payment_status": invoice.payment_status,
            "date": invoice.created_at.isoformat().split('T')[0] if invoice.created_at else None,
            "created_at": invoice.created_at.isoformat() if invoice.created_at else None
        }
        orders_list.append(order_info)

    # Calculate pagination
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 0
    current_page = (skip // limit) + 1 if limit > 0 else 1

    return {
        "data": orders_list,
        "page": current_page,
        "limit": limit,
        "total": total_count,
        "total_pages": total_pages,
        "has_more": current_page < total_pages
    }


@router.get("/order-details/{order_id}")
async def get_order_details(
    order_id: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information for a specific order
    """
    from sqlalchemy import select
    from uuid import UUID
    import json

    try:
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format"
        )

    # Get the invoice
    statement = select(CustomerInvoice).where(
        CustomerInvoice.id == order_uuid
    )

    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Parse items and payment history
    items_data = []
    try:
        items_data = json.loads(invoice.items)
    except:
        items_data = []

    payment_history = []
    try:
        payment_history = json.loads(invoice.payments_history)
    except:
        payment_history = []

    # Get customer name
    from ..models.customer import Customer
    customer_stmt = select(Customer).where(Customer.id == invoice.customer_id)
    customer_result = await db.execute(customer_stmt)
    customer = customer_result.scalar_one_or_none()
    customer_name = customer.name if customer else ""

    return {
        "order_id": str(invoice.id),
        "invoice_no": invoice.invoice_no,
        "customer_name": customer_name,
        "items": items_data,
        "order_total": float(invoice.total_amount) if invoice.total_amount else 0.0,
        "amount_paid": float(invoice.amount_paid) if invoice.amount_paid else 0.0,
        "balance_due": float(invoice.balance_due) if invoice.balance_due else 0.0,
        "payment_history": payment_history,
        "status": invoice.payment_status
    }


@router.put("/process-payment/{order_id}")
async def process_payment(
    order_id: str,
    payment_data: dict,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Process a payment for an existing order
    """
    from sqlalchemy import select
    from uuid import UUID
    from decimal import Decimal
    import json
    from datetime import datetime

    try:
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format"
        )

    # Get the invoice
    statement = select(CustomerInvoice).where(
        CustomerInvoice.id == order_uuid
    )

    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Extract payment data from request body
    amount = payment_data.get("amount")
    payment_method = payment_data.get("payment_method", "cash")
    description = payment_data.get("description", "")
    payment_date = payment_data.get("payment_date")

    # Validate required fields
    if amount is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Amount is required in payment data"
        )

    # Validate payment amount
    if amount <= 0:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Payment amount must be greater than zero"
        )

    # Ensure amount doesn't exceed balance due
    if amount > float(invoice.balance_due):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount ({amount}) exceeds balance due ({float(invoice.balance_due)})"
        )

    # Update payment fields
    previous_balance = invoice.balance_due
    new_amount_paid = invoice.amount_paid + Decimal(str(amount))
    new_balance_due = invoice.balance_due - Decimal(str(amount))

    # Update payment status
    if float(new_balance_due) <= 0:
        new_payment_status = "paid"
    else:
        new_payment_status = "partial" if float(invoice.amount_paid) > 0 or amount > 0 else "unpaid"

    # Add to payment history
    try:
        payment_history = json.loads(invoice.payments_history)
    except (json.JSONDecodeError, TypeError):
        payment_history = []

    # Set payment date
    if payment_date:
        try:
            # Handle various date formats
            if payment_date.endswith('Z'):
                payment_datetime = datetime.fromisoformat(payment_date.replace('Z', '+00:00'))
            elif '+' in payment_date or '-' in payment_date[10:]:  # Has timezone offset
                payment_datetime = datetime.fromisoformat(payment_date)
            else:
                # Assume it's a simple date string like "2024-01-01"
                payment_datetime = datetime.fromisoformat(payment_date)
        except ValueError:
            payment_datetime = datetime.now()
    else:
        payment_datetime = datetime.now()

    # Validate and sanitize inputs
    if not payment_method or len(payment_method) > 50:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment method"
        )

    if len(description) > 500:  # Limit description length
        description = description[:500]

    new_payment = {
        "amount": float(amount),
        "payment_method": str(payment_method),
        "date": payment_datetime.isoformat(),
        "description": str(description)
    }
    payment_history.append(new_payment)

    # Update the invoice
    invoice.amount_paid = new_amount_paid
    invoice.balance_due = new_balance_due
    invoice.payment_status = new_payment_status
    invoice.payments_history = json.dumps(payment_history)
    invoice.updated_at = datetime.now()

    await db.commit()
    await db.refresh(invoice)

    return {
        "order_id": str(invoice.id),
        "invoice_no": invoice.invoice_no,
        "previous_balance": float(previous_balance),
        "payment_received": float(amount),
        "new_balance": float(new_balance_due),
        "total_paid": float(new_amount_paid),
        "payment_status": invoice.payment_status,
        "payment_record": new_payment,
        "updated_payment_history": payment_history
    }


@router.get("/payment-history/{order_id}")
async def get_payment_history(
    order_id: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get payment history for an invoice
    """
    from sqlalchemy import select
    from uuid import UUID
    from ..models.customer_invoice import CustomerInvoice
    import json

    try:
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format"
        )

    # Get the invoice
    statement = select(CustomerInvoice).where(CustomerInvoice.id == order_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Parse payment history
    try:
        payment_history = json.loads(invoice.payments_history)
    except (json.JSONDecodeError, TypeError):
        payment_history = []

    return {
        "invoice_id": str(invoice.id),
        "invoice_no": invoice.invoice_no,
        "total_amount": float(invoice.total_amount) if invoice.total_amount else 0.0,
        "amount_paid": float(invoice.amount_paid) if invoice.amount_paid else 0.0,
        "balance_due": float(invoice.balance_due) if invoice.balance_due else 0.0,
        "payment_status": invoice.payment_status,
        "payments_history": payment_history
    }


@router.put("/update-status/{order_id}")
async def update_order_status(
    order_id: str,
    request_data: dict,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update order status (pending, delivered, completed, cancel)
    """
    from sqlalchemy import select
    from uuid import UUID
    from ..models.customer_invoice import CustomerInvoice, CustomerInvoiceStatus

    try:
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format"
        )

    # Get the invoice
    statement = select(CustomerInvoice).where(CustomerInvoice.id == order_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Get new status from request
    new_status = request_data.get('status')
    if not new_status:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Status is required"
        )

    # Validate and update status
    try:
        invoice.status = CustomerInvoiceStatus(new_status.upper())
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Must be one of: PENDING, DELIVERED, COMPLETED, CANCEL"
        )

    invoice.updated_at = datetime.now()
    await db.commit()
    await db.refresh(invoice)

    return {
        "success": True,
        "message": "Order status updated successfully",
        "order_id": str(invoice.id),
        "new_status": invoice.status.value
    }


@router.get("/daily-collection-report/{date}")
async def daily_collection_report(
    date: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all payments collected on a specific date
    """
    from sqlalchemy import select
    import json
    from datetime import datetime
    from ..models.customer import Customer

    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD."
        )

    # Get all invoices that have payments on the specified date
    # We'll need to search through all invoices' payment histories
    all_invoices_stmt = select(CustomerInvoice)
    result = await db.execute(all_invoices_stmt)
    invoices = result.scalars().all()

    collections = []
    total_collections = 0.0

    for invoice in invoices:
        try:
            payment_history = json.loads(invoice.payments_history)
        except (json.JSONDecodeError, TypeError):
            continue

        # Filter payments made on the target date
        for payment in payment_history:
            try:
                payment_date = datetime.fromisoformat(payment['date']).date()
                if payment_date == target_date:
                    # Get customer name - use a join query to avoid N+1 problem
                    customer_stmt = select(Customer).where(Customer.id == invoice.customer_id)
                    customer_result = await db.execute(customer_stmt)
                    customer = customer_result.scalar_one_or_none()
                    customer_name = customer.name if customer else ""

                    collections.append({
                        "order_id": str(invoice.id),
                        "invoice_no": str(invoice.invoice_no),
                        "customer_name": str(customer_name),
                        "amount": float(payment['amount']),
                        "payment_method": str(payment['payment_method']),
                        "description": str(payment.get('description', '')),
                        "time": str(payment['date'])
                    })
                    total_collections += float(payment['amount'])
            except (ValueError, KeyError, TypeError):
                continue

    return {
        "date": date,
        "total_collections": total_collections,
        "collection_count": len(collections),
        "collections": collections
    }


@router.get("/payment-history/{order_id}")
async def get_payment_history(
    order_id: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get payment history for a specific order
    """
    from sqlalchemy import select
    from uuid import UUID
    import json

    try:
        order_uuid = UUID(order_id)
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid order ID format"
        )

    # Get the invoice
    statement = select(CustomerInvoice).where(
        CustomerInvoice.id == order_uuid
    )

    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    try:
        payment_history = json.loads(invoice.payments_history)
    except:
        payment_history = []

    return payment_history


@router.get("/customerinvoicesbydate")
async def get_customer_invoices_by_date(
    date: str,
    current_user: User = Depends(cashier_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all customer invoices for a specific date with total amounts
    """
    from sqlalchemy import select, func, and_
    import json
    from datetime import datetime, date as date_type

    try:
        # Parse the date string to ensure it's valid
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD."
        )

    # Query invoices created on the specific date - use database functions to avoid timezone issues
    statement = select(CustomerInvoice).where(
        func.date(CustomerInvoice.created_at) == target_date
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
                "customer_id": str(invoice.customer_id) if invoice.customer_id else None,
                "total_amount": float(invoice_total),
                "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
                "products": products_list
            })
        except (ValueError, TypeError):
            # If parsing fails for this invoice, skip its amount in total
            continue

    return {
        "date": date,
        "total_invoices": len(invoice_list),
        "total_amount": total_amount,
        "invoices": invoice_list
    }