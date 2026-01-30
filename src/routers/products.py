from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.product import Product, ProductCreate, ProductUpdate, ProductRead
from ..models.user import User  # Import User at the top to avoid NameError
from ..services.product_service import ProductService
from ..auth.auth import get_current_user
from ..auth.rbac import admin_required, cashier_required, employee_required

router = APIRouter()

@router.get("/", response_model=List[ProductRead])
def get_products(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(cashier_required()),  # Cashiers and above can view products
    db: Session = Depends(get_db)
):
    """
    Get list of products with pagination
    Cashiers, employees, and admins can view products
    """
    products = ProductService.get_products(db, skip=skip, limit=limit)
    return products

@router.post("/", response_model=ProductRead)
def create_product(
    product_create: ProductCreate,
    current_user: User = Depends(admin_required()),  # Only admins can create products
    db: Session = Depends(get_db)
):
    """
    Create a new product
    Requires admin role
    """
    # Check if SKU already exists
    existing_product = ProductService.get_product_by_sku(db, product_create.sku)
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product with this SKU already exists"
        )

    return ProductService.create_product(db, product_create)

@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: str,
    current_user: User = Depends(cashier_required()),  # Cashiers and above can view product details
    db: Session = Depends(get_db)
):
    """
    Get a specific product by ID
    Cashiers, employees, and admins can view product details
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    product = ProductService.get_product(db, product_uuid)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return product

@router.put("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: str,
    product_update: ProductUpdate,
    current_user: User = Depends(admin_required()),  # Only admins can update products
    db: Session = Depends(get_db)
):
    """
    Update a specific product by ID
    Requires admin role
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    product = ProductService.get_product(db, product_uuid)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return ProductService.update_product(db, product_uuid, product_update)

@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    current_user: User = Depends(admin_required()),  # Only admins can delete products
    db: Session = Depends(get_db)
):
    """
    Delete a specific product by ID
    Requires admin role
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    success = ProductService.delete_product(db, product_uuid)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return {"message": "Product deleted successfully"}

# Import statement needed for User type hint
from ..models.user import User