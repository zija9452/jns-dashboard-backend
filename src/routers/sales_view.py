from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
import json

from src.database import get_db
from src.models.user import User
from src.models.invoice import Invoice
from src.models.daily_cash import DailyCash
from src.models.expense import Expense
from src.auth.session_auth import admin_cashier_employee_required_from_session

router = APIRouter()


@router.get("/walkin-invoices")
async def get_walkin_invoices(
    from_date: str = Query(...),
    to_date: str = Query(...),
    branch: str = Query("European Sports Light House"),
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get walk-in invoices for the given date range
    """
    try:
        from_date_obj = datetime.fromisoformat(from_date).date()
        to_date_obj = datetime.fromisoformat(to_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    # Query walk-in invoices (SIN- prefix)
    statement = select(Invoice).where(
        and_(
            Invoice.invoice_no.like("SIN-%"),
            func.date(Invoice.created_at) >= from_date_obj,
            func.date(Invoice.created_at) <= to_date_obj
        )
    )
    
    result = await db.execute(statement)
    invoices = result.scalars().all()

    invoice_list = []
    for inv in invoices:
        try:
            totals = json.loads(inv.totals) if inv.totals else {}
            items = json.loads(inv.items) if inv.items else []
            
            total_invoice_amount = float(totals.get('total', 0))
            total_invoice_paid = float(totals.get('amount_paid', 0))
            total_invoice_discount = float(totals.get('discount', 0))
            
            # Track if this is the first item in the invoice
            first_item = True
            
            # Create separate row for each item in the invoice
            for item in items:
                product_name = item.get('product_name', item.get('pro_name', 'N/A'))
                quantity = item.get('quantity', 0)
                unit_price = item.get('unit_price', 0)
                item_discount = float(item.get('discount', 0))
                item_total = quantity * unit_price - item_discount
                item_cost = item_total * 0.7  # Assume 70% cost
                
                # Show payment and discount only on first item
                amount_paid = total_invoice_paid if first_item else 0.0
                discount = total_invoice_discount if first_item else 0.0
                
                invoice_list.append({
                    "id": str(inv.id),
                    "invoice_no": inv.invoice_no,
                    "product_name": product_name,
                    "total_amount": float(item_total),
                    "amount_paid": amount_paid,
                    "balance_due": 0.0 if first_item else 0.0,
                    "payment_status": inv.payment_status,
                    "payment_method": inv.payment_method or "cash",
                    "quantity": quantity,
                    "discount": discount,
                    "total_discount": discount,
                    "cost": float(item_cost),
                    "created_at": inv.created_at.isoformat() if inv.created_at else None
                })
                
                first_item = False
        except Exception as e:
            print(f"Error processing invoice {inv.id}: {e}")
            continue

    return {"invoices": invoice_list, "total": len(invoice_list)}


@router.get("/customized-invoices")
async def get_customized_invoices(
    from_date: str = Query(...),
    to_date: str = Query(...),
    branch: str = Query("European Sports Light House"),
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get customized/customer invoices for the given date range
    """
    try:
        from_date_obj = datetime.fromisoformat(from_date).date()
        to_date_obj = datetime.fromisoformat(to_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    # Query customer invoices (CIV- prefix)
    statement = select(Invoice).where(
        and_(
            Invoice.invoice_no.like("CIV-%"),
            func.date(Invoice.created_at) >= from_date_obj,
            func.date(Invoice.created_at) <= to_date_obj
        )
    )
    
    result = await db.execute(statement)
    invoices = result.scalars().all()

    invoice_list = []
    for inv in invoices:
        try:
            totals = json.loads(inv.totals) if inv.totals else {}
            items = json.loads(inv.items) if inv.items else []
            
            # Calculate quantity from items
            total_quantity = sum(item.get('quantity', 0) for item in items)
            
            # Get payment history for partial payments
            payment_history = []
            if inv.payments_history:
                try:
                    history = json.loads(inv.payments_history)
                    payment_history = [
                        {
                            "date": p.get('date', ''),
                            "amount": p.get('amount', 0),
                            "method": p.get('payment_method', 'cash')
                        }
                        for p in history
                    ]
                except:
                    pass
            
            invoice_list.append({
                "id": str(inv.id),
                "invoice_no": inv.invoice_no,
                "customer_name": inv.customer_name,
                "total_amount": float(totals.get('total', 0)),
                "amount_paid": float(totals.get('amount_paid', 0)),
                "balance_due": float(totals.get('balance_due', 0)),
                "payment_status": inv.payment_status,
                "payment_method": inv.payment_method or "cash",
                "quantity": total_quantity,
                "discount": float(totals.get('discount', 0)),
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
                "partial_payments": payment_history
            })
        except Exception as e:
            print(f"Error processing invoice {inv.id}: {e}")
            continue

    return {"invoices": invoice_list, "total": len(invoice_list)}


@router.get("/summary")
async def get_sales_summary(
    from_date: str = Query(...),
    to_date: str = Query(...),
    branch: str = Query("European Sports Light House"),
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get sales summary for the given date range
    """
    try:
        from_date_obj = datetime.fromisoformat(from_date).date()
        to_date_obj = datetime.fromisoformat(to_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    # Get opening balance (from first date in range)
    daily_cash_result = await db.execute(
        select(DailyCash).where(DailyCash.date == from_date_obj)
    )
    daily_cash = daily_cash_result.scalar_one_or_none()
    opening = float(daily_cash.total_opening) if daily_cash else 0.0

    # Get total sales from daily_cash table
    total_sales = 0.0
    total_cash_sales = 0.0
    
    daily_cash_all = await db.execute(
        select(DailyCash).where(
            and_(
                DailyCash.date >= from_date_obj,
                DailyCash.date <= to_date_obj
            )
        )
    )
    for dc in daily_cash_all.scalars().all():
        total_sales += float(dc.total_sales)
        total_cash_sales += float(dc.cash_sales)

    # Calculate gross profit (assume 30% margin)
    gross_profit = total_sales * 0.3

    # Get total expenses
    expenses_result = await db.execute(
        select(func.sum(Expense.amount)).where(
            and_(
                Expense.expense_date >= from_date_obj,
                Expense.expense_date <= to_date_obj
            )
        )
    )
    total_expenses = float(expenses_result.scalar_one_or_none() or 0)

    # Calculate net cash
    net_cash = opening + total_cash_sales - total_expenses

    # Calculate net profit
    net_profit = gross_profit - total_expenses

    return {
        "opening": opening,
        "totalSale": total_sales,
        "grossProfit": gross_profit,
        "totalExpense": total_expenses,
        "totalRecovery": total_cash_sales,
        "vendorPayments": 0.0,
        "netCash": net_cash,
        "totalPurchase": total_sales * 0.7,  # Assume 70% purchase cost
        "totalRefund": 0.0,
        "netProfit": net_profit
    }
