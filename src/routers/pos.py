from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List, Optional
from uuid import UUID
import uuid
from datetime import datetime, timedelta

from ..database.database import get_db
from ..models.invoice import Invoice, InvoiceCreate, InvoiceRead, InvoiceStatus
from ..models.product import Product
from ..models.customer import Customer
from ..models.stock_entry import StockEntryCreate, StockEntryType
from ..services.invoice_service import InvoiceService
from ..services.product_service import ProductService
from ..services.customer_service import CustomerService
from ..services.stock_service import StockService
from ..auth.auth import get_current_user
from ..auth.rbac import cashier_required, admin_required, employee_required

router = APIRouter()

@router.post("/quick-sell", response_model=InvoiceRead)
def quick_sell(
    product_ids: List[str],
    customer_id: str = None,
    current_user: User = Depends(cashier_required()),
    db: Session = Depends(get_db)
):
    """
    Quick sell functionality for cashier users
    Creates an invoice with minimal details for quick transactions
    """
    # Validate product IDs
    validated_product_ids = []
    for pid in product_ids:
        try:
            product_uuid = UUID(pid)
            product = ProductService.get_product(db, product_uuid)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {pid} not found"
                )
            if product.stock_level <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough stock for product {product.name}"
                )
            validated_product_ids.append(product_uuid)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid product ID format: {pid}"
            )

    # If customer ID provided, validate it
    customer_uuid = None
    if customer_id:
        try:
            customer_uuid = UUID(customer_id)
            customer = CustomerService.get_customer(db, customer_uuid)
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Customer with ID {customer_id} not found"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid customer ID format: {customer_id}"
            )

    # Create invoice items
    items = []
    total_amount = 0

    for product_id in validated_product_ids:
        product = ProductService.get_product(db, product_id)
        items.append({
            "product_id": str(product.id),
            "product_name": product.name,
            "quantity": 1,  # Quick sell is typically for 1 item
            "unit_price": float(product.unit_price),
            "total": float(product.unit_price)
        })
        total_amount += float(product.unit_price)

    # Create invoice data
    invoice_create = InvoiceCreate(
        customer_id=customer_uuid or UUID("00000000-0000-0000-0000-000000000000"),  # Default to anonymous customer if not provided
        items=str(items),  # In a real implementation, we'd use proper serialization
        totals=str({"subtotal": total_amount, "tax": 0, "total": total_amount}),
        taxes=0,
        discounts=0,
        status=InvoiceStatus.ISSUED
    )

    # Create the invoice
    invoice = InvoiceService.create_invoice(db, invoice_create, current_user.id)
    return invoice

@router.post("/quick-sell-item", response_model=InvoiceRead)
def quick_sell_item(
    product_id: str,
    quantity: int = 1,
    customer_id: str = None,
    current_user: User = Depends(cashier_required()),
    db: Session = Depends(get_db)
):
    """
    Quick sell a single item functionality for cashier users
    """
    # Validate product ID
    try:
        product_uuid = UUID(product_id)
        product = ProductService.get_product(db, product_uuid)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found"
            )
        if product.stock_level < quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Not enough stock for product {product.name}. Available: {product.stock_level}, Requested: {quantity}"
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid product ID format: {product_id}"
        )

    # If customer ID provided, validate it
    customer_uuid = None
    if customer_id:
        try:
            customer_uuid = UUID(customer_id)
            customer = CustomerService.get_customer(db, customer_uuid)
            if not customer:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Customer with ID {customer_id} not found"
                )
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid customer ID format: {customer_id}"
            )

    # Create invoice item
    items = [{
        "product_id": str(product.id),
        "product_name": product.name,
        "quantity": quantity,
        "unit_price": float(product.unit_price),
        "total": float(product.unit_price) * quantity
    }]
    total_amount = float(product.unit_price) * quantity

    # Create invoice data
    invoice_create = InvoiceCreate(
        customer_id=customer_uuid or UUID("00000000-0000-0000-0000-000000000000"),  # Default to anonymous customer if not provided
        items=str(items),  # In a real implementation, we'd use proper serialization
        totals=str({"subtotal": total_amount, "tax": 0, "total": total_amount}),
        taxes=0,
        discounts=0,
        status=InvoiceStatus.ISSUED
    )

    # Create the invoice
    invoice = InvoiceService.create_invoice(db, invoice_create, current_user.id)
    return invoice

from pydantic import BaseModel

class CashDrawerOpen(BaseModel):
    amount: float
    note: str = ""

class CashDrawerClose(BaseModel):
    expected_amount: float
    actual_amount: float
    note: str = ""

class CashDrawerRecord(BaseModel):
    id: UUID
    cashier_id: UUID
    drawer_opened_at: datetime
    drawer_closed_at: Optional[datetime] = None
    initial_amount: float
    expected_closing_amount: float
    actual_closing_amount: float
    variance: float
    note: Optional[str] = None
    created_at: datetime

