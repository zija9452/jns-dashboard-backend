from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from uuid import UUID
import uuid
import json

from ..database.database import get_db
from ..models.user import User
from ..models.vendor import Vendor, VendorCreate, VendorUpdate, VendorRead
from ..services.vendor_service import VendorService
from ..auth.session_auth import get_current_user_from_session, admin_required_from_session, cashier_required_from_session, employee_required_from_session, admin_cashier_employee_required_from_session

router = APIRouter()

@router.get("/", response_model=List[VendorRead])
async def get_vendors(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required_from_session()),  # Only admins can view vendors
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of vendors with pagination
    Requires admin role
    """
    vendors = await VendorService.get_vendors(db, skip=skip, limit=limit)
    return vendors

@router.post("/", response_model=VendorRead)
async def create_vendor(
    vendor_create: VendorCreate,
    current_user: User = Depends(admin_required_from_session()),  # Only admins can create vendors
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new vendor
    Requires admin role
    """
    return await VendorService.create_vendor(db, vendor_create, str(current_user.id))

# Endpoints required by the JavaScript frontend (MUST be before dynamic routes)

@router.get("/viewvendor")
async def view_vendors(
    search_string: Optional[str] = None,
    branches: Optional[str] = None,
    searchphone: Optional[str] = None,
    searchaddress: Optional[str] = None,
    page: int = 1,
    limit: int = 10000,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    View vendors with search and branch filtering
    Required by JavaScript frontend
    Returns: Paginated data + total count for proper frontend pagination
    Same approach as /products/viewproduct
    """
    # Calculate skip from page
    skip = (page - 1) * limit

    # Build base query
    base_statement = select(Vendor)

    # Apply branch filter at database level
    if branches:
        base_statement = base_statement.where(Vendor.branch == branches)

    # Apply search filters at database level
    if search_string and search_string.strip():
        search_pattern = f"%{search_string.strip()}%"
        base_statement = base_statement.where(Vendor.name.ilike(search_pattern))

    # Get total count
    count_statement = select(Vendor.id)
    if branches:
        count_statement = count_statement.where(Vendor.branch == branches)
    if search_string and search_string.strip():
        search_pattern = f"%{search_string.strip()}%"
        count_statement = count_statement.where(Vendor.name.ilike(search_pattern))

    count_result = await db.execute(count_statement)
    total_count = len(count_result.scalars().all())

    # Apply pagination at database level
    statement = base_statement.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(statement)
    vendors = result.scalars().all()

    # Format the response for the JavaScript frontend
    result_list = []
    for vendor in vendors:
        contacts_data = {}
        try:
            contacts_data = json.loads(vendor.contacts)
        except:
            contacts_data = {"phone": "", "email": "", "address": ""}

        vendor_data = {
            "ven_id": str(vendor.id),
            "ven_name": vendor.name,
            "ven_phone": contacts_data.get("phone", ""),
            "ven_address": contacts_data.get("address", ""),
            "branch": getattr(vendor, 'branch', '') or '',
            "vend_balance": float(vendor.balance) if hasattr(vendor, 'balance') and vendor.balance else 0.0
        }

        result_list.append(vendor_data)

    # Calculate total pages
    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    # Prepare response with pagination info
    response_data = {
        'data': result_list,
        'page': page,
        'limit': limit,
        'total': total_count,
        'totalPages': total_pages
    }

    return response_data

@router.get("/getvendor/{id}")
async def get_vendor_details(
    id: str,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve specific vendor details by ID
    Required by JavaScript frontend
    """
    try:
        vendor_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor ID format"
        )

    vendor = await VendorService.get_vendor(db, vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    # Parse contacts JSON to extract phone and address
    import json
    contacts_data = {}
    try:
        contacts_data = json.loads(vendor.contacts)
    except:
        contacts_data = {"phone": "", "email": "", "address": ""}

    # Map to the expected frontend fields
    vendor_data = {
        "ven_id": str(vendor.id),
        "ven_name": vendor.name,
        "ven_phone": contacts_data.get("phone", ""),
        "ven_address": contacts_data.get("address", ""),
        "branch": getattr(vendor, 'branch', '') or ''  # Using getattr to safely access branch field
    }

    return vendor_data

@router.post("/deletevendor/{id}")
async def delete_vendor_frontend(
    id: str,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a vendor by ID (frontend compatible response)
    Required by JavaScript frontend
    """
    try:
        vendor_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor ID format"
        )

    success = await VendorService.delete_vendor(db, vendor_id, str(current_user.id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    return {
        "success": True,
        "message": "Vendor deleted successfully"
    }

@router.post("/getvendorbalance")
async def get_vendor_balance(
    branches: str = None,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get vendor balance by branch
    Required by JavaScript frontend
    """
    # In a real implementation, this would calculate actual vendor balances
    # For now, returning a default value
    if branches:
        balance = 5000.0  # Placeholder value
    else:
        balance = 10000.0  # Default placeholder value

    return {
        "cus_balance": balance  # Using cus_balance as per the frontend expectation
    }

@router.post("/vendorviewreport")
async def vendor_view_report(
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate vendor view report with actual vendor data in proper table format
    """
    import base64
    from datetime import datetime
    
    # Fetch all vendors
    vendors = await VendorService.get_vendors(db, skip=0, limit=10000)
    
    # Calculate total balance
    total_balance = 0.0
    
    # Build vendor rows for PDF table
    vendor_rows = ""
    for i, vendor in enumerate(vendors):
        import json
        contacts_data = {}
        try:
            contacts_data = json.loads(vendor.contacts)
        except:
            contacts_data = {"phone": "", "email": "", "address": ""}
        
        # Use actual vendor balance from database
        vendor_balance = float(vendor.balance) if hasattr(vendor, 'balance') and vendor.balance else 0.0
        total_balance += vendor_balance
        
        vendor_rows += f"""
        <tr>
            <td class="border">{i+1}</td>
            <td class="border">{vendor.name}</td>
            <td class="border">{contacts_data.get('phone', '')}</td>
            <td class="border">{contacts_data.get('address', '')}</td>
            <td class="border text-right">{vendor_balance:,.2f}</td>
        </tr>
        """
    
    # Add total row
    vendor_rows += f"""
        <tr class="total-row">
            <td class="border" colspan="4" style="text-align: right; font-weight: bold;">Total Market Balance:</td>
            <td class="border text-right" style="font-weight: bold;">{total_balance:,.2f}</td>
        </tr>
    """
    
    # Create HTML content for PDF with proper table styling
    current_date = datetime.now().strftime('%d-%m-%Y')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4 landscape;
                margin: 15mm;
            }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 15px;
                margin: 0;
                padding: 0;
            }}
            h1 {{
                text-align: center;
                color: #333;
                margin: 0 0 10px 0;
                font-size: 28px;
                font-weight: bold;
            }}
            .print-date {{
                text-align: right;
                margin-bottom: 15px;
                color: #666;
                font-size: 13px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            th {{
                background-color: #444;
                color: white;
                border: 2px solid #000;
                padding: 14px 12px;
                text-align: left;
                font-weight: bold;
                font-size: 16px;
            }}
            td {{
                border: 1px solid #000;
                padding: 12px;
                font-size: 15px;
            }}
            .border {{
                border: 1px solid #000;
            }}
            .text-right {{
                text-align: right;
            }}
            tr:nth-child(even) {{
                background-color: #f5f5f5;
            }}
            tr:nth-child(odd) {{
                background-color: #fff;
            }}
            .total-row {{
                background-color: #e0e0e0 !important;
                font-weight: bold;
                font-size: 16px;
            }}
            .footer {{
                margin-top: 20px;
                text-align: center;
                font-size: 13px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <h1>Vendor Details</h1>
        <div class="print-date"><strong>Print Date:</strong> {current_date}</div>
        <table>
            <thead>
                <tr>
                    <th style="width: 40px;">#</th>
                    <th>Vendor Name</th>
                    <th>Phone</th>
                    <th>Address</th>
                    <th style="width: 100px; text-align: right;">Balance</th>
                </tr>
            </thead>
            <tbody>
                {vendor_rows}
            </tbody>
        </table>
        <div class="footer">
            <p>Total Vendors: {len(vendors)}</p>
        </div>
    </body>
    </html>
    """
    
    # Try to use weasyprint if available, otherwise fallback to simple PDF
    try:
        from weasyprint import HTML
        from io import BytesIO
        
        # Generate PDF using weasyprint
        pdf_doc = HTML(string=html_content)
        pdf_bytes = pdf_doc.write_pdf()
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
        
    except ImportError:
        # Fallback to simple PDF if weasyprint is not installed
        pdf_content = "%PDF-1.4\n"
        pdf_content += "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        pdf_content += "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        pdf_content += "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 792 612] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        pdf_content += "4 0 obj\n<< /Length 300 >>\nstream\n"
        pdf_content += "BT\n/F1 18 Tf 350 550 Td (Vendor Details) Tj ET\n"
        pdf_content += "BT\n/F1 10 Tf 600 520 Td (Print Date: " + current_date + ") Tj ET\n"
        pdf_content += "BT\n/F1 12 Tf 50 480 Td (# | Vendor Name | Phone | Address | Balance) Tj ET\n"
        pdf_content += "BT\n/F1 10 Tf 50 460 Td (----------------------------------------------------) Tj ET\n"
        
        # Add vendor names in table format
        y_position = 430
        for i, vendor in enumerate(vendors[:15]):
            import json
            contacts_data = {}
            try:
                contacts_data = json.loads(vendor.contacts)
            except:
                pass
            
            # Use actual vendor balance
            vendor_balance = float(vendor.balance) if hasattr(vendor, 'balance') and vendor.balance else 0.0
            vendor_text = f"{i+1} | {vendor.name} | {contacts_data.get('phone', '')} | {getattr(vendor, 'branch', '') or 'N/A'} | {vendor_balance:,.2f}"
            pdf_content += f"BT\n/F1 9 Tf 50 {y_position} Td ({vendor_text}) Tj ET\n"
            y_position -= 18
        
        pdf_content += f"BT\n/F1 12 Tf 50 {y_position - 30} Td (Total Market Balance: {total_balance:,.2f}) Tj ET\n"
        pdf_content += "ET\nendstream\nendobj\n"
        pdf_content += "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        pdf_content += "xref\n0 6\ntrailer\n<< /Size 6 /Root 1 0 R >>\n%%EOF"
        
        encoded_pdf = base64.b64encode(pdf_content.encode()).decode()
    
    return encoded_pdf

# Standard REST API routes (MUST be after specific routes)
# IMPORTANT: Static routes MUST come before dynamic routes like {vendor_id}

@router.get("/all-payment-history")
async def get_all_vendor_payment_history(
    page: int = 1,
    limit: int = 10,
    vendor_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all vendor payment history with pagination
    Access: Admin, Cashier, Employee
    """
    from sqlalchemy import select

    # Calculate skip
    skip = (page - 1) * limit

    # Get all vendors
    vendors_result = await db.execute(select(Vendor))
    all_vendors = vendors_result.scalars().all()

    # Build payment list
    all_payments = []

    for vendor in all_vendors:
        # Filter by vendor_id if specified
        if vendor_id and str(vendor.id) != vendor_id:
            continue

        # Parse payment history
        payment_history = []
        try:
            payment_history = json.loads(vendor.payments_history) if vendor.payments_history else []
        except:
            payment_history = []

        # Add vendor info to each payment
        for payment in payment_history:
            payment_entry = {
                "vendor_id": str(vendor.id),
                "vendor_name": vendor.name,
                "payment_date": payment.get("date", ""),
                "datetime": payment.get("datetime", ""),
                "amount": payment.get("amount", 0),
                "payment_method": payment.get("payment_method", ""),
                "payment_type": payment.get("payment_type", ""),
                "description": payment.get("description", ""),
                "balance_after": payment.get("balance_after", 0)
            }

            # Apply search filter (search in vendor name and description)
            if search:
                search_lower = search.lower()
                if (search_lower not in vendor.name.lower() and
                    search_lower not in payment_entry["description"].lower()):
                    continue

            all_payments.append(payment_entry)

    # Sort by datetime (newest first)
    all_payments.sort(key=lambda x: x.get("datetime", "") or "", reverse=True)

    # Apply pagination
    total = len(all_payments)
    paginated_payments = all_payments[skip:skip + limit]

    return {
        "payments": paginated_payments,
        "total": total,
        "page": page,
        "limit": limit
    }


@router.get("/{vendor_id}", response_model=VendorRead)
async def get_vendor(
    vendor_id: str,
    current_user: User = Depends(admin_required_from_session()),  # Only admins can view vendor details
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific vendor by ID
    Requires admin role
    """
    try:
        vendor_uuid = UUID(vendor_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor ID format"
        )

    vendor = await VendorService.get_vendor(db, vendor_uuid)

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    return vendor

@router.put("/{vendor_id}", response_model=VendorRead)
async def update_vendor(
    vendor_id: str,
    vendor_update: VendorUpdate,
    current_user: User = Depends(admin_required_from_session()),  # Only admins can update vendors
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific vendor by ID
    Requires admin role
    """
    try:
        vendor_uuid = UUID(vendor_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor ID format"
        )

    vendor = await VendorService.get_vendor(db, vendor_uuid)

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    return await VendorService.update_vendor(db, vendor_uuid, vendor_update, str(current_user.id))

@router.delete("/{vendor_id}")
async def delete_vendor(
    vendor_id: str,
    current_user: User = Depends(admin_required_from_session()),  # Only admins can delete vendors
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific vendor by ID
    Requires admin role
    """
    try:
        vendor_uuid = UUID(vendor_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor ID format"
        )

    success = await VendorService.delete_vendor(db, vendor_uuid, str(current_user.id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    return {"message": "Vendor deleted successfully"}


@router.post("/process-payment/{vendor_id}")
async def process_vendor_payment(
    vendor_id: UUID,
    payment_data: dict,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Process vendor payment (similar to customer invoice payment)
    Access: Admin, Cashier, Employee
    
    Request Body:
    {
        "amount_paid": 5000.00,
        "payment_method": "Cash",
        "payment_type": "payment",  // or "reverse_payment"
        "date": "2026-03-31",
        "description": "Payment to vendor"
    }
    """
    from sqlalchemy import select
    import json
    from datetime import datetime
    
    # Get vendor
    vendor = await db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    # Extract payment data
    amount_paid = float(payment_data.get('amount_paid', 0))
    payment_method = payment_data.get('payment_method', 'Cash')
    payment_type = payment_data.get('payment_type', 'payment')
    payment_date = payment_data.get('date', datetime.now().strftime('%Y-%m-%d'))
    description = payment_data.get('description', '')
    
    if amount_paid <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount must be positive"
        )
    
    # Get current balance
    current_balance = float(vendor.balance)
    
    # Calculate new balance based on payment type
    if payment_type == 'payment':
        # Payment reduces vendor balance (we're paying them)
        new_balance = current_balance - amount_paid
    elif payment_type == 'reverse_payment':
        # Reverse payment increases vendor balance
        new_balance = current_balance + amount_paid
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payment type. Use 'payment' or 'reverse_payment'"
        )
    
    # Update vendor balance
    vendor.balance = new_balance
    
    # Add to payment history
    payment_history = []
    try:
        payment_history = json.loads(vendor.payments_history) if vendor.payments_history else []
    except:
        payment_history = []
    
    payment_history.append({
        "date": payment_date,
        "datetime": datetime.now().isoformat(),
        "amount": amount_paid,
        "payment_method": payment_method,
        "payment_type": payment_type,
        "description": description,
        "balance_after": new_balance,
        "created_by": str(current_user.id),
        "created_by_username": current_user.username
    })
    vendor.payments_history = json.dumps(payment_history)
    
    await db.commit()
    
    return {
        "message": "Vendor payment processed successfully",
        "vendor_id": str(vendor.id),
        "vendor_name": vendor.name,
        "amount_paid": amount_paid,
        "payment_method": payment_method,
        "payment_type": payment_type,
        "previous_balance": current_balance,
        "new_balance": new_balance,
        "payment_date": payment_date
    }


@router.get("/payment-history/{vendor_id}")
async def get_vendor_payment_history(
    vendor_id: UUID,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get vendor payment history
    Access: Admin, Cashier, Employee
    """
    import json
    
    # Get vendor
    vendor = await db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    # Parse payment history
    payment_history = []
    try:
        payment_history = json.loads(vendor.payments_history) if vendor.payments_history else []
    except:
        payment_history = []
    
    return {
        "vendor_id": str(vendor.id),
        "vendor_name": vendor.name,
        "current_balance": float(vendor.balance),
        "payment_history": payment_history
    }


@router.get("/viewvendorbalance")
async def view_vendor_balance(
    vendor_id: UUID,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get vendor current balance
    Access: Admin, Cashier, Employee
    """
    # Get vendor
    vendor = await db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )
    
    return {
        "vendor_id": str(vendor.id),
        "vendor_name": vendor.name,
        "balance": float(vendor.balance),
        "payments_history_count": len(json.loads(vendor.payments_history)) if vendor.payments_history else 0
    }