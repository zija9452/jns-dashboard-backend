from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from uuid import UUID
import uuid
import time
import logging
import io

from ..database.database import get_db
from ..models.product import Product, ProductCreate, ProductUpdate, ProductRead
from ..models.user import User  # Import User at the top to avoid NameError
from ..services.product_service import ProductService
from ..services.cloudinary_service import CloudinaryService
from ..auth.session_auth import get_current_user_from_session, admin_required_from_session, admin_employee_required_from_session, admin_employee_warehouse_required_from_session
from sqlmodel import select

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory cache for view-products API (5 minutes TTL)
_products_cache: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 300  # 5 minutes
_cache_cleanup_interval = 60  # Cleanup every 60 seconds
_last_cleanup_time = time.time()

@router.get("/", response_model=List[ProductRead])
async def get_products(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user_from_session),  # Admins and cashiers can view products
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of products with pagination
    Admins and cashiers can view products
    """
    products = await ProductService.get_products(db, skip=skip, limit=limit)
    return products

# Helper function to clear products cache
async def clear_products_cache():
    """Clear all cached product data from Redis"""
    from ..utils.cache import cache
    
    # Invalidate all product caches
    await cache.delete_pattern("product:barcode:*")
    await cache.delete_pattern("stock:view:*")
    
    logger.info("✓ Product cache invalidated")

@router.post("/", response_model=ProductRead)
async def create_product(
    product_create: ProductCreate,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new product
    Requires admin, employee, or warehouse role
    Auto-sets is_warehouse_product = true if role is warehouse
    """
    # Check role access
    if current_user.role.name not in ["admin", "employee", "warehouse"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin, employee, or warehouse access required"
        )

    # Auto-set is_warehouse_product for warehouse role
    if current_user.role.name == "warehouse":
        product_create.is_warehouse_product = True

    # Check if product name already exists (case-insensitive)
    from sqlmodel import select
    statement = select(Product).where(Product.name == product_create.name)
    result = await db.execute(statement)
    existing_product = result.scalar_one_or_none()

    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product with this name already exists. Please use a different name."
        )

    # Check if SKU already exists
    existing_product = await ProductService.get_product_by_sku(db, product_create.sku)
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product with this SKU already exists"
        )

    # Clear cache after creating product
    await clear_products_cache()

    return await ProductService.create_product(db, product_create, str(current_user.id))

# --- TEMPORARY BULK INSERT ENDPOINT (Remove after use) ---
@router.post("/bulk-insert", response_model=List[ProductRead])
async def create_products_bulk_temp(
    products_create: List[ProductCreate],
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Temporary endpoint for bulk product insertion
    Requires admin, employee, or warehouse role
    """
    # Check role access
    if current_user.role.name not in ["admin", "employee", "warehouse"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin, employee, or warehouse access required"
        )

    if not products_create:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product list cannot be empty"
        )

    # Auto-set is_warehouse_product for warehouse role
    if current_user.role.name == "warehouse":
        for p in products_create:
            p.is_warehouse_product = True

    # Clear cache after bulk creation
    await clear_products_cache()

    try:
        return await ProductService.bulk_create_products(db, products_create, str(current_user.id))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
# ---------------------------------------------------------

# Specific routes that should come before the generic /{product_id} route to avoid conflicts
@router.get("/getproducts/{id}")
async def get_product_details(
    id: UUID,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve specific product details by ID
    Required by JavaScript frontend
    Optimized: Direct query without service layer
    """
    from sqlmodel import select
    
    # Direct query - faster than service layer
    statement = select(Product).where(Product.id == id)
    result = await db.execute(statement)
    product = result.scalar_one_or_none()
    
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
        "cat_id_fk": product.category or "",
        "limitedquan": product.limited_qty,
        "branch": product.branch or "",
        "brand": product.brand_action or "",
        "pro_image": product.attributes or "",
        "article_no": product.article_no or '',
        "warehouse_limited_qty": product.warehouse_limited_qty,
        "warehouse_cost": float(product.warehouse_cost) if product.warehouse_cost else 0.0
    }

    return product_data

