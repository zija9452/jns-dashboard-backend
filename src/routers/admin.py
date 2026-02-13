from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any
from uuid import UUID
import uuid
from datetime import datetime, timedelta
from pydantic import BaseModel

from ..database.database import get_db
from ..models.user import User  # Import User at the top to avoid NameError
from ..models.salesman import Salesman, SalesmanCreate, SalesmanUpdate
from ..models.stock_entry import StockEntry, StockEntryType
from ..models.product import Product
from ..models.vendor import Vendor
from ..auth.session_auth import get_current_user_from_session, admin_required_from_session, employee_required_from_session, admin_cashier_employee_required_from_session
from ..services.user_service import UserService
from ..services.product_service import ProductService
from ..services.invoice_service import InvoiceService
from ..services.customer_service import CustomerService
from ..services.expense_service import ExpenseService
from ..services.stock_service import StockService

# Pydantic models for request bodies
class CreateAdminRequest(BaseModel):
    ad_name: str
    ad_role: str
    ad_phone: str = None
    ad_address: str = None
    ad_password: str = ""
    ad_cnic: str = None
    ad_branch: str = None

class UpdateAdminRequest(BaseModel):
    ad_name: str = None
    ad_role: str = None
    ad_phone: str = None
    ad_address: str = None
    ad_password: str = None
    ad_cnic: str = None
    ad_branch: str = None

router = APIRouter()

@router.get("/")
async def get_admin_dashboard(
    current_user: User = Depends(admin_required_from_session()),
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
    current_user: User = Depends(admin_required_from_session()),
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
    current_user: User = Depends(admin_required_from_session()),
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
    current_user: User = Depends(admin_required_from_session()),
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
    current_user: User = Depends(admin_required_from_session()),
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
        "ad_phone": user.phone or "",
        "ad_address": user.address or "",
        "ad_password": "",  # Never return actual password
        "ad_cnic": user.cnic or "",
        "ad_branch": user.branch or ""
    }

    return admin_data

