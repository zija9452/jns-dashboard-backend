from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
import base64
from uuid import UUID

from ..database.database import get_db
from ..models.invoice import Invoice
from ..models.customer_invoice import CustomerInvoice
from ..models.warehouse_invoice import WarehouseInvoice
from ..models.user import User
from ..auth.session_auth import cashier_required_from_session, admin_cashier_employee_required_from_session
from ..utils.cache import cache

router = APIRouter()


@router.get("/search")
async def search_duplicate_bills(
    search_query: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(8, ge=1, le=100),
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for invoices from both walk-in and customer invoices
    Returns last 24 hours data by default, or search results if query provided
    Supports pagination with page and limit parameters
    """
    # Calculate 24 hours ago
    now = datetime.now()
    twenty_four_hours_ago = now - timedelta(hours=24)

    invoice_list = []

    # Search walk-in invoices (SIN- prefix)
    if search_query:
        # Search by invoice number
        walkin_statement = select(Invoice).where(
            and_(
                Invoice.invoice_no.like("SIN-%"),
                or_(
                    Invoice.invoice_no.ilike(f"%{search_query}%"),
                    Invoice.customer_name.ilike(f"%{search_query}%")
                )
            )
        )
    else:
        # Last 24 hours
        walkin_statement = select(Invoice).where(
            and_(
                Invoice.invoice_no.like("SIN-%"),
                Invoice.payment_date >= twenty_four_hours_ago
            )
        )

    walkin_result = await db.execute(walkin_statement)
    walkin_invoices = walkin_result.scalars().all()

    for inv in walkin_invoices:
        try:
            items_data = json.loads(inv.items) if inv.items else []
            totals_data = json.loads(inv.totals) if inv.totals else {}

            invoice_list.append({
                "id": str(inv.id),
                "invoice_no": inv.invoice_no,
                "customer_name": inv.customer_name or "Walk-in Customer",
                "type": "walkin",
                "total_amount": float(inv.total_amount),
                "amount_paid": float(inv.amount_paid),
                "balance_due": float(inv.total_amount - inv.amount_paid),
                "discount": float(totals_data.get('discount', 0)),
                "payment_status": inv.payment_status,
                "payment_method": inv.payment_method,
                "payment_date": inv.payment_date.isoformat() if inv.payment_date else inv.created_at.isoformat(),
                "created_at": inv.created_at.isoformat(),
                "items": items_data
            })
        except Exception as e:
            continue

    # Search customer invoices (CIN- prefix)
    if search_query:
        customer_statement = select(CustomerInvoice).where(
            or_(
                CustomerInvoice.invoice_no.ilike(f"%{search_query}%"),
                CustomerInvoice.customer_name.ilike(f"%{search_query}%"),
                CustomerInvoice.team_name.ilike(f"%{search_query}%")
            )
        )
    else:
        # Last 24 hours
        customer_statement = select(CustomerInvoice).where(
            CustomerInvoice.created_at >= twenty_four_hours_ago
        )

    customer_result = await db.execute(customer_statement)
    customer_invoices = customer_result.scalars().all()

    for inv in customer_invoices:
        try:
            items_data = json.loads(inv.items) if inv.items else []
            totals_data = json.loads(inv.totals) if inv.totals else {}

            invoice_list.append({
                "id": str(inv.id),
                "invoice_no": inv.invoice_no,
                "customer_name": inv.customer_name or "N/A",
                "team_name": inv.team_name or "",
                "type": "customer",
                "total_amount": float(inv.total_amount),
                "amount_paid": float(inv.amount_paid),
                "balance_due": float(inv.balance_due),
                "discount": float(inv.discounts or 0),
                "payment_status": inv.payment_status,
                "payment_method": inv.payment_method,
                "payment_date": inv.created_at.isoformat(),
                "created_at": inv.created_at.isoformat(),
                "items": items_data
            })
        except Exception as e:
            continue

    # Search warehouse invoices (WIN- prefix)
    if search_query:
        warehouse_statement = select(WarehouseInvoice).where(
            or_(
                WarehouseInvoice.invoice_no.ilike(f"%{search_query}%"),
                WarehouseInvoice.customer_name.ilike(f"%{search_query}%")
            )
        )
    else:
        # Last 24 hours
        warehouse_statement = select(WarehouseInvoice).where(
            WarehouseInvoice.created_at >= twenty_four_hours_ago
        )

    warehouse_result = await db.execute(warehouse_statement)
    warehouse_invoices = warehouse_result.scalars().all()

    for inv in warehouse_invoices:
        try:
            items_data = json.loads(inv.items) if inv.items else []
            totals_data = json.loads(inv.totals) if inv.totals else {}

            invoice_list.append({
                "id": str(inv.id),
                "invoice_no": inv.invoice_no,
                "customer_name": inv.customer_name or "N/A",
                "type": "warehouse",
                "total_amount": float(inv.total_amount),
                "amount_paid": float(inv.amount_paid),
                "balance_due": float(inv.total_amount - inv.amount_paid),
                "discount": float(inv.discounts or 0),
                "payment_status": inv.payment_status,
                "payment_method": inv.payment_method,
                "payment_date": inv.payment_date.isoformat() if inv.payment_date else inv.created_at.isoformat(),
                "created_at": inv.created_at.isoformat(),
                "items": items_data
            })
        except Exception as e:
            continue


    # Sort by payment_date descending (most recent first)
    invoice_list.sort(key=lambda x: x.get('payment_date', ''), reverse=True)

    # Apply pagination
    total_items = len(invoice_list)
    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    paginated_invoices = invoice_list[start_idx:end_idx]

    return {
        "invoices": paginated_invoices,
        "total": total_items,
        "page": page,
        "limit": limit,
        "total_pages": (total_items + limit - 1) // limit,
        "search_query": search_query,
        "time_range": "last_24_hours" if not search_query else "search_results"
    }


@router.get("/{invoice_id}/duplicate")
async def get_duplicate_invoice(
    invoice_id: str,
    invoice_type: str = Query(..., description="Type: 'walkin' or 'customer'"),
    current_user: User = Depends(admin_cashier_employee_required_from_session()),  # All authenticated users can access
    db: AsyncSession = Depends(get_db)
):
    """
    Get duplicate invoice PDF with 7-day Redis cache
    """
    try:
        invoice_uuid = UUID(invoice_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice ID format"
        )
    
    # Check Redis cache first (7 days)
    cache_key = f"invoice:duplicate:{invoice_type}:{invoice_id}"
    cached_pdf = await cache.get(cache_key)
    
    if cached_pdf:
        # Return cached PDF
        return {
            "pdf": cached_pdf,
            "source": "cache",
            "bill_type": "DUPLICATE BILL"
        }
    
    # Not cached - generate PDF
    if invoice_type == "walkin":
        # Get walk-in invoice
        statement = select(Invoice).where(Invoice.id == invoice_uuid)
        result = await db.execute(statement)
        invoice = result.scalar_one_or_none()
        
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Walk-in invoice not found"
            )
        
        # Parse items
        items_data = json.loads(invoice.items) if invoice.items else []
        
        # Import PDF generator from walkin_invoice
        from .walkin_invoice import generate_walkin_receipt_pdf
        
        # Generate PDF with "DUPLICATE BILL"
        pdf_data = generate_walkin_receipt_pdf(
            invoice_no=invoice.invoice_no,
            customer_name=invoice.customer_name,
            team_name="",
            items=items_data,
            total_amount=float(invoice.total_amount),
            total_discount=float(invoice.discounts or 0),
            amount_paid=float(invoice.amount_paid),
            balance_due=0.0,
            payment_method=invoice.payment_method,
            payment_status=invoice.payment_status,
            created_at=invoice.payment_date or invoice.created_at,
            bill_type="DUPLICATE BILL"
        )
        
    elif invoice_type == "warehouse":
        # Get warehouse invoice
        statement = select(WarehouseInvoice).where(WarehouseInvoice.id == invoice_uuid)
        result = await db.execute(statement)
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Warehouse invoice not found"
            )

        # Parse items
        items_data = json.loads(invoice.items) if invoice.items else []
        
        # Reuse PDF generator logic from walk-in
        from .walkin_invoice import generate_walkin_receipt_pdf
        
        # Generate PDF with "DUPLICATE BILL"
        pdf_data = generate_walkin_receipt_pdf(
            invoice_no=invoice.invoice_no,
            customer_name=invoice.customer_name or "N/A",
            team_name="",
            items=items_data,
            total_amount=float(invoice.total_amount),
            total_discount=float(invoice.discounts or 0),
            amount_paid=float(invoice.amount_paid),
            balance_due=float(invoice.total_amount - invoice.amount_paid),
            payment_method=invoice.payment_method,
            payment_status=invoice.payment_status,
            created_at=invoice.payment_date or invoice.created_at,
            bill_type="DUPLICATE BILL"
        )

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invoice type. Must be 'walkin' or 'customer'"
        )
    
    # Save to Redis for 7 days (604800 seconds)
    await cache.set(cache_key, pdf_data, ttl=604800)
    
    return {
        "pdf": pdf_data,
        "source": "generated",
        "bill_type": "DUPLICATE BILL"
    }
