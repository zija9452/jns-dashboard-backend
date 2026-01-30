from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.user import User  # Import User at the top to avoid NameError
from ..models.refund import Refund, RefundCreate, RefundUpdate, RefundRead
from ..services.refund_service import RefundService
from ..auth.auth import get_current_user
from ..auth.rbac import admin_required, cashier_required, employee_required

router = APIRouter()

@router.get("/", response_model=List[RefundRead])
def get_refunds(
    invoice_id: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(employee_required()),  # Employees and above can view refunds
    db: Session = Depends(get_db)
):
    """
    Get list of refunds with pagination
    Optionally filter by invoice_id
    Employees and admins can view refunds
    """
    invoice_uuid = None
    if invoice_id:
        try:
            invoice_uuid = UUID(invoice_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid invoice ID format"
            )

    refunds = RefundService.get_refunds(db, invoice_id=invoice_uuid, skip=skip, limit=limit)
    return refunds

@router.post("/", response_model=RefundRead)
def create_refund(
    refund_create: RefundCreate,
    current_user: User = Depends(employee_required()),  # Employees and above can create refunds
    db: Session = Depends(get_db)
):
    """
    Create a new refund
    This adjusts stock levels for the products in the original invoice
    Employees and admins can create refunds
    """
    return RefundService.create_refund(db, refund_create, current_user.id)

@router.get("/{refund_id}", response_model=RefundRead)
def get_refund(
    refund_id: str,
    current_user: User = Depends(employee_required()),  # Employees and above can view refund details
    db: Session = Depends(get_db)
):
    """
    Get a specific refund by ID
    Employees and admins can view refund details
    """
    try:
        refund_uuid = UUID(refund_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refund ID format"
        )

    refund = RefundService.get_refund(db, refund_uuid)

    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )

    return refund

@router.put("/{refund_id}", response_model=RefundRead)
def update_refund(
    refund_id: str,
    refund_update: RefundUpdate,
    current_user: User = Depends(admin_required()),  # Only admins can update refunds
    db: Session = Depends(get_db)
):
    """
    Update a specific refund by ID
    Requires admin role
    """
    try:
        refund_uuid = UUID(refund_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refund ID format"
        )

    refund = RefundService.get_refund(db, refund_uuid)

    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )

    return RefundService.update_refund(db, refund_uuid, refund_update, current_user.id)

@router.delete("/{refund_id}")
def delete_refund(
    refund_id: str,
    current_user: User = Depends(admin_required()),  # Only admins can delete refunds
    db: Session = Depends(get_db)
):
    """
    Delete a specific refund by ID
    This adjusts stock levels back to the previous state
    Requires admin role
    """
    try:
        refund_uuid = UUID(refund_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid refund ID format"
        )

    success = RefundService.delete_refund(db, refund_uuid, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )

    return {"message": "Refund deleted successfully"}