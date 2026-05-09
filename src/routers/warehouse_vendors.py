from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
import uuid
from sqlalchemy import select, or_, func
import json
import base64
from datetime import datetime

from ..database.database import get_db
from ..models.user import User
from ..models.warehouse_vendor import WarehouseVendor, WarehouseVendorCreate, WarehouseVendorUpdate, WarehouseVendorRead
from ..services.warehouse_vendor_service import WarehouseVendorService
from ..auth.session_auth import admin_required_from_session, admin_employee_warehouse_required_from_session

router = APIRouter()

@router.get("/", response_model=List[WarehouseVendorRead])
async def get_vendors(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Get list of warehouse vendors with pagination"""
    return await WarehouseVendorService.get_vendors(db, skip=skip, limit=limit)

@router.get("/viewvendor")
async def view_vendors(
    search_string: str = None,
    branches: str = None,
    page: int = 1,
    limit: int = 10000,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """View warehouse vendors with search and branch filtering"""
    skip = (page - 1) * limit
    base_statement = select(WarehouseVendor)

    if branches:
        base_statement = base_statement.where(WarehouseVendor.branch == branches)

    if search_string and search_string.strip():
        search_pattern = f"%{search_string.strip()}%"
        base_statement = base_statement.where(WarehouseVendor.name.ilike(search_pattern))

    count_statement = select(func.count()).select_from(base_statement.subquery())
    count_result = await db.execute(count_statement)
    total_count = count_result.scalar() or 0

    statement = base_statement.offset(skip).limit(limit)
    result = await db.execute(statement)
    vendors = result.scalars().all()

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
            "branch": vendor.branch or "",
            "vend_balance": float(vendor.balance or 0.0)
        }
        result_list.append(vendor_data)

    total_pages = (total_count + limit - 1) // limit if limit > 0 else 1

    return {
        'data': result_list,
        'page': page,
        'limit': limit,
        'total': total_count,
        'totalPages': total_pages
    }

@router.get("/all-payment-history")
async def get_all_vendor_payment_history(
    page: int = 1,
    limit: int = 10,
    vendor_id: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get all warehouse vendor payment history with pagination
    Access: Admin, Employee, Warehouse
    """
    from sqlalchemy import select

    # Calculate skip
    skip = (page - 1) * limit

    # Get all vendors
    vendors_result = await db.execute(select(WarehouseVendor))
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

@router.post("/", response_model=WarehouseVendorRead)
async def create_vendor(
    vendor_create: WarehouseVendorCreate,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Create a new warehouse vendor"""
    return await WarehouseVendorService.create_vendor(db, vendor_create, str(current_user.id))

@router.get("/{vendor_id}", response_model=WarehouseVendorRead)
async def get_vendor(
    vendor_id: str,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific warehouse vendor by ID"""
    try:
        vendor_uuid = UUID(vendor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid vendor ID format")

    vendor = await WarehouseVendorService.get_vendor(db, vendor_uuid)
    if not vendor:
        raise HTTPException(status_code=404, detail="Warehouse vendor not found")
    return vendor

@router.put("/{vendor_id}", response_model=WarehouseVendorRead)
async def update_vendor(
    vendor_id: str,
    vendor_update: WarehouseVendorUpdate,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Update a specific warehouse vendor by ID"""
    try:
        vendor_uuid = UUID(vendor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid vendor ID format")

    vendor = await WarehouseVendorService.update_vendor(db, vendor_uuid, vendor_update, str(current_user.id))
    if not vendor:
        raise HTTPException(status_code=404, detail="Warehouse vendor not found")
    return vendor

@router.delete("/{vendor_id}")
async def delete_vendor(
    vendor_id: str,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Delete a specific warehouse vendor by ID"""
    try:
        vendor_uuid = UUID(vendor_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid vendor ID format")

    success = await WarehouseVendorService.delete_vendor(db, vendor_uuid, str(current_user.id))
    if not success:
        raise HTTPException(status_code=404, detail="Warehouse vendor not found")
    return {"message": "Warehouse vendor deleted successfully"}

@router.post("/process-payment/{vendor_id}")
async def process_vendor_payment(
    vendor_id: UUID,
    payment_data: dict,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Process warehouse vendor payment
    Access: Admin, Employee, Warehouse
    """
    import json
    from datetime import datetime
    
    # Get vendor
    vendor = await db.get(WarehouseVendor, vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse vendor not found"
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
    current_balance = float(vendor.balance or 0.0)
    
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
        "message": "Warehouse vendor payment processed successfully",
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
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get warehouse vendor payment history
    Access: Admin, Employee, Warehouse
    """
    import json
    
    # Get vendor
    vendor = await db.get(WarehouseVendor, vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse vendor not found"
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
        "current_balance": float(vendor.balance or 0.0),
        "payment_history": payment_history
    }

@router.get("/viewvendorbalance")
async def view_vendor_balance(
    vendor_id: UUID,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get warehouse vendor current balance
    Access: Admin, Employee, Warehouse
    """
    # Get vendor
    vendor = await db.get(WarehouseVendor, vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse vendor not found"
        )
    
    return {
        "vendor_id": str(vendor.id),
        "vendor_name": vendor.name,
        "balance": float(vendor.balance or 0.0),
        "payments_history_count": len(json.loads(vendor.payments_history)) if vendor.payments_history else 0
    }

@router.post("/vendorviewreport")
async def vendor_view_report(
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """Generate warehouse vendor view report PDF"""
    vendors = await WarehouseVendorService.get_vendors(db, skip=0, limit=10000)
    
    total_balance = sum(float(v.balance or 0.0) for v in vendors)

    vendor_rows = ""
    for i, vendor in enumerate(vendors):
        contacts_data = {}
        try:
            contacts_data = json.loads(vendor.contacts)
        except:
            contacts_data = {"phone": "", "email": "", "address": ""}

        vendor_rows += f"""
        <tr>
            <td class="border">{i+1}</td>
            <td class="border">{vendor.name}</td>
            <td class="border">{contacts_data.get('phone', '')}</td>
            <td class="border">{contacts_data.get('address', '')}</td>
            <td class="border">{vendor.branch or ''}</td>
            <td class="border text-right">{float(vendor.balance or 0.0):.2f}</td>
        </tr>
        """
    
    vendor_rows += f"""
        <tr class="total-row">
            <td class="border" colspan="5" style="text-align: right; font-weight: bold;">Total Balance:</td>
            <td class="border text-right" style="font-weight: bold;">{total_balance:.2f}</td>
        </tr>
    """
    
    current_date = datetime.now().strftime('%d-%m-%Y')
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{ size: A4 landscape; margin: 15mm; }}
            body {{ font-family: Arial, sans-serif; font-size: 15px; }}
            h1 {{ text-align: center; font-weight: bold; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th {{ background-color: #444; color: white; border: 1px solid #000; padding: 10px; }}
            td {{ border: 1px solid #000; padding: 10px; }}
            .text-right {{ text-align: right; }}
            .total-row {{ background-color: #e0e0e0; font-weight: bold; }}
        </style>
    </head>
    <body>
        <h1>Warehouse Vendor Details</h1>
        <div style="text-align: right;"><strong>Print Date:</strong> {current_date}</div>
        <table>
            <thead>
                <tr>
                    <th style="width: 40px;">#</th>
                    <th>Vendor Name</th>
                    <th>Phone</th>
                    <th>Address</th>
                    <th>Branch</th>
                    <th style="width: 100px; text-align: right;">Balance</th>
                </tr>
            </thead>
            <tbody>
                {vendor_rows}
            </tbody>
        </table>
    </body>
    </html>
    """
    
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html_content).write_pdf()
        return base64.b64encode(pdf_bytes).decode()
    except:
        return base64.b64encode(b"PDF Generation Error").decode()