@router.post("/deleteadmin/{id}")
async def delete_admin(
    id: str,
    current_user: User = Depends(admin_required_from_session()),
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

@router.get("/getsalesman/{id}")
async def get_salesman(
    id: str,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve specific salesman details by ID
    Required by JavaScript frontend
    """
    from ..services.salesman_service import SalesmanService
    from ..models.salesman import Salesman

    try:
        salesman_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid salesman ID format"
        )

    salesman = await SalesmanService.get_salesman(db, salesman_id)
    if not salesman:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesman not found"
        )

    # Map to the expected frontend fields based on the JavaScript code
    salesman_data = {
        "sal_id": str(salesman.id),
        "sal_name": salesman.name,
        "sal_phone": salesman.phone or "",  # Using actual phone field from model
        "sal_address": salesman.address or "",  # Using actual address field from model
        "branch": salesman.branch or ""  # Using actual branch field from model
    }

    return salesman_data

@router.get("/viewsalesman")
async def view_salesman(
    search_string: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required_from_session()),
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
            "sal_id": str(salesman.id),
            "sal_name": salesman.name,
            "sal_phone": salesman.phone or "",  # Using actual phone field from model
            "sal_address": salesman.address or "",  # Using actual address field from model
            "branch": salesman.branch or ""  # Using actual branch field from model
        })

    return result

# JavaScript frontend seems to call this endpoint for admin search (likely copy-paste error)
# So we'll also provide admin user search under the same endpoint name
@router.get("/viewadmin")
async def view_admin(
    search_string: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    View admin users with optional search functionality
    Required by JavaScript frontend - alternative to viewsalesman for admin users
    """
    from ..models.role import Role
    from sqlalchemy import select

    # Get all users, with optional search
    all_users = await UserService.get_users(db, skip=skip, limit=limit)

    # Filter for admin users only
    admin_users = []
    for user in all_users:
        role_result = await db.execute(select(Role).where(Role.id == user.role_id))
        role = role_result.scalar_one_or_none()
        if role and (role.name == "admin" or role.name == "employee" or role.name == "cashier"):  # Include all staff roles
            admin_users.append(user)

    # Filter by search string if provided
    if search_string:
        search_lower = search_string.lower()
        filtered_users = []
        for user in admin_users:
            if (search_lower in user.full_name.lower() or
                search_lower in user.username.lower() or
                search_lower in user.email.lower() or
                search_lower in (user.phone or "").lower() or
                search_lower in (user.address or "").lower() or
                search_lower in (user.cnic or "").lower()):
                filtered_users.append(user)
        admin_users = filtered_users

    # Format the response to match expected frontend structure
    result = []
    for user in admin_users:
        role_result = await db.execute(select(Role).where(Role.id == user.role_id))
        role = role_result.scalar_one_or_none()

        result.append({
            "ad_id": str(user.id),
            "ad_name": user.full_name,
            "ad_role": role.name if role else "unknown",
            "ad_phone": user.phone or "",
            "ad_address": user.address or "",
            "ad_cnic": user.cnic or "",
            "ad_branch": user.branch or ""
        })

    return result

# Admin-specific salesman CRUD endpoints

@router.post("/salesman")
async def create_salesman_admin(
    salesman_create: SalesmanCreate,
    current_user: User = Depends(admin_required_from_session()),  # Only admins can create salesmen
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new salesman via admin endpoint
    Required by JavaScript frontend
    """
    from ..services.salesman_service import SalesmanService
    from ..models.salesman import Salesman

    # Check if code already exists
    existing_salesman = await SalesmanService.get_salesman_by_code(db, salesman_create.code)
    if existing_salesman:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Salesman with this code already exists"
        )

    created_salesman = await SalesmanService.create_salesman(db, salesman_create, str(current_user.id))

    # Format response to match expected frontend structure
    return {
        "sal_id": str(created_salesman.id),
        "sal_name": created_salesman.name,
        "sal_phone": created_salesman.phone or "",
        "sal_address": created_salesman.address or "",
        "branch": created_salesman.branch or "",
        "code": created_salesman.code,
        "commission_rate": str(created_salesman.commission_rate)
    }

@router.put("/salesman/{id}")
async def update_salesman_admin(
    id: str,
    salesman_update: SalesmanUpdate,
    current_user: User = Depends(admin_required_from_session()),  # Only admins can update salesmen
    db: AsyncSession = Depends(get_db)
):
    """
    Update a specific salesman by ID via admin endpoint
    Required by JavaScript frontend
    """
    from ..services.salesman_service import SalesmanService
    from ..models.salesman import Salesman

    try:
        salesman_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid salesman ID format"
        )

    # Check if updating code and if new code already exists
    if salesman_update.code:
        existing_salesman = await SalesmanService.get_salesman_by_code(db, salesman_update.code)
        if existing_salesman and str(existing_salesman.id) != id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Salesman with this code already exists"
            )

    updated_salesman = await SalesmanService.update_salesman(db, salesman_id, salesman_update, str(current_user.id))

    if not updated_salesman:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesman not found"
        )

    # Format response to match expected frontend structure
    return {
        "sal_id": str(updated_salesman.id),
        "sal_name": updated_salesman.name,
        "sal_phone": updated_salesman.phone or "",
        "sal_address": updated_salesman.address or "",
        "branch": updated_salesman.branch or "",
        "code": updated_salesman.code,
        "commission_rate": str(updated_salesman.commission_rate)
    }

@router.delete("/salesman/{id}")
async def delete_salesman_admin(
    id: str,
    current_user: User = Depends(admin_required_from_session()),  # Only admins can delete salesmen
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific salesman by ID via admin endpoint
    Required by JavaScript frontend
    """
    from ..services.salesman_service import SalesmanService

    try:
        salesman_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid salesman ID format"
        )

    success = await SalesmanService.delete_salesman(db, salesman_id, str(current_user.id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salesman not found"
        )

    return {
        "success": True,
        "message": "Salesman deleted successfully"
    }





@router.get("/customerorderreport")
async def customer_order_report(
    orderid: str = None,
    timezone: str = None,
    printoption: str = None,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate customer order report in PDF format
    Required by JavaScript frontend
    """
    from ..models.customer_invoice import CustomerInvoice
    from sqlalchemy import select
    import base64

    # If order ID is provided, get specific order details
    order_details = None
    if orderid:
        try:
            from uuid import UUID
            order_uuid = UUID(orderid)

            statement = select(CustomerInvoice).where(CustomerInvoice == order_uuid)
            result = await db.execute(statement)
            order = result.scalar_one_or_none()

            if order:
                import json
                fields_data = {}
                try:
                    fields_data = json.loads(order.fields)
                except:
                    fields_data = {}

                order_details = {
                    "orderid": str(order.id),
                    "status": order.status.value if hasattr(order.status, 'value') else order.status,
                    "fields": fields_data,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                    "updated_at": order.updated_at.isoformat() if order.updated_at else None
                }
        except:
            pass  # If order ID is invalid, continue with general report

    # Generate a simple PDF report (base64 encoded)
    pdf_content = "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    pdf_content += "2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    pdf_content += "3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
    pdf_content += "4 0 obj\n<<\n/Length 60\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Customer Order Report) Tj\nET\nendstream\nendobj\n"
    pdf_content += "xref\n0 5\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n%%EOF"

    # Encode to base64
    encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

    return encoded_pdf




@router.get("/viewadmins")
async def view_admins(
    search_string: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required_from_session()),
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

        result.append({
            "ad_id": str(user.id),
            "ad_name": user.full_name,
            "ad_role": role.name if role else "unknown",
            "ad_phone": user.phone or "",
            "ad_address": user.address or "",
            "ad_cnic": user.cnic or "",
            "ad_branch": user.branch or "",
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat()
        })

    return result


@router.post("/createadmin")
async def create_admin(
    request: CreateAdminRequest,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new admin user
    Required by JavaScript frontend
    """
    from ..models.role import Role
    from sqlalchemy import select

    # Check if role exists
    role_result = await db.execute(select(Role).where(Role.name == request.ad_role))
    role = role_result.scalar_one_or_none()
    if not role:
        # Create the role if it doesn't exist
        from uuid import UUID
        role = Role(name=request.ad_role, permissions="{}")
        db.add(role)
        await db.commit()
        await db.refresh(role)

    # Create user
    from ..models.user import UserCreate
    import uuid
    # Generate unique email by adding a random suffix to avoid conflicts
    base_email = request.ad_name.replace(' ', '.').lower()
    unique_email = f"{base_email}.{str(uuid.uuid4())[:8]}@example.com"
    unique_username = f"{request.ad_name.replace(' ', '').lower()}.{str(uuid.uuid4())[:8]}"

    # Create user with all required fields, explicitly setting company_id to None to avoid foreign key constraint
    user_create = UserCreate(
        full_name=request.ad_name,
        email=unique_email,  # Default email with unique suffix
        username=unique_username,
        role_id=role.id,
        phone=request.ad_phone,
        address=request.ad_address,
        cnic=request.ad_cnic,
        branch=request.ad_branch,
        password=request.ad_password if request.ad_password else "default_password123",
        company_id=None  # Explicitly set to None to avoid foreign key constraint issue
    )

    created_user = await UserService.create_user(db, user_create)

    return {
        "ad_id": str(created_user.id),
        "ad_name": created_user.full_name,
        "ad_role": role.name,
        "ad_phone": request.ad_phone or "",
        "ad_address": request.ad_address or "",
        "ad_cnic": request.ad_cnic or "",
        "ad_branch": request.ad_branch or "",
        "message": "Admin user created successfully"
    }


@router.put("/updateadmin/{id}")
async def update_admin(
    id: str,
    request: UpdateAdminRequest,
    current_user: User = Depends(admin_required_from_session()),
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

    # Prepare update data - only include fields that are provided
    from ..models.user import UserUpdate
    update_data = {}

    if request.ad_name is not None:
        update_data["full_name"] = request.ad_name
    if request.ad_phone is not None:
        update_data["phone"] = request.ad_phone
    if request.ad_address is not None:
        update_data["address"] = request.ad_address
    if request.ad_cnic is not None:
        update_data["cnic"] = request.ad_cnic
    if request.ad_branch is not None:
        update_data["branch"] = request.ad_branch

    if request.ad_role:
        from ..models.role import Role
        from sqlalchemy import select
        role_result = await db.execute(select(Role).where(Role.name == request.ad_role))
        role = role_result.scalar_one_or_none()
        if role:
            update_data["role_id"] = str(role.id)  # Convert UUID to string for audit logging

    if request.ad_password:
        # In a real implementation, you'd hash the password here
        # For now, we'll skip updating the password in this example
        pass

    # Convert UUIDs to strings for audit logging
    audit_data = update_data.copy()
    for key, value in audit_data.items():
        if isinstance(value, UUID):
            audit_data[key] = str(value)

    user_update = UserUpdate(**update_data)
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
        "ad_phone": updated_user.phone or "",
        "ad_address": updated_user.address or "",
        "ad_cnic": updated_user.cnic or "",
        "ad_branch": updated_user.branch or "",
        "message": "Admin user updated successfully"
    }


# Product-related endpoints required by the JavaScript frontend

@router.get("/getmaxproid")
async def get_max_pro_id(
    current_user: User = Depends(admin_required_from_session()),
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

@router.get("/getproducts/{id}")
async def get_products(
    id: str,
    current_user: User = Depends(admin_required_from_session()),
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

@router.get("/viewproduct")
async def view_product(
    search_string: str = None,
    branches: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required_from_session()),
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

@router.post("/deleteproduct/{id}")
async def delete_product(
    id: str,
    current_user: User = Depends(admin_required_from_session()),  # Keep as admin only for security
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

@router.post("/deleteproductimage/{id}")
async def delete_product_image(
    id: str,
    current_user: User = Depends(admin_required_from_session()),  # Allow employees to manage product images
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
    current_user: User = Depends(admin_required_from_session()),  # Allow employees to create brands
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
    current_user: User = Depends(admin_required_from_session()),  # Allow employees to delete brands
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
    current_user: User = Depends(admin_required_from_session()),  # Allow employees to check stock details
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

@router.get("/getcustomervendorbybranch")
async def get_customer_vendor_by_branch(
    branch: str = None,
    current_user: User = Depends(admin_required_from_session()),  # Allow employees to get category info
    db: AsyncSession = Depends(get_db)
):
    """
    Get salesmen by branch for customer form
    Required by JavaScript frontend
    """
    from ..services.salesman_service import SalesmanService

    # Get all salesmen from the database
    salesmen = await SalesmanService.get_salesmen(db, skip=0, limit=1000)

    # Format the response to match expected frontend structure
    salesmans = []
    for salesman in salesmen:
        salesmans.append({
            "sal_id": str(salesman.id),
            "sal_name": salesman.name
        })

    return {
        "salesmans": salesmans
    }

# Customer-related endpoints required by the JavaScript frontend

@router.get("/getcustomer/{id}")
async def get_customer(
    id: str,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve specific customer details by ID
    Required by JavaScript frontend
    """
    from ..models.customer import Customer
    from ..services.customer_service import CustomerService

    try:
        customer_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer ID format"
        )

    customer = await CustomerService.get_customer(db, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Parse contacts JSON to extract phone
    import json
    contacts_data = {}
    try:
        contacts_data = json.loads(customer.contacts)
    except:
        contacts_data = {"phone": "", "email": ""}

    # Parse address JSON to extract address
    address_data = {}
    try:
        if customer.billing_addr:
            address_data = json.loads(customer.billing_addr)
    except:
        address_data = {"street": "", "city": "", "country": ""}

    # For salesman ID, we'll use a default value for now
    # In a real implementation, you would have a relationship with salesman
    cus_sal_id_fk = "1"  # Placeholder - would come from actual relationship

    # For branch, we'll use a default value or extract from customer data
    # For now, using a field that might store branch info or a default
    branch = getattr(customer, 'branch', '') or ''

    # Map to the expected frontend fields
    customer_data = {
        "cus_id": str(customer.id),
        "cus_name": customer.name,
        "cus_phone": contacts_data.get("phone", ""),
        "cus_cnic": "",  # CNIC not stored in current model, would need extension
        "cus_address": address_data.get("street", ""),
        "cus_sal_id_fk": cus_sal_id_fk,
        "branch": branch
    }

    return customer_data

@router.get("/viewcustomer")
async def view_customer(
    search_string: str = None,
    branches: str = None,
    searchphone: str = None,
    searchaddress: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    View customers with search and branch filtering
    Required by JavaScript frontend
    """
    from ..models.customer import Customer
    from ..services.customer_service import CustomerService

    # Get all customers with pagination
    customers = await CustomerService.get_customers(db, skip=skip, limit=limit)

    # Apply filters
    filtered_customers = []
    for customer in customers:
        # Apply branch filter if provided
        if branches:
            # For now, assuming there's a branch field in customer model
            # In a real implementation, you would check the actual branch field
            customer_branch = getattr(customer, 'branch', '')
            if customer_branch != branches:
                continue

        # Apply search filters
        should_include = True
        if search_string:
            search_lower = search_string.lower()
            if search_lower not in customer.name.lower():
                should_include = False

        if should_include and searchphone:
            import json
            try:
                contacts_data = json.loads(customer.contacts)
                phone = contacts_data.get("phone", "")
                if searchphone not in phone:
                    should_include = False
            except:
                should_include = False

        if should_include and searchaddress:
            import json
            try:
                address_data = {}
                if customer.billing_addr:
                    address_data = json.loads(customer.billing_addr)
                address = address_data.get("street", "")
                if searchaddress not in address:
                    should_include = False
            except:
                should_include = False

        if should_include:
            filtered_customers.append(customer)

    # Format the response to match expected frontend structure
    result = []
    for customer in filtered_customers:
        import json
        contacts_data = {}
        try:
            contacts_data = json.loads(customer.contacts)
        except:
            contacts_data = {"phone": "", "email": ""}

        address_data = {}
        try:
            if customer.billing_addr:
                address_data = json.loads(customer.billing_addr)
        except:
            address_data = {"street": "", "city": "", "country": ""}

        result.append({
            "cus_id": str(customer.id),
            "cus_name": customer.name,
            "cus_phone": contacts_data.get("phone", ""),
            "cus_cnic": "",  # Placeholder
            "cus_address": address_data.get("street", ""),
            "cus_sal_id_fk": "1",  # Placeholder
            "branch": getattr(customer, 'branch', ''),
            "cus_balance": float(customer.credit_limit)
        })

    return result

@router.post("/deletecustomer/{id}")
async def delete_customer(
    id: str,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a customer by ID
    Required by JavaScript frontend
    """
    from ..services.customer_service import CustomerService

    try:
        customer_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer ID format"
        )

    success = await CustomerService.delete_customer(db, customer_id, str(current_user.id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return {
        "success": True,
        "message": "Customer deleted successfully"
    }

@router.post("/getcustomerbalance")
async def get_customer_balance(
    branches: str = None,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get customer balance by branch
    Required by JavaScript frontend
    """
    # In a real implementation, this would calculate actual customer balances
    # For now, returning a default value
    if branches:
        # If branch is specified, you might filter customers by branch
        # and calculate the total balance for that branch
        balance = 5000.0  # Placeholder value
    else:
        balance = 10000.0  # Default placeholder value

    return {
        "cus_balance": balance
    }

@router.post("/customerviewreport")
async def customer_view_report(
    timezone: str = None,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate customer view report
    Required by JavaScript frontend
    """
    # In a real implementation, this would generate a PDF report
    # For now, returning a placeholder response
    # This would typically involve creating a PDF and returning base64 encoded data

    # Placeholder response - in real implementation, this would generate an actual report
    import base64
    # Create a simple placeholder PDF content (this is just a minimal PDF header)
    pdf_content = "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    pdf_content += "2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    pdf_content += "3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
    pdf_content += "4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Customer Report) Tj\nET\nendstream\nendobj\n"
    pdf_content += "xref\n0 5\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n%%EOF"

    # Encode to base64
    encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

    return encoded_pdf

# Vendor-related endpoints required by the JavaScript frontend

@router.get("/getvendor/{id}")
async def get_vendor(
    id: str,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve specific vendor details by ID
    Required by JavaScript frontend
    """
    from ..models.vendor import Vendor
    from ..services.vendor_service import VendorService

    try:
        vendor_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor ID format"
        )

    vendor = await VendorService.get_vendor(db, vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    # Parse contacts JSON to extract phone and address
    import json
    contacts_data = {}
    try:
        contacts_data = json.loads(vendor.contacts)
    except:
        contacts_data = {"phone": "", "email": "", "address": ""}

    # Map to the expected frontend fields
    vendor_data = {
        "ven_id": str(vendor.id),
        "ven_name": vendor.name,
        "ven_phone": contacts_data.get("phone", ""),
        "ven_address": contacts_data.get("address", ""),
        "branch": getattr(vendor, 'branch', '') or ''  # Using getattr to safely access branch field
    }

    return vendor_data

@router.get("/viewvendor")
async def view_vendor(
    search_string: str = None,
    branches: str = None,
    searchphone: str = None,
    searchaddress: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    View vendors with search and branch filtering
    Required by JavaScript frontend
    """
    from ..models.vendor import Vendor
    from ..services.vendor_service import VendorService

    # Get all vendors with pagination
    vendors = await VendorService.get_vendors(db, skip=skip, limit=limit)

    # Apply filters
    filtered_vendors = []
    for vendor in vendors:
        # Apply branch filter if provided
        if branches:
            # For now, assuming there's a branch field in vendor model
            # In a real implementation, you would check the actual branch field
            vendor_branch = getattr(vendor, 'branch', '')
            if vendor_branch != branches:
                continue

        # Apply search filters
        should_include = True
        if search_string:
            search_lower = search_string.lower()
            if search_lower not in vendor.name.lower():
                should_include = False

        if should_include and searchphone:
            import json
            try:
                contacts_data = json.loads(vendor.contacts)
                phone = contacts_data.get("phone", "")
                if searchphone not in phone:
                    should_include = False
            except:
                should_include = False

        if should_include and searchaddress:
            import json
            try:
                contacts_data = {}
                if vendor.contacts:
                    contacts_data = json.loads(vendor.contacts)
                address = contacts_data.get("address", "")
                if searchaddress not in address:
                    should_include = False
            except:
                should_include = False

        if should_include:
            filtered_vendors.append(vendor)

    # Format the response to match expected frontend structure
    result = []
    for vendor in filtered_vendors:
        import json
        contacts_data = {}
        try:
            contacts_data = json.loads(vendor.contacts)
        except:
            contacts_data = {"phone": "", "email": "", "address": ""}

        result.append({
            "ven_id": str(vendor.id),
            "ven_name": vendor.name,
            "ven_phone": contacts_data.get("phone", ""),
            "ven_address": contacts_data.get("address", ""),
            "branch": getattr(vendor, 'branch', '')
        })

    return result

@router.post("/deletevendor/{id}")
async def delete_vendor(
    id: str,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a vendor by ID
    Required by JavaScript frontend
    """
    from ..services.vendor_service import VendorService

    try:
        vendor_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid vendor ID format"
        )

    success = await VendorService.delete_vendor(db, vendor_id, str(current_user.id))
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    return {
        "success": True,
        "message": "Vendor deleted successfully"
    }

@router.post("/getvendorbalance")
async def get_vendor_balance(
    branches: str = None,
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get vendor balance by branch
    Required by JavaScript frontend
    """
    # In a real implementation, this would calculate actual vendor balances
    # For now, returning a default value
    if branches:
        # If branch is specified, you might filter vendors by branch
        # and calculate the total balance for that branch
        balance = 5000.0  # Placeholder value
    else:
        balance = 10000.0  # Default placeholder value

    return {
        "cus_balance": balance  # Using cus_balance as per the frontend expectation
    }

@router.post("/vendorviewreport")
async def vendor_view_report(
    current_user: User = Depends(admin_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate vendor view report
    Required by JavaScript frontend
    """
    # In a real implementation, this would generate a PDF report
    # For now, returning a placeholder response
    # This would typically involve creating a PDF and returning base64 encoded data

    # Placeholder response - in real implementation, this would generate an actual report
    import base64
    # Create a simple placeholder PDF content (this is just a minimal PDF header)
    pdf_content = "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    pdf_content += "2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    pdf_content += "3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
    pdf_content += "4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Vendor Report) Tj\nET\nendstream\nendobj\n"
    pdf_content += "xref\n0 5\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n%%EOF"

    # Encode to base64
    encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

    return encoded_pdf


# Stock Management Endpoints required by the JavaScript frontend

@router.get("/viewstock")
async def view_stock(
    search_string: str = None,
    branches: str = None,
    shelf: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required_from_session()),  # Require admin for stock management
    db: AsyncSession = Depends(get_db)
):
    """
    View stock with search and branch filtering
    Required by JavaScript frontend
    """
    from ..models.product import Product
    from sqlalchemy import select

    # Get products with pagination
    statement = select(Product).offset(skip).limit(limit)
    result = await db.execute(statement)
    products = result.scalars().all()

    # Apply filters
    filtered_products = []
    for product in products:
        # Apply branch filter if provided
        if branches and product.branch != branches:
            continue

        # Apply search filter if provided
        should_include = True
        if search_string:
            search_lower = search_string.lower()
            if (search_lower not in product.name.lower() and
                search_lower not in (product.barcode or "").lower() and
                search_lower not in (product.sku or "").lower()):
                should_include = False

        if should_include:
            filtered_products.append(product)

    # Format the response to match frontend expectations
    result = []
    for product in filtered_products:
        # Calculate margin if prices are available
        margin = 0.0
        if product.unit_price and product.cost_price and float(product.cost_price) != 0:
            margin = ((float(product.unit_price) - float(product.cost_price)) / float(product.cost_price)) * 100

        result.append({
            "pro_id": str(product.id),
            "pro_name": product.name,
            "quantity": product.stock_level,
            "branch": product.branch or "",
            "ven_name": "",  # Will need to join with vendor table to get vendor name
            "pro_price": float(product.unit_price) if product.unit_price else 0.0,
            "pro_cost": float(product.cost_price) if product.cost_price else 0.0,
            "pro_barcode": product.barcode or "",
            "pro_dis": float(product.discount) if product.discount else 0.0,
            "cat_id_fk": product.category or "",
            "limitedquan": product.limited_qty,
            "brand": product.brand_action or "",
            "pro_image": product.attributes or "",
            "margin": margin
        })

    return result


@router.get("/searchstock")
async def search_stock(
    branches: str = None,
    search_string: str = None,
    current_user: User = Depends(employee_required_from_session()),  # Allow employees to search stock
    db: AsyncSession = Depends(get_db)
):
    """
    Search stock by branch
    Required by JavaScript frontend
    """
    from ..models.product import Product
    from sqlalchemy import select

    # Build query
    statement = select(Product)

    # Apply filters
    if branches:
        statement = statement.where(Product.branch == branches)
    if search_string:
        statement = statement.where(Product.name.ilike(f"%{search_string}%"))

    # Execute query
    result = await db.execute(statement)
    products = result.scalars().all()

    # Format the response
    result = []
    for product in products:
        result.append({
            "stock_id": str(product.id),
            "pro_name": product.name,
            "quantity": product.stock_level,
            "branch": product.branch or ""
        })

    return result


@router.post("/adjuststock")
async def adjust_stock(
    stock_items: List[Dict] = None,
    timezone: str = None,
    current_user: User = Depends(admin_required_from_session()),  # Only admin can adjust stock
    db: AsyncSession = Depends(get_db)
):
    """
    Adjust stock levels for multiple products
    Required by JavaScript frontend
    """
    from ..models.product import Product
    from ..models.stock_entry import StockEntry, StockEntryType
    from sqlalchemy import select
    from datetime import datetime

    if not stock_items:
        stock_items = []

    results = []
    for item in stock_items:
        pro_name = item.get('pro_name')
        quantity = int(item.get('quantity', 0))
        stock_id = item.get('stock_id')
        status = item.get('status', 'IN')  # 'IN', 'OUT', 'ADJUST'
        frombranch = item.get('frombranch')
        tobranch = item.get('tobranch')

        # Find the product by name or ID
        if pro_name:
            statement = select(Product).where(Product.name == pro_name)
        elif stock_id:
            try:
                from uuid import UUID
                statement = select(Product).where(Product.id == UUID(stock_id))
            except:
                results.append({
                    "pro_name": pro_name,
                    "status": "failed",
                    "error": "Invalid stock ID format"
                })
                continue
        else:
            continue

        result = await db.execute(statement)
        product = result.scalar_one_or_none()

        if not product:
            results.append({
                "pro_name": pro_name,
                "status": "failed",
                "error": "Product not found"
            })
            continue

        # Determine the type of stock adjustment
        stock_entry_type = StockEntryType.ADJUST
        if status.upper() == 'IN':
            adj_quantity = abs(quantity)
        elif status.upper() == 'OUT':
            adj_quantity = -abs(quantity)
        elif status.upper() == 'TRANSFER':
            # For transfer, we need to move stock from one location to another
            adj_quantity = -abs(quantity)  # Remove from source
            # We would normally add to destination branch as well
        else:  # ADJUST
            adj_quantity = quantity

        # Update product stock level
        product.stock_level += adj_quantity
        await db.commit()

        # Create a stock entry record
        stock_entry = StockEntry(
            product_id=product.id,
            qty=adj_quantity,
            type=stock_entry_type,
            location=f"From: {frombranch} to: {tobranch}" if tobranch and tobranch.strip() != "" else f"Branch: {frombranch}",
            ref=f"STOCK_ADJ_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )
        db.add(stock_entry)
        await db.commit()

        results.append({
            "pro_name": product.name,
            "new_stock_level": product.stock_level,
            "status": "success"
        })

    # Generate a simple PDF report (base64 encoded)
    import base64
    pdf_content = "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    pdf_content += "2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    pdf_content += "3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
    pdf_content += "4 0 obj\n<<\n/Length 60\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Stock Adjustment Report) Tj\nET\nendstream\nendobj\n"
    pdf_content += "xref\n0 5\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n%%EOF"

    encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

    return encoded_pdf


@router.post("/savestockin")
async def save_stock_in(
    stock_items: List[Dict] = None,
    timezone: str = None,
    Date: str = None,
    current_user: User = Depends(admin_required_from_session()),  # Only admin can save stock in
    db: AsyncSession = Depends(get_db)
):
    """
    Save stock in transactions for multiple products
    Required by JavaScript frontend
    """
    from ..models.product import Product
    from ..models.vendor import Vendor
    from ..models.stock_entry import StockEntry, StockEntryType
    from sqlalchemy import select
    import json
    from uuid import uuid4

    if not stock_items:
        stock_items = []

    results = []
    for item in stock_items:
        ven_name = item.get('ven_name')
        pro_name = item.get('pro_name')
        pro_price = float(item.get('pro_price', 0))
        pro_cost = float(item.get('pro_cost', 0))
        quantity = int(item.get('quantity', 0))
        total_cost = float(item.get('totalCost', 0))
        pro_barcode = item.get('pro_barcode')
        cat_name = item.get('cat_name')
        brand = item.get('brand')
        pro_id = item.get('pro_id')
        ven_id = item.get('ven_id')

        # Find or create product
        if pro_id:
            try:
                from uuid import UUID
                pro_uuid = UUID(pro_id)
                statement = select(Product).where(Product.id == pro_uuid)
            except:
                statement = select(Product).where(Product.name == pro_name)
        else:
            statement = select(Product).where(Product.name == pro_name)

        result = await db.execute(statement)
        product = result.scalar_one_or_none()

        if not product:
            # Create new product if not found
            new_product = Product(
                id=uuid4(),
                name=pro_name,
                unit_price=pro_price,
                cost_price=pro_cost,
                stock_level=quantity,
                barcode=pro_barcode,
                category=cat_name,
                brand_action=brand,
                sku=pro_barcode,
                supplier_id=UUID(ven_id) if ven_id and ven_id != "None" else None
            )
            db.add(new_product)
            await db.commit()
            await db.refresh(new_product)
            product = new_product
        else:
            # Update existing product stock
            product.stock_level += quantity
            product.unit_price = pro_price
            product.cost_price = pro_cost
            product.barcode = pro_barcode
            product.category = cat_name
            product.brand_action = brand
            await db.commit()

        # Create stock entry record
        stock_entry = StockEntry(
            product_id=product.id,
            qty=quantity,
            type=StockEntryType.IN,
            location="Stock In",
            ref=f"STOCK_IN_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )
        db.add(stock_entry)
        await db.commit()

        results.append({
            "pro_name": product.name,
            "new_stock_level": product.stock_level,
            "status": "success"
        })

    return {
        "message": "Stock in transactions saved successfully",
        "results": results
    }


@router.post("/stockreport")
async def stock_report(
    cat_name: str = None,
    pro_name: str = None,
    ven_name: str = None,
    timezone: str = None,
    branches: str = None,
    shelf: str = None,
    current_user: User = Depends(admin_required_from_session()),  # Only admin can generate reports
    db: AsyncSession = Depends(get_db)
):
    """
    Generate stock report in PDF format
    Required by JavaScript frontend
    """
    from ..models.product import Product
    from sqlalchemy import select

    # Build query with filters
    statement = select(Product)

    if cat_name:
        statement = statement.where(Product.category == cat_name)
    if pro_name:
        statement = statement.where(Product.name.ilike(f"%{pro_name}%"))
    if branches:
        statement = statement.where(Product.branch == branches)
    if shelf:
        # Assuming shelf is part of product location info
        pass  # Add shelf filtering if needed

    result = await db.execute(statement)
    products = result.scalars().all()

    # Generate a simple PDF report (base64 encoded)
    import base64
    pdf_content = "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    pdf_content += "2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    pdf_content += "3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
    pdf_content += "4 0 obj\n<<\n/Length 50\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Stock Report) Tj\nET\nendstream\nendobj\n"
    pdf_content += "xref\n0 5\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n%%EOF"

    encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

    return encoded_pdf


@router.post("/stockreportexcel")
async def stock_report_excel(
    cat_name: str = None,
    pro_name: str = None,
    ven_name: str = None,
    timezone: str = None,
    branches: str = None,
    shelf: str = None,
    current_user: User = Depends(admin_required_from_session()),  # Only admin can generate reports
    db: AsyncSession = Depends(get_db)
):
    """
    Generate stock report in Excel format
    Required by JavaScript frontend
    """
    from fastapi.responses import StreamingResponse
    import io
    from openpyxl import Workbook
    from ..models.product import Product
    from sqlalchemy import select

    # Build query with filters
    statement = select(Product)

    if cat_name:
        statement = statement.where(Product.category == cat_name)
    if pro_name:
        statement = statement.where(Product.name.ilike(f"%{pro_name}%"))
    if branches:
        statement = statement.where(Product.branch == branches)
    if shelf:
        # Assuming shelf is part of product location info
        pass  # Add shelf filtering if needed

    result = await db.execute(statement)
    products = result.scalars().all()

    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Stock Report"

    # Add headers
    headers = ["Product ID", "Product Name", "Quantity", "Branch", "Price", "Cost", "Barcode", "Category", "Brand"]
    ws.append(headers)

    # Add data
    for product in products:
        row = [
            str(product.id),
            product.name,
            product.stock_level,
            product.branch or "",
            float(product.unit_price) if product.unit_price else 0.0,
            float(product.cost_price) if product.cost_price else 0.0,
            product.barcode or "",
            product.category or "",
            product.brand_action or ""
        ]
        ws.append(row)

    # Save to bytes
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # Return as streaming response (will be handled by frontend differently)
    # For now, return a placeholder base64 representation
    import base64
    excel_content = buffer.getvalue()
    encoded_excel = base64.b64encode(excel_content).decode()

    return encoded_excel


@router.post("/dailyinventoryreport")
async def daily_inventory_report(
    current_user: User = Depends(admin_required_from_session()),  # Only admin can generate reports
    db: AsyncSession = Depends(get_db)
):
    """
    Generate daily inventory report in PDF format
    Required by JavaScript frontend
    """
    from ..models.product import Product
    from sqlalchemy import select
    from datetime import datetime

    # Get all products
    statement = select(Product)
    result = await db.execute(statement)
    products = result.scalars().all()

    # Generate a simple PDF report (base64 encoded)
    import base64
    pdf_content = "%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n"
    pdf_content += "2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n"
    pdf_content += "3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n"
    pdf_content += "4 0 obj\n<<\n/Length 60\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Daily Inventory Report - " + datetime.now().strftime("%Y-%m-%d") + ") Tj\nET\nendstream\nendobj\n"
    pdf_content += "xref\n0 5\ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\n%%EOF"

    encoded_pdf = base64.b64encode(pdf_content.encode()).decode()

    return encoded_pdf


@router.post("/printbarcodes")
async def print_barcodes(
    pro_name: str,
    quantity: int,
    barcode: str = None,
    current_user: User = Depends(admin_required_from_session()),  # Only admin can print barcodes
    db: AsyncSession = Depends(get_db)
):
    """
    Generate ZPL commands for printing barcodes for a product
    Required by JavaScript frontend for Zebra printer integration
    """
    from ..models.product import Product
    from sqlalchemy import select

    # Get product details if barcode not provided
    if not barcode:
        statement = select(Product).where(Product.name == pro_name)
        result = await db.execute(statement)
        product = result.scalar_one_or_none()

        if product:
            barcode = product.barcode or product.sku or pro_name

    if not barcode:
        barcode = pro_name  # Fallback to product name

    # Generate ZPL commands for printing multiple barcodes based on quantity
    zpl_commands = "^XA"  # Start format

    # Calculate how many labels per row/column based on printer settings
    labels_per_row = 2  # Adjust based on your label size
    labels_per_col = 3  # Adjust based on your label size

    # For each item to print (based on quantity)
    for i in range(quantity):
        row = (i // labels_per_row) % labels_per_col
        col = i % labels_per_row

        # Position the label (adjust coordinates based on your label size)
        x_pos = col * 200  # Horizontal spacing
        y_pos = row * 150  # Vertical spacing

        # Add the barcode and text to the ZPL command
        zpl_commands += f"^FO{x_pos},{y_pos}"  # Field origin (position)
        zpl_commands += "^BY2,3,100"  # Bar code field params (width, height, gap)
        zpl_commands += f"^BCN,100,Y,N,N,A"  # Code 128 barcode
        zpl_commands += f"^FD{barcode}^FS"  # Field data and end field
        zpl_commands += f"^FO{x_pos},{y_pos+100}"  # Position for product name
        zpl_commands += "^A0N,25,25"  # Font A, Normal, 25 dots wide, 25 dots high
        zpl_commands += f"^FD{pro_name}^FS"  # Product name

        # Add a new label start if we've reached the max per sheet
        if (i + 1) % (labels_per_row * labels_per_col) == 0:
            zpl_commands += "^XZ"  # End format
            zpl_commands += "^XA"  # Start new format

    zpl_commands += "^XZ"  # End format

    return {
        "zpl_commands": zpl_commands,
        "product": pro_name,
        "quantity": quantity,
        "barcode": barcode,
        "message": f"Generated ZPL for {quantity} barcode(s) of {pro_name}"
    }


# Enhanced SaveStockIn to include barcode printing capability
@router.post("/savestockinwithbarcodes")
async def save_stock_in_with_barcodes(
    stock_items: List[Dict] = None,
    timezone: str = None,
    Date: str = None,
    print_barcodes: bool = False,
    current_user: User = Depends(admin_required_from_session()),  # Only admin can save stock in
    db: AsyncSession = Depends(get_db)
):
    """
    Save stock in transactions and optionally generate ZPL commands for barcode printing
    Required by JavaScript frontend for integrated barcode printing
    """
    from ..models.product import Product
    from ..models.vendor import Vendor
    from ..models.stock_entry import StockEntry, StockEntryType
    from sqlalchemy import select
    import json
    from uuid import uuid4

    if not stock_items:
        stock_items = []

    results = []
    zpl_commands_list = []

    for item in stock_items:
        ven_name = item.get('ven_name')
        pro_name = item.get('pro_name')
        pro_price = float(item.get('pro_price', 0))
        pro_cost = float(item.get('pro_cost', 0))
        quantity = int(item.get('quantity', 0))
        total_cost = float(item.get('totalCost', 0))
        pro_barcode = item.get('pro_barcode')
        cat_name = item.get('cat_name')
        brand = item.get('brand')
        pro_id = item.get('pro_id')
        ven_id = item.get('ven_id')

        # Find or create product
        if pro_id:
            try:
                from uuid import UUID
                pro_uuid = UUID(pro_id)
                statement = select(Product).where(Product.id == pro_uuid)
            except:
                statement = select(Product).where(Product.name == pro_name)
        else:
            statement = select(Product).where(Product.name == pro_name)

        result = await db.execute(statement)
        product = result.scalar_one_or_none()

        if not product:
            # Create new product if not found
            new_product = Product(
                id=uuid4(),
                name=pro_name,
                unit_price=pro_price,
                cost_price=pro_cost,
                stock_level=quantity,
                barcode=pro_barcode,
                category=cat_name,
                brand_action=brand,
                sku=pro_barcode,
                supplier_id=UUID(ven_id) if ven_id and ven_id != "None" else None
            )
            db.add(new_product)
            await db.commit()
            await db.refresh(new_product)
            product = new_product
        else:
            # Update existing product stock
            product.stock_level += quantity
            product.unit_price = pro_price
            product.cost_price = pro_cost
            product.barcode = pro_barcode
            product.category = cat_name
            product.brand_action = brand
            await db.commit()

        # Create stock entry record
        from datetime import datetime
        stock_entry = StockEntry(
            product_id=product.id,
            qty=quantity,
            type=StockEntryType.IN,
            location="Stock In",
            ref=f"STOCK_IN_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        )
        db.add(stock_entry)
        await db.commit()

        results.append({
            "pro_name": product.name,
            "new_stock_level": product.stock_level,
            "status": "success"
        })

        # Generate ZPL commands if requested
        if print_barcodes and quantity > 0:
            barcode_to_use = pro_barcode or product.barcode or product.sku or pro_name

            # Generate ZPL for this product's quantity
            zpl_cmd = "^XA"  # Start format

            # For simplicity, print one label per item in the quantity
            # In a real scenario, you might want to optimize this based on label layout
            for i in range(quantity):
                # Simple positioning - adjust based on your label size
                x_pos = 50
                y_pos = 50 + (i * 150)  # Space labels vertically

                zpl_cmd += f"^FO{x_pos},{y_pos}"  # Field origin
                zpl_cmd += "^BY2,3,100"  # Bar code field params
                zpl_cmd += f"^BCN,100,Y,N,N,A"  # Code 128 barcode
                zpl_cmd += f"^FD{barcode_to_use}^FS"  # Field data
                zpl_cmd += f"^FO{x_pos},{y_pos+100}"  # Position for product name
                zpl_cmd += "^A0N,25,25"  # Font
                zpl_cmd += f"^FD{pro_name}^FS"  # Product name

            zpl_cmd += "^XZ"  # End format
            zpl_commands_list.append({
                "product": pro_name,
                "zpl_commands": zpl_cmd
            })

    response = {
        "message": "Stock in transactions saved successfully",
        "results": results
    }

    if print_barcodes and zpl_commands_list:
        response["zpl_commands"] = zpl_commands_list
        response["print_requested"] = True

    return response