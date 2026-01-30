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

# Endpoints required by the JavaScript frontend

@router.get("/get-products/{id}")
def get_product_details(
    id: str,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Retrieve specific product details by ID
    Required by JavaScript frontend
    """
    try:
        product_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    product = ProductService.get_product(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Map to the expected frontend fields
    product_data = {
        "pro_id": str(product.id),
        "pro_name": product.name,
        "pro_price": float(product.unit_price),
        "pro_cost": float(product.cost_price),
        "pro_barcode": product.barcode or "",
        "pro_dis": float(product.discount) if product.discount else 0.0,
        "cat_id_fk": product.category or "",  # This should be the category ID
        "limitedquan": product.limited_qty,
        "branch": product.branch or "",
        "brand": product.brand_action or "",
        "pro_image": product.attributes or ""  # Using attributes field to store image path
    }

    return product_data

@router.get("/view-product")
def view_products(
    search_string: str = None,
    branches: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    View products with search and branch filtering
    Required by JavaScript frontend
    """
    # Get all products with pagination
    products = ProductService.get_products(db, skip=skip, limit=limit)

    # Apply filters
    filtered_products = []
    for product in products:
        # Apply branch filter if provided
        if branches and product.branch != branches:
            continue

        # Apply search filter if provided
        if search_string:
            search_lower = search_string.lower()
            if (search_lower not in product.name.lower() and
                search_lower not in (product.barcode or "").lower() and
                search_lower not in (product.sku or "").lower()):
                continue

        filtered_products.append(product)

    # Format the response to match expected frontend structure
    result = []
    for product in filtered_products:
        result.append({
            "pro_id": str(product.id),
            "pro_name": product.name,
            "pro_price": float(product.unit_price),
            "pro_cost": float(product.cost_price),
            "pro_barcode": product.barcode or "",
            "pro_dis": float(product.discount) if product.discount else 0.0,
            "cat_id_fk": product.category or "",
            "limitedquan": product.limited_qty,
            "branch": product.branch or "",
            "brand": product.brand_action or "",
            "pro_image": product.attributes or ""
        })

    return result

@router.get("/get-max-pro-id")
def get_max_pro_id(
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Get the maximum product ID for barcode calculation
    Required by JavaScript frontend
    """
    from sqlmodel import func

    # Query to get the maximum ID in the products table
    max_id_result = db.exec(func.max(Product.id)).first()

    if max_id_result:
        # Convert UUID to a numeric representation for the frontend
        # Using the integer representation of the UUID
        import uuid
        max_uuid = max_id_result
        # Take the last 8 characters of the UUID as a simple numeric-like ID
        max_id_str = str(max_uuid)[-8:]
        # Convert to integer if possible, or use a default value
        try:
            max_id_num = int(max_id_str, 16)  # Interpret as hex
        except ValueError:
            max_id_num = 1000  # Default fallback
    else:
        max_id_num = 1000  # Default if no products exist

    return max_id_num

@router.post("/delete-product/{id}")
def delete_product_frontend(
    id: str,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Delete a product by ID (frontend compatible response)
    Required by JavaScript frontend
    """
    try:
        product_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    success = ProductService.delete_product(db, product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return {
        "success": True,
        "message": "Product deleted successfully"
    }

@router.post("/delete-product-image/{id}")
def delete_product_image(
    id: str,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Delete product image by product ID
    Required by JavaScript frontend
    """
    try:
        product_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    product = ProductService.get_product(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Clear the image field (using attributes field to store image path)
    product.attributes = None

    db.add(product)
    db.commit()
    db.refresh(product)

    return {
        "success": True,
        "message": "Product image deleted successfully"
    }

@router.post("/brand")
def create_brand(
    brand: str = None,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Add a new brand
    Required by JavaScript frontend
    """
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brand name is required"
        )

    # In a real implementation, you would create a Brands table
    # For now, we'll return a success response with dummy ID
    return {
        "success": True,
        "ID": 1,  # Dummy ID - in real implementation this would be the actual brand ID
        "shelf": brand
    }

@router.post("/delete-brand")
def delete_brand(
    brand: str = None,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Delete a brand
    Required by JavaScript frontend
    """
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Brand name is required"
        )

    # In a real implementation, you would delete from a Brands table
    # For now, we'll return a success response
    return {
        "success": True,
        "message": f"Brand '{brand}' deleted successfully"
    }

@router.post("/get-stock-detail")
def get_stock_detail(
    pro_name: str = None,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Get stock details for a specific product
    Required by JavaScript frontend
    """
    if not pro_name:
        return {"error": "Product not found"}

    # Find product by name
    from sqlmodel import select
    statement = select(Product).where(Product.name.ilike(f"%{pro_name}%"))
    product = db.exec(statement).first()

    if product:
        return {
            "quantity": product.stock_level
        }
    else:
        return {"error": "Product not found"}

@router.get("/get-customer-vendor-by-branch")
def get_customer_vendor_by_branch(
    branch: str = None,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Get categories by branch
    Required by JavaScript frontend
    """
    # For now, return a mock response
    # In a real implementation, you would query actual category data
    categories = []

    # If branch is provided, filter categories by branch
    # Since we don't have a separate category table, we'll return mock data
    categories = [
        {"cat_id": "1", "cat_name": "Electronics"},
        {"cat_id": "2", "cat_name": "Clothing"},
        {"cat_id": "3", "cat_name": "Home & Garden"},
        {"cat_id": "4", "cat_name": "Books"},
        {"cat_id": "5", "cat_name": "Sports"}
    ]

    return {
        "categories": categories
    }