from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.invoice import Invoice, InvoiceCreate, InvoiceUpdate, InvoiceRead, InvoiceStatus
from ..services.invoice_service import InvoiceService
from ..auth.auth import get_current_user
from ..auth.rbac import admin_required, cashier_required, employee_required

router = APIRouter()

@router.get("/", response_model=List[InvoiceRead])
def get_invoices(
    customer_id: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(cashier_required()),  # Cashiers and above can view invoices
    db: Session = Depends(get_db)
):
    """
    Get list of invoices with pagination
    Optionally filter by customer_id
    Cashiers, employees, and admins can view invoices
    """
    customer_uuid = None
    if customer_id:
        try:
            customer_uuid = UUID(customer_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid customer ID format"
            )

    invoices = InvoiceService.get_invoices(db, customer_id=customer_uuid, skip=skip, limit=limit)
    return invoices

@router.post("/", response_model=InvoiceRead)
def create_invoice(
    invoice_create: InvoiceCreate,
    current_user: User = Depends(cashier_required()),  # Cashiers and above can create invoices
    db: Session = Depends(get_db)
):
    """
    Create a new invoice
    This adjusts stock levels for the products in the invoice
    Cashiers, employees, and admins can create invoices
    """
    return InvoiceService.create_invoice(db, invoice_create, current_user.id)

@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(
    invoice_id: str,
    current_user: User = Depends(cashier_required()),  # Cashiers and above can view invoice details
    db: Session = Depends(get_db)
):
    """
    Get a specific invoice by ID
    Cashiers, employees, and admins can view invoice details
    """
    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    invoice = InvoiceService.get_invoice(db, invoice_uuid)

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    return invoice

@router.put("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(
    invoice_id: str,
    invoice_update: InvoiceUpdate,
    current_user: User = Depends(employee_required()),  # Employees and above can update invoices
    db: Session = Depends(get_db)
):
    """
    Update a specific invoice by ID
    This may adjust stock levels if status changes
    Employees and admins can update invoices
    """
    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    invoice = InvoiceService.get_invoice(db, invoice_uuid)

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    return InvoiceService.update_invoice(db, invoice_uuid, invoice_update, current_user.id)

@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: str,
    current_user: User = Depends(admin_required()),  # Only admins can delete invoices
    db: Session = Depends(get_db)
):
    """
    Delete a specific invoice by ID
    This restores stock levels for the products in the invoice
    Requires admin role
    """
    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    success = InvoiceService.delete_invoice(db, invoice_uuid, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    return {"message": "Invoice deleted successfully"}

# Import statement needed for User type hint
from ..models.user import User