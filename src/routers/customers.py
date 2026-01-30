from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.user import User  # Import User at the top to avoid NameError
from ..models.customer import Customer, CustomerCreate, CustomerUpdate, CustomerRead
from ..services.customer_service import CustomerService
from ..auth.auth import get_current_user
from ..auth.rbac import admin_required, cashier_required, employee_required

router = APIRouter()

@router.get("/", response_model=List[CustomerRead])
def get_customers(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(cashier_required()),  # Cashiers and above can view customers
    db: Session = Depends(get_db)
):
    """
    Get list of customers with pagination
    Cashiers, employees, and admins can view customers
    """
    customers = CustomerService.get_customers(db, skip=skip, limit=limit)
    return customers

@router.post("/", response_model=CustomerRead)
def create_customer(
    customer_create: CustomerCreate,
    current_user: User = Depends(admin_required()),  # Only admins can create customers
    db: Session = Depends(get_db)
):
    """
    Create a new customer
    Requires admin role
    """
    return CustomerService.create_customer(db, customer_create)

@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(
    customer_id: str,
    current_user: User = Depends(cashier_required()),  # Cashiers and above can view customer details
    db: Session = Depends(get_db)
):
    """
    Get a specific customer by ID
    Cashiers, employees, and admins can view customer details
    """
    try:
        customer_uuid = UUID(customer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer ID format"
        )

    customer = CustomerService.get_customer(db, customer_uuid)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return customer

@router.put("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: str,
    customer_update: CustomerUpdate,
    current_user: User = Depends(employee_required()),  # Employees and above can update customers
    db: Session = Depends(get_db)
):
    """
    Update a specific customer by ID
    Requires employee or admin role
    """
    try:
        customer_uuid = UUID(customer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer ID format"
        )

    customer = CustomerService.get_customer(db, customer_uuid)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return CustomerService.update_customer(db, customer_uuid, customer_update)

@router.delete("/{customer_id}")
def delete_customer(
    customer_id: str,
    current_user: User = Depends(admin_required()),  # Only admins can delete customers
    db: Session = Depends(get_db)
):
    """
    Delete a specific customer by ID
    Requires admin role
    """
    try:
        customer_uuid = UUID(customer_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer ID format"
        )

    success = CustomerService.delete_customer(db, customer_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return {"message": "Customer deleted successfully"}