class CashDrawerService:
    """
    Service class for handling cash drawer operations
    """

    @staticmethod
    async def record_drawer_open(db: Session, cashier_id: UUID, amount: float, note: str = "") -> dict:
        """
        Record opening of cash drawer
        """
        # In a real implementation, this would create a record in a cash drawer tracking table
        return {
            "message": "Cash drawer opened",
            "amount": amount,
            "timestamp": datetime.utcnow(),
            "cashier_id": str(cashier_id),
            "note": note
        }

    @staticmethod
    async def record_drawer_close(db: Session, cashier_id: UUID, expected_amount: float, actual_amount: float, note: str = "") -> dict:
        """
        Record closing of cash drawer and calculate variance
        """
        variance = actual_amount - expected_amount

        # In a real implementation, this would update the cash drawer record
        return {
            "message": "Cash drawer closed",
            "expected_amount": expected_amount,
            "actual_amount": actual_amount,
            "variance": variance,
            "timestamp": datetime.utcnow(),
            "cashier_id": str(cashier_id),
            "note": note
        }

@router.post("/cash-drawer/open")
def open_cash_drawer(
    request: CashDrawerOpen,
    current_user: User = Depends(cashier_required()),
    db: Session = Depends(get_db)
):
    """
    Record opening of cash drawer with initial amount
    """
    result = CashDrawerService.record_drawer_open(db, current_user.id, request.amount, request.note)
    return result

@router.post("/cash-drawer/close")
def close_cash_drawer(
    request: CashDrawerClose,
    current_user: User = Depends(cashier_required()),
    db: Session = Depends(get_db)
):
    """
    Record closing of cash drawer and calculate variance
    """
    result = CashDrawerService.record_drawer_close(db, current_user.id, request.expected_amount, request.actual_amount, request.note)
    return result

class ShiftClose(BaseModel):
    expected_amount: float
    actual_amount: float
    note: str = ""

@router.post("/shift-close")
def close_shift(
    request: ShiftClose,
    current_user: User = Depends(cashier_required()),
    db: Session = Depends(get_db)
):
    """
    Close the cashier's shift and generate final report
    """
    # Calculate variance
    variance = request.actual_amount - request.expected_amount

    # In a real implementation, this would:
    # 1. Close the cash drawer
    # 2. Generate a detailed shift report
    # 3. Record the shift closure
    # 4. Update cashier's shift status

    shift_closure = {
        "message": "Shift closed successfully",
        "cashier": current_user.username,
        "shift_close_time": datetime.utcnow(),
        "expected_amount": request.expected_amount,
        "actual_amount": request.actual_amount,
        "variance": variance,
        "note": request.note,
        "report": {
            "total_transactions": 0,  # Would come from actual data
            "total_sales": request.actual_amount,  # Simplified for demo
            "total_refunds": 0,  # Would come from actual data
        }
    }

    return shift_closure

@router.get("/shift-report")
def get_shift_report(
    current_user: User = Depends(cashier_required()),
    db: Session = Depends(get_db)
):
    """
    Get shift report for the current cashier
    """
    # This would typically aggregate data for the current shift
    from sqlmodel import select
    from ..models.invoice import Invoice, InvoiceStatus

    # Get invoices for the current user during the shift (today)
    today_start = datetime.combine(datetime.today().date(), datetime.min.time())
    today_end = datetime.combine(datetime.today().date(), datetime.max.time())

    # In a real implementation, we'd filter by date range and cashier
    # For now, we'll return a basic report
    return {
        "cashier": current_user.username,
        "shift_date": datetime.today().date(),
        "total_transactions": 0,  # This would come from actual data
        "total_sales": 0,  # This would come from actual data
        "total_refunds": 0,  # This would come from actual data
        "generated_at": datetime.utcnow()
    }

@router.get("/daily-report")
def get_daily_report(
    date: str = None,
    current_user: User = Depends(cashier_required()),
    db: Session = Depends(get_db)
):
    """
    Get daily report for the current cashier or for a specific date
    """
    # Parse date or use today
    report_date = datetime.today().date()
    if date:
        try:
            report_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )

    # This would typically aggregate data for the specified date
    # In a real implementation, we'd query the database for invoices, refunds, etc.
    # For now, we'll return a template report
    report = {
        "report_type": "daily",
        "date": report_date.isoformat(),
        "generated_at": datetime.utcnow(),
        "cashier": current_user.username,
        "summary": {
            "total_transactions": 0,  # Would come from actual data
            "total_sales": 0,  # Would come from actual data
            "total_refunds": 0,  # Would come from actual data
            "net_sales": 0,  # Would come from actual data
            "avg_transaction_value": 0  # Would come from actual data
        },
        "by_payment_method": {
            "cash": 0,
            "card": 0,
            "other": 0
        },
        "top_selling_items": []  # Would come from actual data
    }

    return report

