from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.salesman import Salesman, SalesmanCreate, SalesmanUpdate, SalesmanRead
from ..services.salesman_service import SalesmanService
from ..auth.auth import get_current_user
from ..auth.rbac import admin_required, cashier_required, employee_required

router = APIRouter()

@router.get("/", response_model=List[SalesmanRead])
def get_salesmen(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(employee_required()),  # Employees and above can view salesmen
    db: Session = Depends(get_db)
):
    """
    Get list of salesmen with pagination
    Employees and admins can view salesmen
    """
    salesmen = SalesmanService.get_salesmen(db, skip=skip, limit=limit)
    return salesmen

@router.post("/", response_model=SalesmanRead)
def create_salesman(
    salesman_create: SalesmanCreate,
    current_user: User = Depends(admin_required()),  # Only admins can create salesmen
    db: Session = Depends(get_db)
):
    """
    Create a new salesman
    Requires admin role
    """
    # Check if code already exists
    existing_salesman = SalesmanService.get_salesman_by_code(db, salesman_create.code)
    if existing_salesman:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Salesman with this code already exists"
        )

    return SalesmanService.create_salesman(db, salesman_create)

@router.get("/{salesman_id}", response_model=SalesmanRead)
def get_salesman(
    salesman_id: str,
    current_user: User = Depends(employee_required()),  # Employees and above can view salesman details
    db: Session = Depends(get_db)
):
    """
    Get a specific salesman by ID
    Employees and admins can view salesman details
    """
    try:
        salesman_uuid = UUID(salesman_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid salesman ID format"
        )

    salesman = SalesmanService.get_salesman(db, salesman_uuid)

    if not salesman:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesman not found"
        )

    return salesman

@router.put("/{salesman_id}", response_model=SalesmanRead)
def update_salesman(
    salesman_id: str,
    salesman_update: SalesmanUpdate,
    current_user: User = Depends(admin_required()),  # Only admins can update salesmen
    db: Session = Depends(get_db)
):
    """
    Update a specific salesman by ID
    Requires admin role
    """
    try:
        salesman_uuid = UUID(salesman_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid salesman ID format"
        )

    salesman = SalesmanService.get_salesman(db, salesman_uuid)

    if not salesman:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesman not found"
        )

    # Check if updating code and if new code already exists
    if salesman_update.code and salesman_update.code != salesman.code:
        existing_salesman = SalesmanService.get_salesman_by_code(db, salesman_update.code)
        if existing_salesman:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Salesman with this code already exists"
            )

    return SalesmanService.update_salesman(db, salesman_uuid, salesman_update)

@router.delete("/{salesman_id}")
def delete_salesman(
    salesman_id: str,
    current_user: User = Depends(admin_required()),  # Only admins can delete salesmen
    db: Session = Depends(get_db)
):
    """
    Delete a specific salesman by ID
    Requires admin role
    """
    try:
        salesman_uuid = UUID(salesman_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid salesman ID format"
        )

    success = SalesmanService.delete_salesman(db, salesman_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesman not found"
        )

    return {"message": "Salesman deleted successfully"}

# Import statement needed for User type hint
from ..models.user import User