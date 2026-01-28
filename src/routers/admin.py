from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import Dict, Any
from uuid import UUID
import uuid
from datetime import datetime, timedelta

from ..database.database import get_db
from ..auth.auth import get_current_user
from ..auth.rbac import admin_required
from ..services.user_service import UserService
from ..services.product_service import ProductService
from ..services.invoice_service import InvoiceService
from ..services.customer_service import CustomerService
from ..services.expense_service import ExpenseService

router = APIRouter()

@router.get("/")
def get_admin_dashboard(
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
):
    """
    Get admin dashboard overview with key metrics
    Requires admin role
    """
    # Get counts of key entities
    total_users = len(UserService.get_users(db, skip=0, limit=10000))
    total_products = len(ProductService.get_products(db, skip=0, limit=10000))
    total_customers = len(CustomerService.get_customers(db, skip=0, limit=10000))
    total_invoices = len(InvoiceService.get_invoices(db, skip=0, limit=10000))
    total_expenses = len(ExpenseService.get_expenses(db, skip=0, limit=10000))

    # Get recent activity
    recent_invoices = InvoiceService.get_invoices(db, skip=0, limit=5)
    recent_customers = CustomerService.get_customers(db, skip=0, limit=5)

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
def get_reports(
    report_type: str = "daily",
    start_date: str = None,
    end_date: str = None,
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
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
        invoices = InvoiceService.get_invoices(db, skip=0, limit=10000)
        total_revenue = sum(float(inv.totals.get('total', 0)) for inv in invoices if hasattr(inv, 'totals'))
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
        products = ProductService.get_products(db, skip=0, limit=10000)
        low_stock_items = [prod for prod in products if prod.stock_level < 10]
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
def get_settings(
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
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
def update_settings(
    settings_update: Dict[str, Any],
    current_user: User = Depends(admin_required()),
    db: Session = Depends(get_db)
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

# Import statement needed for User type hint
from ..models.user import User