from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.custom_order import CustomOrder, CustomOrderCreate, CustomOrderUpdate, CustomOrderRead, CustomOrderStatus
from ..services.custom_order_service import CustomOrderService
from ..auth.auth import get_current_user
from ..auth.rbac import admin_required, cashier_required, employee_required

router = APIRouter()

@router.get("/", response_model=List[CustomOrderRead])
def get_custom_orders(
    status: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(employee_required()),  # Employees and above can view custom orders
    db: Session = Depends(get_db)
):
    """
    Get list of custom orders with pagination
    Optionally filter by status
    Employees and admins can view custom orders
    """
    status_enum = None
    if status:
        try:
            status_enum = CustomOrderStatus(status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Valid statuses are: {[s.value for s in CustomOrderStatus]}"
            )

    custom_orders = CustomOrderService.get_custom_orders(db, status=status_enum, skip=skip, limit=limit)
    return custom_orders

@router.post("/", response_model=CustomOrderRead)
def create_custom_order(
    custom_order_create: CustomOrderCreate,
    current_user: User = Depends(employee_required()),  # Employees and above can create custom orders
    db: Session = Depends(get_db)
):
    """
    Create a new custom order
    Employees and admins can create custom orders
    """
    return CustomOrderService.create_custom_order(db, custom_order_create, current_user.id)

@router.get("/{custom_order_id}", response_model=CustomOrderRead)
def get_custom_order(
    custom_order_id: str,
    current_user: User = Depends(employee_required()),  # Employees and above can view custom order details
    db: Session = Depends(get_db)
):
    """
    Get a specific custom order by ID
    Employees and admins can view custom order details
    """
    try:
        custom_order_uuid = UUID(custom_order_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid custom order ID format"
        )

    custom_order = CustomOrderService.get_custom_order(db, custom_order_uuid)

    if not custom_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom order not found"
        )

    return custom_order

@router.put("/{custom_order_id}", response_model=CustomOrderRead)
def update_custom_order(
    custom_order_id: str,
    custom_order_update: CustomOrderUpdate,
    current_user: User = Depends(employee_required()),  # Employees and above can update custom orders
    db: Session = Depends(get_db)
):
    """
    Update a specific custom order by ID
    Employees and admins can update custom orders
    """
    try:
        custom_order_uuid = UUID(custom_order_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid custom order ID format"
        )

    custom_order = CustomOrderService.get_custom_order(db, custom_order_uuid)

    if not custom_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom order not found"
        )

    return CustomOrderService.update_custom_order(db, custom_order_uuid, custom_order_update, current_user.id)

@router.delete("/{custom_order_id}")
def delete_custom_order(
    custom_order_id: str,
    current_user: User = Depends(admin_required()),  # Only admins can delete custom orders
    db: Session = Depends(get_db)
):
    """
    Delete a specific custom order by ID
    Requires admin role
    """
    try:
        custom_order_uuid = UUID(custom_order_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid custom order ID format"
        )

    success = CustomOrderService.delete_custom_order(db, custom_order_uuid, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Custom order not found"
        )

    return {"message": "Custom order deleted successfully"}

# Import statement needed for User type hint
from ..models.user import User