from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
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

# Import statement needed for User type hint
from ..models.user import User