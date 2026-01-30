from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.user import User  # Import User at the top to avoid NameError
from ..models.vendor import Vendor, VendorCreate, VendorUpdate, VendorRead
from ..services.vendor_service import VendorService
from ..auth.auth import get_current_user
from ..auth.rbac import admin_required, cashier_required, employee_required

router = APIRouter()

@router.get("/", response_model=List[VendorRead])
def get_vendors(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(employee_required()),  # Employees and above can view vendors
    db: Session = Depends(get_db)
):
    """
    Get list of vendors with pagination
    Employees and admins can view vendors
    """
    vendors = VendorService.get_vendors(db, skip=skip, limit=limit)
    return vendors

@router.post("/", response_model=VendorRead)
def create_vendor(
    vendor_create: VendorCreate,
    current_user: User = Depends(admin_required()),  # Only admins can create vendors
    db: Session = Depends(get_db)
):
    """
    Create a new vendor
    Requires admin role
    """
    return VendorService.create_vendor(db, vendor_create)

@router.get("/{vendor_id}", response_model=VendorRead)
def get_vendor(
    vendor_id: str,
    current_user: User = Depends(employee_required()),  # Employees and above can view vendor details
    db: Session = Depends(get_db)
):
    """
    Get a specific vendor by ID
    Employees and admins can view vendor details
    """
    try:
        vendor_uuid = UUID(vendor_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor ID format"
        )

    vendor = VendorService.get_vendor(db, vendor_uuid)

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    return vendor

@router.put("/{vendor_id}", response_model=VendorRead)
def update_vendor(
    vendor_id: str,
    vendor_update: VendorUpdate,
    current_user: User = Depends(admin_required()),  # Only admins can update vendors
    db: Session = Depends(get_db)
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

    vendor = VendorService.get_vendor(db, vendor_uuid)

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    return VendorService.update_vendor(db, vendor_uuid, vendor_update)

@router.delete("/{vendor_id}")
def delete_vendor(
    vendor_id: str,
    current_user: User = Depends(admin_required()),  # Only admins can delete vendors
    db: Session = Depends(get_db)
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

    success = VendorService.delete_vendor(db, vendor_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    return {"message": "Vendor deleted successfully"}

# Endpoints required by the JavaScript frontend

@router.get("/get-vendor/{id}")
def get_vendor_details(
    id: str,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
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

    vendor = VendorService.get_vendor(db, vendor_id)
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

@router.get("/view-vendor")
def view_vendors(
    search_string: str = None,
    branches: str = None,
    searchphone: str = None,
    searchaddress: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    View vendors with search and branch filtering
    Required by JavaScript frontend
    """
    # Get all vendors with pagination
    vendors = VendorService.get_vendors(db, skip=skip, limit=limit)

    # Apply filters
    filtered_vendors = []
    for vendor in vendors:
        # Apply branch filter if provided
        if branches:
            # For now, assuming there's a branch field in vendor model
            # In a real implementation, you would check the actual branch field
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
            "branch": getattr(vendor, 'branch', '')
        })

    return result

@router.post("/delete-vendor/{id}")
def delete_vendor_frontend(
    id: str,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
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

    success = VendorService.delete_vendor(db, vendor_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    return {
        "success": True,
        "message": "Vendor deleted successfully"
    }

@router.post("/get-vendor-balance")
def get_vendor_balance(
    branches: str = None,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Get vendor balance by branch
    Required by JavaScript frontend
    """
    # In a real implementation, this would calculate actual vendor balances
    # For now, returning a default value
    if branches:
        # If branch is specified, you might filter vendors by branch
        # and calculate the total balance for that branch
        balance = 5000.0  # Placeholder value
    else:
        balance = 10000.0  # Default placeholder value

    return {
        "cus_balance": balance  # Using cus_balance as per the frontend expectation
    }

@router.post("/vendor-view-report")
def vendor_view_report(
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Generate vendor view report
    Required by JavaScript frontend
    """
    # In a real implementation, this would generate a PDF report
    # For now, returning a placeholder response
    # This would typically involve creating a PDF and returning base64 encoded data

    # Placeholder response - in real implementation, this would generate an actual report
    import base64
    # Create a simple placeholder PDF content (this is just a minimal PDF header)
    pdf_content = "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    pdf_content += "2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    pdf_content += "3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
    pdf_content += "4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Vendor Report) Tj\nET\nendstream\nendobj\n"
    pdf_content += "xref\n0 5\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n%%EOF"

    # Encode to base64
    encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

    return encoded_pdf