@router.get("/sales-report")
def get_sales_report(
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(cashier_required()),
    db: Session = Depends(get_db)
):
    """
    Get sales report for a date range
    """
    # Parse dates or use default range (last 7 days)
    end_dt = datetime.today().date()
    start_dt = end_dt - timedelta(days=7)

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start date format. Use YYYY-MM-DD"
            )

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end date format. Use YYYY-MM-DD"
            )

    if start_dt > end_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )

    # This would typically aggregate sales data for the date range
    # For now, we'll return a template report
    report = {
        "report_type": "sales",
        "date_range": {
            "start": start_dt.isoformat(),
            "end": end_dt.isoformat()
        },
        "generated_at": datetime.utcnow(),
        "summary": {
            "total_sales": 0,  # Would come from actual data
            "total_transactions": 0,  # Would come from actual data
            "total_refunds": 0,  # Would come from actual data
            "net_sales": 0,  # Would come from actual data
            "avg_transaction_value": 0  # Would come from actual data
        },
        "by_cashier": [],  # Would break down by cashier
        "by_category": [],  # Would break down by product category
        "trends": {
            "busiest_day": None,  # Would come from actual data
            "peak_hours": []  # Would come from actual data
        }
    }

    return report

@router.get("/duplicate-bill/{invoice_id}")
def get_duplicate_bill(
    invoice_id: str,
    current_user: User = Depends(cashier_required()),
    db: Session = Depends(get_db)
):
    """
    Get duplicate bill for an existing invoice
    """
    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    invoice = InvoiceService.get_invoice(db, invoice_uuid)

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Get customer details if available
    customer = None
    if invoice.customer_id:
        customer = CustomerService.get_customer(db, invoice.customer_id)

    # Parse items from the stored JSON string
    import json
    try:
        items = json.loads(invoice.items) if isinstance(invoice.items, str) else invoice.items
    except:
        items = []

    # Calculate totals
    subtotal = 0
    tax_total = float(invoice.taxes)
    discount_total = float(invoice.discounts) if invoice.discounts else 0

    for item in items:
        if isinstance(item, dict):
            subtotal += float(item.get('total', 0))

    total = subtotal + tax_total - discount_total

    # Return detailed invoice for duplicate bill
    duplicate_bill = {
        "invoice_details": {
            "invoice_no": invoice.invoice_no,
            "invoice_id": str(invoice.id),
            "created_at": invoice.created_at.isoformat(),
            "status": invoice.status.value
        },
        "customer_info": {
            "id": str(customer.id) if customer else None,
            "name": customer.name if customer else "Walk-in Customer",
            "contact": customer.contacts if customer and hasattr(customer, 'contacts') else ""
        } if customer else {
            "id": None,
            "name": "Walk-in Customer",
            "contact": ""
        },
        "items": items,
        "totals": {
            "subtotal": round(subtotal, 2),
            "tax": round(tax_total, 2),
            "discount": round(discount_total, 2),
            "total": round(total, 2)
        },
        "cashier": current_user.username,
        "printed_at": datetime.utcnow().isoformat(),
        "print_count": 1  # In a real implementation, this would track how many times printed
    }

    return duplicate_bill

@router.post("/duplicate-bill/{invoice_id}")
def print_duplicate_bill(
    invoice_id: str,
    current_user: User = Depends(cashier_required()),
    db: Session = Depends(get_db)
):
    """
    Print duplicate bill for an existing invoice (with print tracking)
    """
    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )

    invoice = InvoiceService.get_invoice(db, invoice_uuid)

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )

    # Get customer details if available
    customer = None
    if invoice.customer_id:
        customer = CustomerService.get_customer(db, invoice.customer_id)

    # Parse items from the stored JSON string
    import json
    try:
        items = json.loads(invoice.items) if isinstance(invoice.items, str) else invoice.items
    except:
        items = []

    # Calculate totals
    subtotal = 0
    tax_total = float(invoice.taxes)
    discount_total = float(invoice.discounts) if invoice.discounts else 0

    for item in items:
        if isinstance(item, dict):
            subtotal += float(item.get('total', 0))

    total = subtotal + tax_total - discount_total

    # Return detailed invoice for printing
    duplicate_bill = {
        "invoice_details": {
            "invoice_no": invoice.invoice_no,
            "invoice_id": str(invoice.id),
            "created_at": invoice.created_at.isoformat(),
            "status": invoice.status.value
        },
        "customer_info": {
            "id": str(customer.id) if customer else None,
            "name": customer.name if customer else "Walk-in Customer",
            "contact": customer.contacts if customer and hasattr(customer, 'contacts') else ""
        } if customer else {
            "id": None,
            "name": "Walk-in Customer",
            "contact": ""
        },
        "items": items,
        "totals": {
            "subtotal": round(subtotal, 2),
            "tax": round(tax_total, 2),
            "discount": round(discount_total, 2),
            "total": round(total, 2)
        },
        "cashier": current_user.username,
        "printed_at": datetime.utcnow().isoformat(),
        "message": "Duplicate bill generated successfully"
    }

    # In a real implementation, you might want to track the number of prints
    # This could involve updating an audit log or a print counter

    return duplicate_bill

# Import statement needed for User type hint
from ..models.user import User