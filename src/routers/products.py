from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
import uuid

from ..database.database import get_db
from ..models.product import Product, ProductCreate, ProductUpdate, ProductRead
from ..models.user import User  # Import User at the top to avoid NameError
from ..services.product_service import ProductService
from ..auth.session_auth import get_current_user_from_session, admin_required_from_session, employee_required_from_session, admin_cashier_employee_required_from_session
from sqlmodel import select

router = APIRouter()

@router.get("/", response_model=List[ProductRead])
async def get_products(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),  # Admins and cashiers can view products
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of products with pagination
    Admins and cashiers can view products
    """
    products = await ProductService.get_products(db, skip=skip, limit=limit)
    return products

@router.post("/", response_model=ProductRead)
async def create_product(
    product_create: ProductCreate,
    current_user: User = Depends(employee_required_from_session()),  # Admins and employees can create products
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new product
    Requires admin or employee role
    """
    # Check if SKU already exists
    existing_product = await ProductService.get_product_by_sku(db, product_create.sku)
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product with this SKU already exists"
        )

    return await ProductService.create_product(db, product_create, str(current_user.id))

# Specific routes that should come before the generic /{product_id} route to avoid conflicts
@router.get("/get-products/{id}")
async def get_product_details(
    id: UUID,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve specific product details by ID
    Required by JavaScript frontend
    """
    product = await ProductService.get_product(db, id)
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
async def view_products(
    search_string: str = None,
    branches: str = None,
    skip: int = 0,
    limit: int = 40,  # Fetch 40 products for frontend pagination (optimized)
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    View products with search and branch filtering
    Required by JavaScript frontend
    """
    # Build query with database-level filtering (much faster than in-memory filtering)
    statement = select(Product)

    # Apply branch filter at database level
    if branches:
        statement = statement.where(Product.branch == branches)

    # Apply search filter at database level (case-insensitive)
    if search_string:
        search_lower = search_string.lower()
        # Use simple LIKE instead of ilike for better performance on remote DB
        statement = statement.where(
            or_(
                Product.name.ilike(f"%{search_lower}%"),
                Product.barcode.ilike(f"%{search_lower}%"),
                Product.sku.ilike(f"%{search_lower}%")
            )
        )

    # Apply pagination at database level
    statement = statement.offset(skip).limit(limit)

    # Execute query with optimized options
    result = await db.execute(statement)
    products = result.scalars().all()

    # Format the response to match expected frontend structure
    # Note: Excluding pro_image for better performance (images can be large base64 strings)
    result_list = []
    for product in products:
        result_list.append({
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
            "pro_image": "",  # Empty string for better performance
            "stock": product.stock_level  # Add stock level
        })

    return result_list

@router.get("/get-max-pro-id")
async def get_max_pro_id(
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the maximum product ID for barcode calculation
    Required by JavaScript frontend
    """
    from sqlmodel import select
    from sqlalchemy import desc

    # Query to get the maximum ID in the products table ordered by creation date
    # Since UUIDs don't support MAX function, we order by created_at and get the latest
    result = await db.execute(select(Product).order_by(desc(Product.created_at)).limit(1))
    max_product = result.scalar_one_or_none()

    if max_product:
        # Generate a simple numeric ID based on the number of products
        # Or use a hash of the UUID converted to a number
        import uuid
        max_uuid = max_product.id
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

@router.get("/generate-barcode")
async def generate_barcode(
    current_user: User = Depends(employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a unique barcode for new products
    Uses auto-increment approach for production-ready sequential barcodes
    """
    barcode = await ProductService.generate_unique_barcode(db)
    return {"barcode": barcode}

@router.post("/delete-product/{id}")
async def delete_product_frontend(
    id: str,
    current_user: User = Depends(admin_required_from_session()),  # Keep as admin only for security
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a product by ID (frontend compatible response)
    Required by JavaScript frontend - admin only for security
    """
    try:
        product_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    success = await ProductService.delete_product(db, product_id, str(current_user.id))
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
async def delete_product_image(
    id: str,
    current_user: User = Depends(employee_required_from_session()),  # Allow employees to manage product images
    db: AsyncSession = Depends(get_db)
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

    product = await ProductService.get_product(db, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    # Clear the image field (using attributes field to store image path)
    product.attributes = None

    db.add(product)
    await db.commit()
    await db.refresh(product)

    return {
        "success": True,
        "message": "Product image deleted successfully"
    }

# Generic routes should come after specific routes to avoid conflicts
@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: str,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),  # Admins and cashiers can view product details
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific product by ID
    Admins and cashiers can view product details
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    product = await ProductService.get_product(db, product_uuid)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return product

@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: str,
    product_update: ProductUpdate,
    current_user: User = Depends(employee_required_from_session()),  # Admins and employees can update products
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific product by ID
    Requires admin or employee role
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    product = await ProductService.get_product(db, product_uuid)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return await ProductService.update_product(db, product_uuid, product_update, str(current_user.id))

@router.delete("/{product_id}")
async def delete_product(
    product_id: str,
    current_user: User = Depends(admin_required_from_session()),  # Only admins can delete products (more sensitive operation)
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific product by ID
    Requires admin role (sensitive operation)
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    success = await ProductService.delete_product(db, product_uuid, str(current_user.id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return {"message": "Product deleted successfully"}

# User import is already at the top of the file, removing duplicate

@router.post("/brand")
async def create_brand(
    brand: str = None,
    current_user: User = Depends(employee_required_from_session()),  # Allow employees to create brands
    db: AsyncSession = Depends(get_db)
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
async def delete_brand(
    brand: str = None,
    current_user: User = Depends(employee_required_from_session()),  # Allow employees to delete brands
    db: AsyncSession = Depends(get_db)
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
async def get_stock_detail(
    pro_name: str = None,
    current_user: User = Depends(employee_required_from_session()),  # Allow employees to check stock details
    db: AsyncSession = Depends(get_db)
):
    """
    Get stock details for a specific product
    Required by JavaScript frontend
    """
    if not pro_name:
        return {"error": "Product not found"}

    # Find product by name using case-insensitive search with ilike (PostgreSQL)
    from sqlmodel import select
    statement = select(Product).where(Product.name.ilike(f'%{pro_name}%'))
    result = await db.execute(statement)
    products = result.scalars().all()
    
    # Return the first matching product's stock level
    if products:
        product = products[0]  # Get the first match
        return {
            "quantity": product.stock_level
        }
    else:
        return {"error": "Product not found"}

@router.get("/get-categories-by-branch")
async def get_categories_by_branch(
    branch: str = None,
    current_user: User = Depends(employee_required_from_session()),  # Allow employees to get category info
    db: AsyncSession = Depends(get_db)
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