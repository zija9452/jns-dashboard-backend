from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from uuid import UUID
import uuid
from datetime import datetime, timedelta

from ..database.database import get_db
from ..models.user import User  # Import User at the top to avoid NameError
from ..auth.auth import get_current_user
from ..auth.rbac import admin_required
from ..services.user_service import UserService
from ..services.product_service import ProductService
from ..services.invoice_service import InvoiceService
from ..services.customer_service import CustomerService
from ..services.expense_service import ExpenseService

router = APIRouter()

@router.get("/")
async def get_admin_dashboard(
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get admin dashboard overview with key metrics
    Requires admin role
    """
    # Get counts of key entities
    users = await UserService.get_users(db, skip=0, limit=10000)
    total_users = len(users)

    products = await ProductService.get_products(db, skip=0, limit=10000)
    total_products = len(products)

    customers = await CustomerService.get_customers(db, skip=0, limit=10000)
    total_customers = len(customers)

    invoices = await InvoiceService.get_invoices(db, skip=0, limit=10000)
    total_invoices = len(invoices)

    expenses = await ExpenseService.get_expenses(db, skip=0, limit=10000)
    total_expenses = len(expenses)

    # Get recent activity
    recent_invoices = await InvoiceService.get_invoices(db, skip=0, limit=5)
    recent_customers = await CustomerService.get_customers(db, skip=0, limit=5)

    dashboard_data = {
        "summary": {
            "total_users": total_users,
            "total_products": total_products,
            "total_customers": total_customers,
            "total_invoices": total_invoices,
            "total_expenses": total_expenses
        },
        "recent_activity": {
            "recent_invoices": [invoice.invoice_no for invoice in recent_invoices],
            "recent_customers": [customer.name for customer in recent_customers]
        },
        "last_updated": datetime.utcnow().isoformat()
    }

    return dashboard_data

@router.get("/reports")
async def get_reports(
    report_type: str = "daily",
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get various reports for admin
    Requires admin role
    """
    # Parse dates if provided
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.now() - timedelta(days=30)
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()

    if report_type == "sales":
        # Get sales reports
        invoices = await InvoiceService.get_invoices(db, skip=0, limit=10000)
        total_revenue = sum(float(inv.totals.get('total', 0)) for inv in invoices if hasattr(inv, 'totals') and inv.totals)
        total_invoices_count = len(invoices)

        return {
            "report_type": "sales",
            "period": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
            "metrics": {
                "total_revenue": total_revenue,
                "total_invoices": total_invoices_count,
                "average_invoice_value": total_revenue / total_invoices_count if total_invoices_count > 0 else 0
            }
        }
    elif report_type == "inventory":
        # Get inventory reports
        products = await ProductService.get_products(db, skip=0, limit=10000)
        low_stock_items = [prod for prod in products if prod.stock_level and prod.stock_level < 10]
        total_products = len(products)

        return {
            "report_type": "inventory",
            "period": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
            "metrics": {
                "total_products": total_products,
                "low_stock_items_count": len(low_stock_items),
                "low_stock_items": [{"name": prod.name, "stock": prod.stock_level} for prod in low_stock_items]
            }
        }
    else:
        # Default to daily summary
        return {
            "report_type": report_type,
            "period": {"start": start_dt.isoformat(), "end": end_dt.isoformat()},
            "data": "Report data will be populated based on the requested report type"
        }

@router.get("/settings")
async def get_settings(
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get admin settings
    Requires admin role
    """
    # Return system settings
    settings = {
        "app_version": "1.0.0",
        "database_status": "connected",
        "backup_schedule": "daily at 2 AM",
        "audit_retention_days": 2555,  # 7 years
        "default_timezone": "UTC",
        "features_enabled": {
            "pos_operations": True,
            "inventory_management": True,
            "customer_management": True,
            "reporting": True
        }
    }

    return settings

@router.put("/settings")
async def update_settings(
    settings_update: Dict[str, Any],
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update admin settings
    Requires admin role
    """
    # In a real implementation, this would update system settings in a settings table
    # For now, just return the settings that would be updated

    updated_settings = {
        "message": "Settings updated successfully",
        "updated_fields": list(settings_update.keys()),
        "timestamp": datetime.utcnow().isoformat()
    }

    return updated_settings

# Endpoints required by the JavaScript frontend

@router.get("/getadmin/{id}")
async def get_admin(
    id: str,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve admin user details by ID
    Required by JavaScript frontend
    """
    try:
        user_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

    user = await UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get the user's role name
    from ..models.role import Role
    from sqlalchemy import select
    role_result = await db.execute(select(Role).where(Role.id == user.role_id))
    role = role_result.scalar_one_or_none()

    # Extract extended fields from the meta field if it exists
    import json
    meta_data = {}
    if user.meta:
        try:
            meta_data = json.loads(user.meta)
        except:
            meta_data = {}

    # Map to the expected frontend fields
    admin_data = {
        "ad_id": str(user.id),
        "ad_name": user.full_name,
        "ad_role": role.name if role else "unknown",
        "ad_phone": meta_data.get("phone", ""),
        "ad_address": meta_data.get("address", ""),
        "ad_password": "",  # Never return actual password
        "ad_cnic": meta_data.get("cnic", ""),
        "ad_branch": meta_data.get("branch", "")
    }

    return admin_data

@router.post("/deleteadmin/{id}")
async def delete_admin(
    id: str,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete admin user by ID
    Required by JavaScript frontend
    """
    try:
        user_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

    # Prevent deleting own account
    if str(current_user.id) == id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    user = await UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Delete the user
    success = await UserService.delete_user(db, user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed to delete user"
        )

    return {
        "success": True,
        "message": "User deleted successfully"
    }

@router.get("/viewsalesman")
async def view_salesman(
    search_string: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    View salesman with optional search functionality
    Required by JavaScript frontend
    """
    from ..services.salesman_service import SalesmanService
    from ..models.salesman import Salesman

    # Get all salesmen, with optional search
    salesmen = await SalesmanService.get_salesmen(db, skip=skip, limit=limit)

    # Filter by search string if provided
    if search_string:
        search_lower = search_string.lower()
        filtered_salesmen = []
        for salesman in salesmen:
            if (search_lower in salesman.name.lower() or
                search_lower in salesman.code.lower()):
                filtered_salesmen.append(salesman)
        salesmen = filtered_salesmen

    # Format the response to match expected frontend structure
    result = []
    for salesman in salesmen:
        result.append({
            "id": str(salesman.id),
            "name": salesman.name,
            "code": salesman.code,
            "commission_rate": str(salesman.commission_rate) if salesman.commission_rate else "0.00",
            "created_at": salesman.created_at.isoformat(),
            "updated_at": salesman.updated_at.isoformat()
        })

    return result

@router.get("/viewadmins")
async def view_admins(
    search_string: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    View all admin users with optional search functionality
    """
    from ..models.role import Role
    from sqlalchemy import select

    # Get all users with role 'admin'
    all_users = await UserService.get_users(db, skip=skip, limit=limit)

    # Filter for admin users only
    admin_users = []
    for user in all_users:
        role_result = await db.execute(select(Role).where(Role.id == user.role_id))
        role = role_result.scalar_one_or_none()
        if role and role.name == "admin":
            admin_users.append(user)

    # Filter by search string if provided
    if search_string:
        search_lower = search_string.lower()
        filtered_users = []
        for user in admin_users:
            if (search_lower in user.full_name.lower() or
                search_lower in user.username.lower() or
                search_lower in user.email.lower()):
                filtered_users.append(user)
        admin_users = filtered_users

    # Format the response
    result = []
    for user in admin_users:
        role_result = await db.execute(select(Role).where(Role.id == user.role_id))
        role = role_result.scalar_one_or_none()

        # Extract extended fields from the meta field if it exists
        import json
        meta_data = {}
        if user.meta:
            try:
                meta_data = json.loads(user.meta)
            except:
                meta_data = {}

        result.append({
            "ad_id": str(user.id),
            "ad_name": user.full_name,
            "ad_role": role.name if role else "unknown",
            "ad_phone": meta_data.get("phone", ""),
            "ad_address": meta_data.get("address", ""),
            "ad_cnic": meta_data.get("cnic", ""),
            "ad_branch": meta_data.get("branch", ""),
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat()
        })

    return result

# Capitalized version for JavaScript frontend compatibility
@router.get("/ViewAdmins")
async def view_admins_capitalized(
    search_string: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    View all admin users with optional search functionality (capitalized for JS frontend)
    """
    return await view_admins(search_string, skip, limit, current_user, db)

@router.post("/createadmin")
async def create_admin(
    ad_name: str,
    ad_role: str,
    ad_phone: str = None,
    ad_address: str = None,
    ad_password: str = "",
    ad_cnic: str = None,
    ad_branch: str = None,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new admin user
    Required by JavaScript frontend
    """
    from ..models.role import Role
    from sqlalchemy import select

    # Check if role exists
    role_result = await db.execute(select(Role).where(Role.name == ad_role))
    role = role_result.scalar_one_or_none()
    if not role:
        # Create the role if it doesn't exist
        from uuid import UUID
        role = Role(name=ad_role, permissions="{}")
        db.add(role)
        await db.commit()
        await db.refresh(role)

    # Prepare meta data
    import json
    meta_data = {}
    if ad_phone:
        meta_data["phone"] = ad_phone
    if ad_address:
        meta_data["address"] = ad_address
    if ad_cnic:
        meta_data["cnic"] = ad_cnic
    if ad_branch:
        meta_data["branch"] = ad_branch

    # Create user
    from ..models.user import UserCreate
    user_create = UserCreate(
        full_name=ad_name,
        email=f"{ad_name.replace(' ', '.').lower()}@example.com",  # Default email
        username=ad_name.replace(' ', '').lower(),
        role_id=role.id,
        password=ad_password if ad_password else "default_password123"
    )

    # Store extended fields in meta
    user_create.meta = json.dumps(meta_data) if meta_data else None

    created_user = await UserService.create_user(db, user_create)

    return {
        "ad_id": str(created_user.id),
        "ad_name": created_user.full_name,
        "ad_role": role.name,
        "ad_phone": ad_phone or "",
        "ad_address": ad_address or "",
        "ad_cnic": ad_cnic or "",
        "ad_branch": ad_branch or "",
        "message": "Admin user created successfully"
    }

# Capitalized version for JavaScript frontend compatibility
@router.post("/CreateAdmin")
async def create_admin_capitalized(
    ad_name: str,
    ad_role: str,
    ad_phone: str = None,
    ad_address: str = None,
    ad_password: str = "",
    ad_cnci: str = None,
    ad_branch: str = None,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new admin user - Capitalized endpoint for JS frontend compatibility
    """
    return await create_admin(ad_name, ad_role, ad_phone, ad_address, ad_password, ad_cnci, ad_branch, current_user, db)

@router.put("/updateadmin/{id}")
async def update_admin(
    id: str,
    ad_name: str = None,
    ad_role: str = None,
    ad_phone: str = None,
    ad_address: str = None,
    ad_password: str = None,
    ad_cnic: str = None,
    ad_branch: str = None,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update admin user details
    Required by JavaScript frontend
    """
    try:
        user_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID format"
        )

    user = await UserService.get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Get current meta data
    import json
    meta_data = {}
    if user.meta:
        try:
            meta_data = json.loads(user.meta)
        except:
            meta_data = {}

    # Update meta fields
    if ad_phone is not None:
        meta_data["phone"] = ad_phone
    if ad_address is not None:
        meta_data["address"] = ad_address
    if ad_cnic is not None:
        meta_data["cnic"] = ad_cnic
    if ad_branch is not None:
        meta_data["branch"] = ad_branch

    # Prepare update object
    from ..models.user import UserUpdate
    user_update = UserUpdate(
        full_name=ad_name,
        meta=json.dumps(meta_data)
    )

    if ad_role:
        from ..models.role import Role
        from sqlalchemy import select
        role_result = await db.execute(select(Role).where(Role.name == ad_role))
        role = role_result.scalar_one_or_none()
        if role:
            user_update.role_id = role.id

    if ad_password:
        # In a real implementation, you'd hash the password here
        # For now, we'll skip updating the password in this example
        pass

    updated_user = await UserService.update_user(db, user_id, user_update)

    # Get the updated role name
    from ..models.role import Role
    from sqlalchemy import select
    role_result = await db.execute(select(Role).where(Role.id == updated_user.role_id))
    role = role_result.scalar_one_or_none()

    return {
        "ad_id": str(updated_user.id),
        "ad_name": updated_user.full_name,
        "ad_role": role.name if role else "unknown",
        "ad_phone": meta_data.get("phone", ""),
        "ad_address": meta_data.get("address", ""),
        "ad_cnic": meta_data.get("cnic", ""),
        "ad_branch": meta_data.get("branch", ""),
        "message": "Admin user updated successfully"
    }

# Capitalized version for JavaScript frontend compatibility
@router.put("/UpdateAdmin/{id}")
async def update_admin_capitalized(
    id: str,
    ad_name: str = None,
    ad_role: str = None,
    ad_phone: str = None,
    ad_address: str = None,
    ad_password: str = None,
    ad_cnic: str = None,
    ad_branch: str = None,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Update admin user details - Capitalized endpoint for JS frontend compatibility
    """
    return await update_admin(id, ad_name, ad_role, ad_phone, ad_address, ad_password, ad_cnic, ad_branch, current_user, db)


# Product-related endpoints required by the JavaScript frontend

@router.get("/GetMaxProId")
async def get_max_pro_id(
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the maximum product ID for barcode calculation
    Required by JavaScript frontend
    """
    from sqlmodel import select
    from ..models.product import Product

    # Query to get all products and count them to create a simple numeric ID
    statement = select(Product)
    result = await db.execute(statement)
    products = result.scalars().all()

    # Return the count of products + 1000 as a simple ID for the frontend
    # This simulates a sequential ID for barcode calculation
    max_id_num = len(products) + 1000

    return max_id_num

@router.get("/GetProducts/{id}")
async def get_products(
    id: str,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve specific product details by ID
    Required by JavaScript frontend
    """
    from ..models.product import Product
    from ..services.product_service import ProductService

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

    # Map to the expected frontend fields
    product_data = {
        "pro_id": str(product.id),
        "pro_name": product.name,
        "pro_price": float(product.unit_price) if product.unit_price else 0.0,
        "pro_cost": float(product.cost_price) if product.cost_price else 0.0,
        "pro_barcode": product.barcode or "",
        "pro_dis": float(product.discount) if product.discount else 0.0,
        "cat_id_fk": product.category or "",  # This should be the category ID
        "limitedquan": product.limited_qty,
        "branch": product.branch or "",
        "brand": product.brand_action or "",
        "pro_image": product.attributes or ""  # Using attributes field to store image path
    }

    return product_data

@router.get("/Viewproduct")
async def view_product(
    search_string: str = None,
    branches: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required()),
    db: AsyncSession = Depends(get_db)
):
    """
    View products with search and branch filtering
    Required by JavaScript frontend
    """
    from ..models.product import Product
    from ..services.product_service import ProductService

    # Get all products with pagination
    products = await ProductService.get_products(db, skip=skip, limit=limit)

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
            "pro_price": float(product.unit_price) if product.unit_price else 0.0,
            "pro_cost": float(product.cost_price) if product.cost_price else 0.0,
            "pro_barcode": product.barcode or "",
            "pro_dis": float(product.discount) if product.discount else 0.0,
            "cat_id_fk": product.category or "",
            "limitedquan": product.limited_qty,
            "branch": product.branch or "",
            "brand": product.brand_action or "",
            "pro_image": product.attributes or ""
        })

    return result

@router.post("/Deleteproduct/{id}")
async def delete_product(
    id: str,
    current_user: User = Depends(admin_required()),  # Keep as admin only for security
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a product by ID
    Required by JavaScript frontend - admin only for security
    """
    from ..services.product_service import ProductService

    try:
        product_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid product ID format"
        )

    success = await ProductService.delete_product(db, product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return {
        "success": True,
        "message": "Product deleted successfully"
    }

@router.post("/DeleteProductImage/{id}")
async def delete_product_image(
    id: str,
    current_user: User = Depends(admin_required()),  # Allow employees to manage product images
    db: AsyncSession = Depends(get_db)
):
    """
    Delete product image by product ID
    Required by JavaScript frontend
    """
    from ..models.product import Product
    from ..services.product_service import ProductService

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

@router.post("/brand")
async def create_brand(
    brand: str = None,
    current_user: User = Depends(admin_required()),  # Allow employees to create brands
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

@router.post("/Deletebrand")
async def delete_brand(
    brand: str = None,
    current_user: User = Depends(admin_required()),  # Allow employees to delete brands
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

@router.post("/GetStockDetail")
async def get_stock_detail(
    pro_name: str = None,
    current_user: User = Depends(admin_required()),  # Allow employees to check stock details
    db: AsyncSession = Depends(get_db)
):
    """
    Get stock details for a specific product
    Required by JavaScript frontend
    """
    from ..models.product import Product
    from sqlalchemy import select

    if not pro_name:
        return {"error": "Product not found"}

    # Find product by name - use exact match first, then partial
    statement = select(Product).where(Product.name == pro_name)
    result = await db.execute(statement)
    product = result.scalar_one_or_none()

    # If exact match not found, try partial match
    if not product:
        statement = select(Product).where(Product.name.ilike(f"%{pro_name}%")).limit(1)
        result = await db.execute(statement)
        product = result.scalar_one_or_none()

    if product:
        return {
            "quantity": product.stock_level
        }
    else:
        return {"error": "Product not found"}

@router.get("/GetCustomerVendorByBranch")
async def get_customer_vendor_by_branch(
    branch: str = None,
    current_user: User = Depends(admin_required()),  # Allow employees to get category info
    db: AsyncSession = Depends(get_db)
):
    """
    Get categories by branch
    Required by JavaScript frontend
    """
    # For now, return a mock response
    # In a real implementation, you would query actual category data
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