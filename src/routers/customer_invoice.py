from fastapi import APIRouter, Depends, HTTPException, status
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
from ..auth.auth import get_current_user
from ..auth.rbac import admin_required, employee_required
from ..services.customer_service import CustomerService
from ..services.salesman_service import SalesmanService

router = APIRouter()


@router.post("/GetCustomerDetails")
async def get_customer_details(
    cus_name: str = None,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get customer details by name
    Required by JavaScript frontend
    """
    if not cus_name:
        return {"error": "Customer name is required"}

    # Find customer by name
    from sqlalchemy import select
    statement = select(Customer).where(Customer.name.ilike(f"%{cus_name}%")).limit(1)
    result = await db.execute(statement)
    customer = result.scalar_one_or_none()

    if customer:
        # Parse contacts JSON to extract phone and other details
        contacts_data = {}
        try:
            contacts_data = json.loads(customer.contacts)
        except:
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
        return {"error": "Customer not found"}


@router.post("/Getsalesmandetail")
async def get_salesman_detail(
    sal_name: str = None,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get salesman details by name
    Required by JavaScript frontend
    """
    if not sal_name:
        return {"error": "Salesman name is required"}

    # Find salesman by name
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
        return {"error": "Salesman not found"}


@router.post("/SaveCustomerOrders")
async def save_customer_orders(
    orderItems: List[Dict] = None,
    timezone: str = None,
    Date: str = None,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Save customer orders (customer invoice creation)
    Required by JavaScript frontend
    """
    from sqlalchemy import select
    from decimal import Decimal

    if not orderItems:
        orderItems = []

    # Create customer invoice
    invoice_id = uuid.uuid4()

    # Process each order item
    items_list = []
    total_amount = Decimal('0')

    for item in orderItems:
        # Create item object
        item_obj = {
            "product_name": item.get('pro_name'),
            "quantity": int(item.get('pro_quantity', 0)),
            "unit_price": float(item.get('unit_price', 0)),
            "total_price": float(item.get('total_price', 0)),
            "discount": float(item.get('discount', 0)),
            "cat_name": item.get('cat_name'),
            "cricktshirt_Neckstyle": item.get('cricktshirt_Neckstyle'),
            "cricktshirt_sleeve": item.get('cricktshirt_sleeve'),
            "cricktshirt_bottom": item.get('cricktshirt_bottom'),
            "cricktshirt_fabric": item.get('cricktshirt_fabric'),
            "cricktrouser_style": item.get('cricktrouser_style'),
            "cricktrouser_style2": item.get('cricktrouser_style2'),
            "cricktrouser_bottom": item.get('cricktrouser_bottom'),
            "cricktrouser_pocket": item.get('cricktrouser_pocket'),
            "cricktrouser_fabric": item.get('cricktrouser_fabric'),
            "foottshirt_neckstyle": item.get('foottshirt_neckstyle'),
            "foottshirt_sleeves": item.get('foottshirt_sleeves'),
            "football_fabric": item.get('football_fabric'),
            "footshorts_style": item.get('footshorts_style'),
            "footshorts_pocket": item.get('footshorts_pocket'),
            "footballshort_fabric": item.get('footballshort_fabric'),
            "trackjack_style": item.get('trackjack_style'),
            "trackjack_waist": item.get('trackjack_waist'),
            "trackjack_pocket": item.get('trackjack_pocket'),
            "trackjack_bottom": item.get('trackjack_bottom'),
            "trackjack_fabric": item.get('trackjack_fabric'),
            "tracktrous_style": item.get('tracktrous_style'),
            "tracktrous_bottom": item.get('tracktrous_bottom'),
            "tracktrous_pocket": item.get('tracktrous_pocket'),
            "tracktrous_fabric": item.get('tracktrous_fabric'),
            "imgfile": item.get('imgfile'),
            "imgfile2": item.get('imgfile2'),
            "imgfile3": item.get('imgfile3'),
        }
        items_list.append(item_obj)
        total_amount += Decimal(str(item.get('total_price', 0)))

    # Calculate totals
    total_discount = sum(float(item.get('discount', 0)) for item in orderItems)
    net_amount = total_amount - Decimal(str(total_discount))

    # Generate unique sequential invoice number
    from sqlalchemy import func, select

    # Generate unique invoice number using date-based approach for real-world usage
    from datetime import datetime

    # Use date-based invoice number: CUSTINV-YYYYMMDD-XXX (e.g., CUSTINV-20260203-001)
    date_str = datetime.now().strftime("%Y%m%d")

    # Find the highest invoice number for today and increment the sequence
    today_pattern = f"CUSTINV-{date_str}-%"
    statement = select(func.max(CustomerInvoice.invoice_no)).where(
        CustomerInvoice.invoice_no.like(today_pattern)
    )
    result = await db.execute(statement)
    max_invoice_no = result.scalar_one_or_none()

    if max_invoice_no:
        # Extract the sequence number from existing format like "CUSTINV-20260203-001"
        try:
            # Split by dashes and get the sequence part (last part)
            parts = max_invoice_no.split("-")
            if len(parts) >= 3:
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
        seq_number = "001"  # Start with 001 if no invoices exist for today

    invoice_no = f"CUSTINV-{date_str}-{seq_number}"

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
            invoice_no = f"CUSTINV-{date_str}-{seq_number}"
            counter += 1
        else:
            break  # Found a unique number

    # Create customer invoice data
    invoice_data = {
        "id": invoice_id,
        "invoice_no": invoice_no,
        "customer_id": orderItems[0].get('or_cus_id_fk') if orderItems else None,  # Get customer ID from first item
        "salesman_id": orderItems[0].get('or_sal_id_fk') if orderItems and 'or_sal_id_fk' in orderItems[0] else None,  # Get salesman ID if available
        "items": json.dumps(items_list),
        "totals": json.dumps({
            "subtotal": float(total_amount),
            "tax": 0.0,
            "discount": total_discount,
            "total": float(net_amount)
        }),
        "taxes": Decimal('0'),
        "discounts": Decimal(str(total_discount)),
        "status": CustomerInvoiceStatus.ISSUED,  # Use the customer invoice status enum
        "payment_method": orderItems[0].get('payment_mod', 'cash') if orderItems else 'cash',
        "notes": orderItems[0].get('remarks', '') if orderItems and 'remarks' in orderItems[0] else '',
        "created_by": current_user.id,
        "created_at": datetime.now(),
        "updated_at": datetime.now()
    }

    # Add to database
    db_customer_invoice = CustomerInvoice(**{k: v for k, v in invoice_data.items() if k in ["id", "invoice_no", "customer_id", "salesman_id", "items", "totals", "taxes", "discounts", "status", "payment_method", "notes", "created_by", "created_at", "updated_at"]})
    db.add(db_customer_invoice)
    await db.commit()

    # Generate a simple PDF report (base64 encoded) as response
    pdf_content = "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    pdf_content += "2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    pdf_content += "3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
    pdf_content += "4 0 obj\n<<\n/Length 60\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Customer Invoice Report - " + datetime.now().strftime("%Y-%m-%d") + ") Tj\nET\nendstream\nendobj\n"
    pdf_content += "xref\n0 5\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n%%EOF"

    encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

    return encoded_pdf


@router.get("/ViewCustomerInvoices")
async def view_customer_invoices(
    customer_id: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    View customer invoices with optional customer filtering
    Required by JavaScript frontend
    """
    from sqlalchemy import select

    # Get customer invoices with pagination
    statement = select(CustomerInvoice).offset(skip).limit(limit)

    # Apply customer filter if provided
    if customer_id:
        try:
            customer_uuid = UUID(customer_id)
            statement = statement.where(CustomerInvoice.customer_id == customer_uuid)
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid customer ID format"
            )

    result = await db.execute(statement)
    invoices = result.scalars().all()

    # Format the response
    result = []
    for invoice in invoices:
        # Parse items and totals
        try:
            items_data = json.loads(invoice.items)
        except:
            items_data = []

        try:
            totals_data = json.loads(invoice.totals)
        except:
            totals_data = {}

        result.append({
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
        })

    return result


@router.get("/GetCustomerInvoice/{invoice_id}")
async def get_customer_invoice(
    invoice_id: str,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific customer invoice by ID
    Required by JavaScript frontend
    """
    from sqlalchemy import select

    try:
        invoice_uuid = UUID(invoice_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    # Get the invoice
    statement = select(CustomerInvoice).where(CustomerInvoice.id == invoice_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Parse items and totals
    try:
        items_data = json.loads(invoice.items)
    except:
        items_data = []

    try:
        totals_data = json.loads(invoice.totals)
    except:
        totals_data = {}

    # Format the response
    invoice_data = {
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

    return invoice_data


@router.post("/GetCustomerInvoiceBalance")
async def get_customer_invoice_balance(
    customer_id: str = None,
    current_user: User = Depends(admin_required()),
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
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
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
        except:
            # If parsing fails, skip this invoice
            continue

    return {
        "cus_balance": total_balance
    }


@router.put("/UpdateCustomerOrders/{invoice_id}")
async def update_customer_orders(
    invoice_id: str,
    order_items: List[Dict] = None,
    timezone: str = None,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update customer orders (invoice update)
    Required by JavaScript frontend
    """
    from sqlalchemy import select
    from uuid import UUID
    import json
    from datetime import datetime

    if not order_items:
        order_items = []

    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    # Find the existing invoice
    statement = select(Invoice).where(Invoice.id == invoice_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Update the invoice with new items
    updated_items = []
    total_amount = 0.0

    for item in order_items:
        updated_item = {
            "pro_name": item.get('pro_name'),
            "pro_quantity": int(item.get('pro_quantity', 0)),
            "unit_price": float(item.get('unit_price', 0)),
            "total_price": float(item.get('total_price', 0)),
            "discount": float(item.get('discount', 0)),
            "cat_name": item.get('cat_name'),
            "or_cus_id_fk": item.get('or_cus_id_fk'),
            "or_sal_id_fk": item.get('or_sal_id_fk'),
            "payment_mod": item.get('payment_mod', 'cash'),
            "remarks": item.get('remarks', '')
        }
        updated_items.append(updated_item)
        total_amount += updated_item['total_price']

    # Update the invoice
    invoice.items = json.dumps(updated_items)
    invoice.totals = json.dumps({
        "subtotal": total_amount,
        "tax": 0.0,
        "discount": sum(item['discount'] for item in updated_items),
        "total": total_amount  # Simplified calculation
    })
    invoice.updated_at = datetime.now()

    await db.commit()
    await db.refresh(invoice)

    # Generate updated receipt (PDF as base64)
    import base64
    pdf_content = "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    pdf_content += "2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    pdf_content += "3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
    pdf_content += "4 0 obj\n<<\n/Length 60\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Updated Customer Invoice Report - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ") Tj\nET\nendstream\nendobj\n"
    pdf_content += "xref\n0 5\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n%%EOF"

    encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

    return encoded_pdf


@router.delete("/DeleteCustomerOrders/{invoice_id}")
async def delete_customer_orders(
    invoice_id: str,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete customer orders (invoice deletion)
    Required by JavaScript frontend
    """
    from sqlalchemy import select, delete
    from uuid import UUID

    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    # Find the invoice to delete
    statement = select(Invoice).where(Invoice.id == invoice_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Delete the invoice
    delete_statement = delete(Invoice).where(Invoice.id == invoice_uuid)
    await db.execute(delete_statement)
    await db.commit()

    return {
        "success": True,
        "message": "Customer order deleted successfully"
    }


@router.post("/CustomerInvoicereport")
async def customer_invoice_report(
    cat_name: str = None,
    pro_name: str = None,
    ven_name: str = None,
    timezone: str = None,
    branches: str = None,
    shelf: str = None,
    current_user: User = Depends(admin_required()),  # Only admin can generate reports
    db: AsyncSession = Depends(get_db)
):
    """
    Generate customer invoice report in PDF format
    Required by JavaScript frontend
    """
    from ..models.customer_invoice import CustomerInvoice
    from sqlalchemy import select

    # Build query with filters
    statement = select(CustomerInvoice)

    if cat_name:
        # This would require joining with products to filter by category
        pass  # Add category filtering if needed
    if pro_name:
        # This would require joining with products to filter by product name
        pass  # Add product name filtering if needed
    if branches:
        # This would require filtering by branch if available
        pass  # Add branch filtering if needed

    result = await db.execute(statement)
    invoices = result.scalars().all()

    # Create HTML for PDF report
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Customer Invoice Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Customer Invoice Report</h1>
            <p>Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <table>
            <thead>
                <tr>
                    <th>Invoice ID</th>
                    <th>Invoice No</th>
                    <th>Customer ID</th>
                    <th>Items</th>
                    <th>Totals</th>
                    <th>Taxes</th>
                    <th>Discounts</th>
                    <th>Status</th>
                    <th>Payment Method</th>
                    <th>Notes</th>
                    <th>Created At</th>
                </tr>
            </thead>
            <tbody>
    """

    for invoice in invoices:
        # Parse totals JSON to extract individual values
        totals_data = {}
        try:
            totals_data = json.loads(invoice.totals)
        except:
            totals_data = {}

        html_content += f"""
                <tr>
                    <td>{str(invoice.id)}</td>
                    <td>{invoice.invoice_no}</td>
                    <td>{str(invoice.customer_id) if invoice.customer_id else ""}</td>
                    <td>{invoice.items[:50] + "..." if len(invoice.items) > 50 else invoice.items}</td>
                    <td>{json.dumps(totals_data)}</td>
                    <td>{float(invoice.taxes) if invoice.taxes else 0.0:.2f}</td>
                    <td>{float(invoice.discounts) if invoice.discounts else 0.0:.2f}</td>
                    <td>{invoice.status.value if hasattr(invoice.status, 'value') else invoice.status}</td>
                    <td>{invoice.payment_method}</td>
                    <td>{invoice.notes or ""}</td>
                    <td>{invoice.created_at.isoformat() if invoice.created_at else ""}</td>
                </tr>
        """

    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """

    # Generate PDF using weasyprint
    try:
        from weasyprint import HTML
        import base64

        pdf_bytes = HTML(string=html_content).write_pdf()
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
        return encoded_pdf
    except ImportError:
        # Fallback to simple PDF if weasyprint is not available
        import base64
        pdf_content = "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
        pdf_content += "2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
        pdf_content += "3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
        pdf_content += "4 0 obj\n<<\n/Length 100\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Customer Invoice Report - " + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ") Tj\nET\nendstream\nendobj\n"
        pdf_content += "xref\n0 5\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n%%EOF"

        encoded_pdf = base64.b64encode(pdf_content.encode()).decode()
        return encoded_pdf


@router.put("/UpdateCustomerInvoice/{invoice_id}")
async def update_customer_invoice(
    invoice_id: str,
    e_name: str = None,
    e_amount: float = None,
    note: str = None,
    current_user: User = Depends(admin_required()),
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    # Get the invoice to update
    statement = select(CustomerInvoice).where(CustomerInvoice.id == invoice_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Update fields if provided
    if e_name is not None:
        invoice.invoice_no = e_name
    if e_amount is not None:
        # Update totals JSON with new amount
        try:
            totals_data = json.loads(invoice.totals)
        except:
            totals_data = {}

        totals_data['total'] = e_amount
        totals_data['subtotal'] = e_amount  # Simplified calculation
        invoice.totals = json.dumps(totals_data)
    if note is not None:
        invoice.notes = note

    # Update timestamp
    invoice.updated_at = datetime.now()

    await db.commit()
    await db.refresh(invoice)

    # Parse items and totals for response
    try:
        items_data = json.loads(invoice.items)
    except:
        items_data = []

    try:
        totals_data = json.loads(invoice.totals)
    except:
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


@router.post("/DeleteCustomerInvoice/{invoice_id}")
async def delete_customer_invoice(
    invoice_id: str,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a customer invoice by ID
    Required by JavaScript frontend
    """
    from sqlalchemy import select
    from uuid import UUID

    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    # Get the invoice to delete
    statement = select(CustomerInvoice).where(CustomerInvoice.id == invoice_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Delete the invoice
    await db.delete(invoice)
    await db.commit()

    return {
        "success": True,
        "message": "Invoice deleted successfully"
    }