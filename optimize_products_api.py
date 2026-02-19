"""
Script to update the view-product endpoint for backend pagination
This optimizes performance for 2500+ products
"""

import os

# Read the current file
with open('src/routers/products.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Old view-product endpoint
old_endpoint = '''@router.get("/view-product")
async def view_products(
    search_string: str = None,
    branches: str = None,
    skip: int = 0,
    limit: int = 40,  # Fetch 40 products for frontend pagination
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    View products with search and branch filtering
    Required by JavaScript frontend
    """
    current_time = time.time()

    # Periodic cache cleanup (only every 60 seconds, not on every request)
    global _last_cleanup_time
    if current_time - _last_cleanup_time > _cache_cleanup_interval:
        keys_to_delete = [
            key for key, value in _products_cache.items()
            if current_time - value['timestamp'] >= _CACHE_TTL
        ]
        for key in keys_to_delete:
            del _products_cache[key]
        _last_cleanup_time = current_time

    # Generate cache key
    cache_key = f"{search_string or ''}:{branches or ''}"

    # Check cache (skip/limit handled by frontend, cache full result)
    if cache_key in _products_cache:
        cached_data = _products_cache[cache_key]
        if current_time - cached_data['timestamp'] < _CACHE_TTL:
            return cached_data['data']

    # Build query with database-level filtering
    statement = select(Product)

    # Apply branch filter at database level
    if branches:
        statement = statement.where(Product.branch == branches)

    # Apply search filter at database level (optimized)
    if search_string:
        # Use exact match for SKU (uses index), LIKE for name/barcode
        statement = statement.where(
            or_(
                Product.sku == search_string,  # Exact match - uses index
                Product.name.like(f"%{search_string}%"),  # Case-sensitive LIKE
                Product.barcode.like(f"%{search_string}%")  # Case-sensitive LIKE
            )
        )

    # Apply pagination at database level
    statement = statement.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(statement)
    products = result.scalars().all()

    # Format response using list comprehension (faster than for loop)
    result_list = [
        {
            "pro_id": str(p.id),
            "pro_name": p.name,
            "pro_price": float(p.unit_price) if p.unit_price else 0.0,
            "pro_cost": float(p.cost_price) if p.cost_price else 0.0,
            "pro_barcode": p.barcode or "",
            "pro_dis": float(p.discount) if p.discount else 0.0,
            "cat_id_fk": p.category or "",
            "limitedquan": p.limited_qty,
            "branch": p.branch or "",
            "brand": p.brand_action or "",
            "pro_image": "",
            "stock": p.stock_level
        }
        for p in products
    ]

    # Cache the result
    _products_cache[cache_key] = {
        'data': result_list,
        'timestamp': current_time
    }

    return result_list'''

# New optimized endpoint with backend pagination
new_endpoint = '''@router.get("/view-product")
async def view_products(
    search_string: str = None,
    branches: str = None,
    page: int = 1,       # Page number for backend pagination
    limit: int = 20,     # Items per page (default 20)
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    View products with search and branch filtering
    Required by JavaScript frontend
    Now uses backend pagination for better performance with large datasets (2500+ products)
    """
    from sqlalchemy import func
    
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

    # Generate cache key (include page and limit)
    cache_key = f"{search_string or ''}:{branches or ''}:{page}:{limit}"

    # Check cache
    if cache_key in _products_cache:
        cached_data = _products_cache[cache_key]
        if current_time - cached_data['timestamp'] < _CACHE_TTL:
            return cached_data['data']

    # Build query with database-level filtering
    statement = select(Product)

    # Apply branch filter at database level (indexed - FAST)
    if branches:
        statement = statement.where(Product.branch == branches)

    # Apply search filter at database level (optimized for remote DB)
    if search_string:
        # Use exact match for SKU/barcode (uses index - VERY FAST)
        # Use prefix match for name (uses index - FAST)
        statement = statement.where(
            or_(
                Product.sku == search_string,           # Exact match
                Product.barcode == search_string,       # Exact match
                Product.name.like(f"{search_string}%")  # Prefix match (not %search%)
            )
        )

    # Apply pagination at database level
    statement = statement.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(statement)
    products = result.scalars().all()

    # Get total count for pagination info
    count_statement = select(func.count(Product.id))
    if branches:
        count_statement = count_statement.where(Product.branch == branches)
    if search_string:
        count_statement = count_statement.where(
            or_(
                Product.sku == search_string,
                Product.barcode == search_string,
                Product.name.like(f"{search_string}%")
            )
        )
    
    total_result = await db.execute(count_statement)
    total = total_result.scalar() or 0

    # Format response using list comprehension
    result_list = [
        {
            "pro_id": str(p.id),
            "pro_name": p.name,
            "pro_price": float(p.unit_price) if p.unit_price else 0.0,
            "pro_cost": float(p.cost_price) if p.cost_price else 0.0,
            "pro_barcode": p.barcode or "",
            "pro_dis": float(p.discount) if p.discount else 0.0,
            "cat_id_fk": p.category or "",
            "limitedquan": p.limited_qty,
            "branch": p.branch or "",
            "brand": p.brand_action or "",
            "pro_image": "",
            "stock": p.stock_level
        }
        for p in products
    ]

    # Prepare response with pagination info
    response_data = {
        'data': result_list,
        'total': total,
        'page': page,
        'limit': limit,
        'total_pages': (total + limit - 1) // limit if limit > 0 else 0
    }

    # Cache the result
    _products_cache[cache_key] = {
        'data': response_data,
        'timestamp': current_time
    }

    return response_data'''

# Replace
if old_endpoint in content:
    content = content.replace(old_endpoint, new_endpoint)
    
    # Write back
    with open('src/routers/products.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("[OK] products.py updated successfully!")
    print("\nChanges:")
    print("  - Added backend pagination (page, limit params)")
    print("  - Changed from LIKE '%search%' to prefix match 'search%'")
    print("  - Added total count for pagination info")
    print("  - Response now includes: data, total, page, limit, total_pages")
    print("\n[WARN] Frontend needs to be updated to use backend pagination!")
else:
    print("[ERROR] Could not find the old endpoint. Manual update required.")
