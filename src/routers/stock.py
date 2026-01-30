from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.user import User  # Import User at the top to avoid NameError
from ..models.stock_entry import StockEntry, StockEntryCreate, StockEntryUpdate, StockEntryRead
from ..services.stock_service import StockService
from ..auth.auth import get_current_user
from ..auth.rbac import admin_required, cashier_required, employee_required

router = APIRouter()

@router.get("/", response_model=List[StockEntryRead])
def get_stock_entries(
    product_id: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(employee_required()),  # Employees and above can view stock
    db: Session = Depends(get_db)
):
    """
    Get list of stock entries with pagination
    Optionally filter by product_id
    Employees and admins can view stock entries
    """
    product_uuid = None
    if product_id:
        try:
            product_uuid = UUID(product_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid product ID format"
            )

    stock_entries = StockService.get_stock_entries(db, product_id=product_uuid, skip=skip, limit=limit)
    return stock_entries

@router.post("/", response_model=StockEntryRead)
def create_stock_entry(
    stock_entry_create: StockEntryCreate,
    current_user: User = Depends(admin_required()),  # Only admins can create stock entries
    db: Session = Depends(get_db)
):
    """
    Create a new stock entry
    This adjusts stock levels for the associated product
    Requires admin role
    """
    return StockService.create_stock_entry(db, stock_entry_create)

@router.get("/{stock_id}", response_model=StockEntryRead)
def get_stock_entry(
    stock_id: str,
    current_user: User = Depends(employee_required()),  # Employees and above can view stock details
    db: Session = Depends(get_db)
):
    """
    Get a specific stock entry by ID
    Employees and admins can view stock entry details
    """
    try:
        stock_uuid = UUID(stock_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid stock entry ID format"
        )

    stock_entry = StockService.get_stock_entry(db, stock_uuid)

    if not stock_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock entry not found"
        )

    return stock_entry

@router.put("/{stock_id}", response_model=StockEntryRead)
def update_stock_entry(
    stock_id: str,
    stock_entry_update: StockEntryUpdate,
    current_user: User = Depends(admin_required()),  # Only admins can update stock entries
    db: Session = Depends(get_db)
):
    """
    Update a specific stock entry by ID
    This will also adjust the product stock level accordingly
    Requires admin role
    """
    try:
        stock_uuid = UUID(stock_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid stock entry ID format"
        )

    stock_entry = StockService.get_stock_entry(db, stock_uuid)

    if not stock_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock entry not found"
        )

    return StockService.update_stock_entry(db, stock_uuid, stock_entry_update)

@router.delete("/{stock_id}")
def delete_stock_entry(
    stock_id: str,
    current_user: User = Depends(admin_required()),  # Only admins can delete stock entries
    db: Session = Depends(get_db)
):
    """
    Delete a specific stock entry by ID
    This will adjust the product stock level back to the previous state
    Requires admin role
    """
    try:
        stock_uuid = UUID(stock_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid stock entry ID format"
        )

    success = StockService.delete_stock_entry(db, stock_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stock entry not found"
        )

    return {"message": "Stock entry deleted successfully"}