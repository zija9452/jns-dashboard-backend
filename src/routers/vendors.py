from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.user import User  # Import User at the top to avoid NameError
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
    search_string: str = None,
    branches: str = None,
    searchphone: str = None,
    searchaddress: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    View vendors with search and branch filtering
    Required by JavaScript frontend
    """
    # Get all vendors with pagination
    vendors = await VendorService.get_vendors(db, skip=skip, limit=limit)

    # Apply filters
    filtered_vendors = []
    for vendor in vendors:
        # Apply branch filter if provided
        if branches:
            vendor_branch = getattr(vendor, 'branch', '')
            if vendor_branch != branches:
                continue

        # Apply search filters
        should_include = True
        if search_string:
            search_lower = search_string.lower()
            if search_lower not in vendor.name.lower():
                should_include = False

        if should_include and searchphone:
            import json
            try:
                contacts_data = json.loads(vendor.contacts)
                phone = contacts_data.get("phone", "")
                if searchphone not in phone:
                    should_include = False
            except:
                should_include = False

        if should_include and searchaddress:
            import json
            try:
                contacts_data = {}
                if vendor.contacts:
                    contacts_data = json.loads(vendor.contacts)
                address = contacts_data.get("address", "")
                if searchaddress not in address:
                    should_include = False
            except:
                should_include = False

        if should_include:
            filtered_vendors.append(vendor)

    # Format the response to match expected frontend structure
    result = []
    for vendor in filtered_vendors:
        import json
        contacts_data = {}
        try:
            contacts_data = json.loads(vendor.contacts)
        except:
            contacts_data = {"phone": "", "email": "", "address": ""}

        result.append({
            "ven_id": str(vendor.id),
            "ven_name": vendor.name,
            "ven_phone": contacts_data.get("phone", ""),
            "ven_address": contacts_data.get("address", ""),
            "branch": getattr(vendor, 'branch', ''),
            "vend_balance": 0.0  # Vendor balance
        })

    return result

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
    vendors = await VendorService.get_vendors(db, skip=0, limit=100)
    
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
        
        # For now, balance is 0 (you can implement actual balance calculation later)
        vendor_balance = 0.0
        total_balance += vendor_balance
        
        vendor_rows += f"""
        <tr>
            <td class="border">{i+1}</td>
            <td class="border">{vendor.name}</td>
            <td class="border">{contacts_data.get('phone', '')}</td>
            <td class="border">{contacts_data.get('address', '')}</td>
            <td class="border text-right">{vendor_balance:.2f}</td>
        </tr>
        """
    
    # Add total row
    vendor_rows += f"""
        <tr class="total-row">
            <td class="border" colspan="4" style="text-align: right; font-weight: bold;">Total Market Balance:</td>
            <td class="border text-right" style="font-weight: bold;">{total_balance:.2f}</td>
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
            vendor_text = f"{i+1} | {vendor.name} | {contacts_data.get('phone', '')} | {getattr(vendor, 'branch', '') or 'N/A'} | 0.00"
            pdf_content += f"BT\n/F1 9 Tf 50 {y_position} Td ({vendor_text}) Tj ET\n"
            y_position -= 18
        
        pdf_content += f"BT\n/F1 12 Tf 50 {y_position - 30} Td (Total Market Balance: {total_balance:.2f}) Tj ET\n"
        pdf_content += "ET\nendstream\nendobj\n"
        pdf_content += "5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        pdf_content += "xref\n0 6\ntrailer\n<< /Size 6 /Root 1 0 R >>\n%%EOF"
        
        encoded_pdf = base64.b64encode(pdf_content.encode()).decode()
    
    return encoded_pdf

# Standard REST API routes (MUST be after specific routes)

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