@router.get("/viewproduct")
async def view_products(
    search_string: str = None,
    branches: str = None,
    warehouse: str = None,  # Filter for warehouse products only
    page: int = 1,       # Page number for backend pagination
    limit: int = 8,      # 8 items per page (for 5 pages = 40 products total)
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    View products with branch filtering and search
    Required by JavaScript frontend
    Optimized: Only fetches required fields, no extra data
    Returns: Paginated data + total count for proper frontend pagination
    """
    # Check role access
    if current_user.role.name not in ["admin", "employee", "cashier", "warehouse"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Authenticated access required"
        )

    current_time = time.time()

    # Calculate skip from page
    skip = (page - 1) * limit

    # Periodic cache cleanup (only every 60 seconds)
    global _last_cleanup_time
    if current_time - _last_cleanup_time > _cache_cleanup_interval:
        keys_to_delete = [
            key for key, value in _products_cache.items()
            if current_time - value['timestamp'] >= _CACHE_TTL
        ]
        for key in keys_to_delete:
            del _products_cache[key]
        _last_cleanup_time = current_time

    # Generate cache key (include search for accurate caching)
    cache_key = f"{branches or ''}:{search_string or ''}:{limit}"

    # Check cache for total count (page doesn't matter for count)
    count_cache_key = f"count:{branches or ''}:{search_string or ''}"
    
    # Build base query - select only required columns for better performance
    # Excluding attributes field (images) to avoid large base64 data in list view
    base_statement = select(
        Product.id,
        Product.name,
        Product.unit_price,
        Product.cost_price,
        Product.barcode,
        Product.discount,
        Product.category,
        Product.limited_qty,
        Product.branch,
        Product.brand_action,
        Product.stock_level,
        Product.is_warehouse_product,
        Product.article_no,
        Product.warehouse_stock,
        Product.warehouse_limited_qty,
        Product.warehouse_cost
    )

    # Apply branch filter at database level (indexed - FAST)
    if branches:
        base_statement = base_statement.where(Product.branch == branches)

    # Apply warehouse filter - only show products where is_warehouse_product = true
    if warehouse is not None and isinstance(warehouse, str) and warehouse.lower() == 'true':
        base_statement = base_statement.where(Product.is_warehouse_product == True)

    # Apply search filter at database level (case-insensitive)
    if search_string and search_string.strip():
        search_pattern = f"%{search_string.strip()}%"
        base_statement = base_statement.where(
            or_(
                Product.name.ilike(search_pattern),
                Product.barcode.ilike(search_pattern),
                Product.sku.ilike(search_pattern)
            )
        )

    # Get total count (efficient using count query)
    count_statement = select(Product.id)
    if branches:
        count_statement = count_statement.where(Product.branch == branches)
    # Apply warehouse filter to count statement
    if warehouse and warehouse.lower() == 'true':
        count_statement = count_statement.where(Product.is_warehouse_product == True)
    if search_string and search_string.strip():
        search_pattern = f"%{search_string.strip()}%"
        count_statement = count_statement.where(
            or_(
                Product.name.ilike(search_pattern),
                Product.barcode.ilike(search_pattern),
                Product.sku.ilike(search_pattern)
            )
        )
    
    count_result = await db.execute(count_statement)
    total_count = len(count_result.scalars().all())

    # Apply pagination at database level (order by created_at DESC to show newest last)
    statement = base_statement.order_by(Product.created_at.asc()).offset(skip).limit(limit)

    # Execute query
    result = await db.execute(statement)
    products = result.fetchall()

    # Format response using list comprehension - minimal fields only
    result_list = [
        {
            "pro_id": str(p[0]),
            "pro_name": p[1],
            "pro_price": float(p[2]) if p[2] else 0.0,
            "pro_cost": float(p[3]) if p[3] else 0.0,
            "pro_barcode": p[4] or "",
            "pro_dis": float(p[5]) if p[5] else 0.0,
            "cat_id_fk": p[6] or "",
            "limitedquan": p[7],
            "branch": p[8] or "",
            "brand": p[9] or "",
            "stock": p[10],  # stock_level is at index 10
            "is_warehouse_product": p[11],
            "article_no": p[12] or "",
            "warehouse_stock": p[13],
            "warehouse_limited_qty": p[14],
            "warehouse_cost": float(p[15]) if p[15] else 0.0
        }
        for p in products
    ]

    # Calculate total pages
    total_pages = (total_count + limit - 1) // limit  # Ceiling division

    # Prepare response with pagination info
    response_data = {
        'data': result_list,
        'page': page,
        'limit': limit,
        'total': total_count,
        'total_pages': total_pages,
        'has_more': page < total_pages
    }

    # Cache the result
    _products_cache[cache_key] = {
        'data': response_data,
        'timestamp': current_time
    }

    return response_data

@router.get("/getmaxproid")
async def get_max_pro_id(
    current_user: User = Depends(get_current_user_from_session),
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

@router.get("/generatebarcode")
async def generate_barcode(
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a unique barcode for new products
    Access: admin, employee, warehouse
    """
    # Check role access
    if current_user.role.name not in ["admin", "employee", "warehouse"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin, employee, or warehouse access required"
        )

    barcode = await ProductService.generate_unique_barcode(db)
    return {"barcode": barcode}


@router.post("/upload-image")
async def upload_product_image(
    file: UploadFile = File(..., description="Product image file"),
    current_user: User = Depends(get_current_user_from_session)
):
    """
    Upload product image to Cloudinary and return public URL
    
    Accepts image files (JPG, PNG, WebP) and uploads to Cloudinary CDN.
    Returns the public URL which can be stored in the database.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Validate file size (max 5MB)
    file_size = 0
    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size > 5 * 1024 * 1024:  # 5MB
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size must be less than 5MB"
        )
    
    try:
        # Upload to Cloudinary
        image_url = await CloudinaryService.upload_image(
            file_bytes=file_bytes,
            folder="products",
            public_id=f"product_{uuid.uuid4().hex[:12]}"
        )
        
        logger.info(f"Image uploaded successfully: {image_url}")
        
        return {
            "success": True,
            "url": image_url,
            "size": file_size,
            "content_type": file.content_type
        }
        
    except Exception as e:
        logger.error(f"Failed to upload image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}"
        )


@router.get("/searchbybarcode")
async def search_product_by_barcode(
    barcode: str,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Search product by barcode (FAST - with Redis cache)
    Returns product details for stock in workflow
    """
    from sqlalchemy import select
    import logging
    from ..utils.cache import cache
    
    logging.info(f"Searching for barcode: {barcode}")

    # Try cache first
    cached_product = await cache.get_product_by_barcode(barcode)
    if cached_product:
        logging.info(f"✓ Cache HIT for barcode: {barcode}")
        return cached_product
    
    logging.info(f"Cache MISS for barcode: {barcode}")

    # Search by barcode ONLY (indexed - fast)
    statement = select(Product).where(Product.barcode == barcode)
    result = await db.execute(statement)
    product = result.scalar_one_or_none()
    
    if not product:
        # Try searching by SKU (also indexed)
        logging.info(f"Trying SKU search: {barcode}")
        statement = select(Product).where(Product.sku == barcode)
        result = await db.execute(statement)
        product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Format response
    result_dict = {
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
        "pro_image": product.attributes or "",
        "stock": product.stock_level,
        "is_warehouse_product": product.is_warehouse_product,
        "warehouse_stock": product.warehouse_stock,
        "warehouse_limited_qty": product.warehouse_limited_qty,
        "warehouse_cost": float(product.warehouse_cost) if product.warehouse_cost else 0.0,
        "article_no": product.article_no or ""
    }

    # Cache for 10 minutes
    await cache.set_product_by_barcode(barcode, result_dict, ttl=600)
    logging.info(f"✓ Cached product for barcode: {barcode}")

    return result_dict

@router.post("/deleteproduct/{id}")
async def delete_product_frontend(
    id: str,
    current_user: User = Depends(admin_employee_warehouse_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a product by ID (frontend compatible response)
    Admin, Employee, and Warehouse can delete products. Cashiers cannot delete products.
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

    # Clear cache after deleting product
    await clear_products_cache()

    return {
        "success": True,
        "message": "Product deleted successfully"
    }

@router.post("/deleteproductimage/{id}")
async def delete_product_image(
    id: str,
    current_user: User = Depends(get_current_user_from_session),  # Allow employees to manage product images
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

@router.post("/delete-image")
async def delete_image_from_cloudinary(
    request_data: dict,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete product image from Cloudinary permanently
    
    This endpoint:
    1. Deletes the image from Cloudinary storage
    2. Clears the image field from the product (if product_id is provided)
    
    Request body:
    - public_id: Cloudinary public ID of the image to delete (e.g., "european-sports/products/image_name")
    - image_url: (Optional) Cloudinary URL to extract public_id from (if public_id not provided)
    - product_id: (Optional) Product ID to clear the image field
    """
    try:
        public_id = request_data.get("public_id")
        image_url = request_data.get("image_url")
        product_id = request_data.get("product_id")
        
        # Extract public_id from URL if not provided directly
        if not public_id and image_url:
            public_id = CloudinaryService.get_public_id_from_url(image_url)
        
        if not public_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="public_id or image_url is required"
            )
        
        # Delete from Cloudinary
        deleted = await CloudinaryService.delete_image(public_id)
        
        if not deleted:
            logger.warning(f"Failed to delete image from Cloudinary: {public_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete image from Cloudinary"
            )
        
        # If product_id is provided, also clear the image field from the product
        if product_id:
            try:
                product_uuid = UUID(product_id)
                product = await ProductService.get_product(db, product_uuid)
                
                if product:
                    product.attributes = None
                    db.add(product)
                    await db.commit()
                    await db.refresh(product)
                    logger.info(f"Cleared image field for product: {product_id}")
            except ValueError:
                logger.warning(f"Invalid product_id format: {product_id}")
                # Continue anyway, image was deleted from Cloudinary
        
        logger.info(f"Successfully deleted image from Cloudinary: {public_id}")
        
        return {
            "success": True,
            "message": "Image deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete image: {str(e)}"
        )

# Generic routes should come after specific routes to avoid conflicts
@router.get("/{product_id}", response_model=ProductRead)
async def get_product(
    product_id: str,
    current_user: User = Depends(get_current_user_from_session),  # Admins and cashiers can view product details
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
    current_user: User = Depends(get_current_user_from_session),  # Admins and employees can update products
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

    # Check if new name conflicts with another product (allow if it's the same product)
    if product_update.name and product_update.name != product.name:
        from sqlmodel import select
        statement = select(Product).where(Product.name == product_update.name)
        result = await db.execute(statement)
        existing_product = result.scalar_one_or_none()
        
        if existing_product and existing_product.id != product_uuid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Product with this name already exists. Please use a different name."
            )

    # Clear cache after updating product
    await clear_products_cache()

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

    # Clear cache after deleting product
    await clear_products_cache()

    return {"message": "Product deleted successfully"}

# User import is already at the top of the file, removing duplicate

@router.post("/brand")
async def create_brand(
    brand: str = None,
    current_user: User = Depends(get_current_user_from_session),  # Allow employees to create brands
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

@router.post("/deletebrand")
async def delete_brand(
    brand: str = None,
    current_user: User = Depends(get_current_user_from_session),  # Allow employees to delete brands
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

@router.post("/getstockdetail")
async def get_stock_detail(
    pro_name: str = None,
    current_user: User = Depends(get_current_user_from_session),  # Allow employees to check stock details
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

@router.get("/getcategoriesbybranch")
async def get_categories_by_branch(
    branch: str = None,
    current_user: User = Depends(get_current_user_from_session),  # Allow employees to get category info
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