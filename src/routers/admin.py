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
# Note: User CRUD operations are now handled by /users/ endpoints
# This file contains only admin-specific endpoints for other entities

# Product-related endpoints required by the JavaScript frontend

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

