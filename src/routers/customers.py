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

# Endpoints required by the JavaScript frontend

@router.get("/get-customer/{id}")
def get_customer_details(
    id: str,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Retrieve specific customer details by ID
    Required by JavaScript frontend
    """
    try:
        customer_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer ID format"
        )

    customer = CustomerService.get_customer(db, customer_id)
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
        "branch": branch,
        "cus_balance": float(customer.credit_limit)  # Using credit_limit as placeholder for balance
    }

    return customer_data

@router.get("/view-customer")
def view_customers(
    search_string: str = None,
    branches: str = None,
    searchphone: str = None,
    searchaddress: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    View customers with search and branch filtering
    Required by JavaScript frontend
    """
    # Get all customers with pagination
    customers = CustomerService.get_customers(db, skip=skip, limit=limit)

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

@router.post("/delete-customer/{id}")
def delete_customer_frontend(
    id: str,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Delete a customer by ID (frontend compatible response)
    Required by JavaScript frontend
    """
    try:
        customer_id = UUID(id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid customer ID format"
        )

    success = CustomerService.delete_customer(db, customer_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return {
        "success": True,
        "message": "Customer deleted successfully"
    }

@router.post("/get-customer-balance")
def get_customer_balance(
    branches: str = None,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
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

@router.post("/customer-view-report")
def customer_view_report(
    timezone: str = None,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
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

@router.get("/get-customer-vendor-by-branch")
def get_customer_vendor_by_branch(
    branch: str = None,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Get customers and salesmen by branch
    Required by JavaScript frontend
    """
    # For now, return a mock response with salesman data
    # In a real implementation, you would query actual salesman data

    # If branch is provided, you might filter by branch
    # For now, returning static mock data

    salesmans = [
        {"sal_id": "1", "sal_name": "John Smith"},
        {"sal_id": "2", "sal_name": "Jane Doe"},
        {"sal_id": "3", "sal_name": "Mike Johnson"},
        {"sal_id": "4", "sal_name": "Sarah Williams"}
    ]

    return {
        "salesmans": salesmans
    }