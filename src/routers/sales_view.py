from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
import json

from src.database import get_db
from src.models.user import User
from src.models.invoice import Invoice
from src.models.customer_invoice import CustomerInvoice
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
    Get customized/customer invoices with payments received in the date range.
    
    CASH BASIS approach:
    - Shows invoices that received payments within the selected date range
    - Shows how much was paid on each selected date
    - Simple columns: Total, Today's Payment, Total Paid, Pending
    
    Example:
    - Invoice created on Feb 28
    - Payment 1: Feb 28 (Rs. 10,000) - Shows when Feb 28 selected
    - Payment 2: Mar 3 (Rs. 15,000) - Shows when Mar 3 selected
    """
    try:
        from_date_obj = datetime.fromisoformat(from_date).date()
        to_date_obj = datetime.fromisoformat(to_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    # Query ALL customer invoices (CIN- prefix)
    # We'll filter by payment date in Python, not SQL
    statement = select(CustomerInvoice).where(
        CustomerInvoice.invoice_no.like("CIN-%")
    )

    result = await db.execute(statement)
    all_invoices = result.scalars().all()

    invoice_list = []
    
    for inv in all_invoices:
        try:
            # Parse payment history
            payment_history = []
            if inv.payments_history:
                try:
                    payment_history = json.loads(inv.payments_history)
                except:
                    payment_history = []
            
            # Filter payments within selected date range
            payments_in_range = []
            for payment in payment_history:
                payment_date_str = payment.get('date', '')
                if payment_date_str:
                    try:
                        # Handle ISO format dates
                        if 'T' in payment_date_str:
                            payment_date = datetime.fromisoformat(payment_date_str).date()
                        else:
                            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
                        
                        # Check if payment date is within range
                        if from_date_obj <= payment_date <= to_date_obj:
                            payments_in_range.append({
                                "date": payment_date_str,
                                "amount": float(payment.get('amount', 0)),
                                "method": payment.get('payment_method', 'cash'),
                                "description": payment.get('description', '')
                            })
                    except:
                        continue
            
            # Skip invoices with no payments in the selected date range
            if not payments_in_range:
                continue
            
            # Calculate total payment received in the selected date range
            total_payment_in_range = sum(p['amount'] for p in payments_in_range)
            
            # Get the latest payment time for display
            latest_payment_time = ""
            if payments_in_range:
                latest_payment = payments_in_range[-1]  # Get last payment
                payment_date_str = latest_payment.get('date', '')
                if payment_date_str:
                    try:
                        if 'T' in payment_date_str:
                            payment_datetime = datetime.fromisoformat(payment_date_str)
                            latest_payment_time = payment_datetime.strftime('%I:%M:%S %p')  # Format: 07:16:14 AM
                        else:
                            latest_payment_time = "12:00:00 AM"
                    except:
                        latest_payment_time = "12:00:00 AM"
            
            # Get unique payment methods used in this date range
            methods_in_range = list(set(p['method'] for p in payments_in_range))
            
            # Parse items to get quantity
            items = []
            try:
                items = json.loads(inv.items) if inv.items else []
            except:
                items = []
            
            total_quantity = sum(item.get('quantity', 0) for item in items)
            
            # Calculate values
            total_amount = float(inv.total_amount) if inv.total_amount else 0.0
            total_paid = float(inv.amount_paid) if inv.amount_paid else 0.0
            pending = float(inv.balance_due) if inv.balance_due else 0.0
            
            invoice_list.append({
                "id": str(inv.id),
                "invoice_no": inv.invoice_no,
                "customer_name": inv.customer_name or "N/A",
                "team_name": inv.team_name or "",
                "total_amount": total_amount,
                "payment_in_selected_range": total_payment_in_range,  # Jo payment aaj/selected date mein hui
                "total_paid": total_paid,  # Cumulative total paid till now
                "pending": pending,  # Remaining balance
                "payment_status": inv.payment_status,  # paid/partial/unpaid
                "payment_methods_used": methods_in_range,  # Methods used in selected date
                "quantity": total_quantity,
                "invoice_created_at": inv.created_at.isoformat() if inv.created_at else None,
                "payment_time": latest_payment_time,  # Time of payment (e.g., "02:30 PM")
                "payments_in_range": payments_in_range  # Detailed payment list for reference
            })
            
        except Exception as e:
            print(f"Error processing invoice {inv.id}: {e}")
            continue

    return {"invoices": invoice_list, "total": len(invoice_list)}


@router.get("/customized-summary")
async def get_customized_sales_summary(
    from_date: str = Query(...),
    to_date: str = Query(...),
    branch: str = Query("European Sports Light House"),
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get summary of customer invoice payments received in the date range.
    
    CASH BASIS: Shows payments received on selected dates, not invoice creation dates.
    """
    try:
        from_date_obj = datetime.fromisoformat(from_date).date()
        to_date_obj = datetime.fromisoformat(to_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")

    # Query ALL customer invoices
    statement = select(CustomerInvoice).where(
        CustomerInvoice.invoice_no.like("CIN-%")
    )

    result = await db.execute(statement)
    all_invoices = result.scalars().all()

    # Initialize counters
    total_collection = 0.0
    cash_collection = 0.0
    easypaisa_zohaib_collection = 0.0
    easypaisa_yasir_collection = 0.0
    bank_collection = 0.0
    
    invoices_with_payments = 0

    for inv in all_invoices:
        try:
            # Parse payment history
            payment_history = []
            if inv.payments_history:
                try:
                    payment_history = json.loads(inv.payments_history)
                except:
                    payment_history = []
            
            # Filter payments within selected date range
            for payment in payment_history:
                payment_date_str = payment.get('date', '')
                if payment_date_str:
                    try:
                        # Handle ISO format dates
                        if 'T' in payment_date_str:
                            payment_date = datetime.fromisoformat(payment_date_str).date()
                        else:
                            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
                        
                        # Check if payment date is within range
                        if from_date_obj <= payment_date <= to_date_obj:
                            amount = float(payment.get('amount', 0))
                            method = payment.get('payment_method', 'cash').lower()
                            
                            total_collection += amount
                            invoices_with_payments += 1
                            
                            # Categorize by payment method
                            if method == 'cash':
                                cash_collection += amount
                            elif 'easypaisa' in method and 'zohaib' in method:
                                easypaisa_zohaib_collection += amount
                            elif 'easypaisa' in method and 'yasir' in method:
                                easypaisa_yasir_collection += amount
                            elif 'bank' in method or 'faysal' in method:
                                bank_collection += amount
                            else:
                                # Default to cash for unknown methods
                                cash_collection += amount
                                
                    except:
                        continue
                        
        except Exception as e:
            print(f"Error processing invoice {inv.id} for summary: {e}")
            continue

    return {
        "total_collection": total_collection,
        "cash": cash_collection,
        "easypaisa_zohaib": easypaisa_zohaib_collection,
        "easypaisa_yasir": easypaisa_yasir_collection,
        "bank": bank_collection,
        "invoices_count": invoices_with_payments
    }


@router.get("/summary")
async def get_sales_summary(
    from_date: str = Query(...),
    to_date: str = Query(...),
    branch: str = Query("European Sports Light House"),
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Get combined sales summary for the given date range.
    Includes both walk-in invoices and customer invoice payments.
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

    # Get total sales from daily_cash table (walk-in sales)
    walkin_total_sales = 0.0
    walkin_cash_sales = 0.0

    daily_cash_all = await db.execute(
        select(DailyCash).where(
            and_(
                DailyCash.date >= from_date_obj,
                DailyCash.date <= to_date_obj
            )
        )
    )
    for dc in daily_cash_all.scalars().all():
        walkin_total_sales += float(dc.total_sales)
        walkin_cash_sales += float(dc.cash_sales)

    # Get customer invoice payments in date range
    customer_statement = select(CustomerInvoice).where(
        CustomerInvoice.invoice_no.like("CIN-%")
    )
    customer_result = await db.execute(customer_statement)
    all_customer_invoices = customer_result.scalars().all()

    customer_total_collection = 0.0
    customer_cash_collection = 0.0

    for inv in all_customer_invoices:
        try:
            payment_history = []
            if inv.payments_history:
                try:
                    payment_history = json.loads(inv.payments_history)
                except:
                    payment_history = []
            
            for payment in payment_history:
                payment_date_str = payment.get('date', '')
                if payment_date_str:
                    try:
                        if 'T' in payment_date_str:
                            payment_date = datetime.fromisoformat(payment_date_str).date()
                        else:
                            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
                        
                        if from_date_obj <= payment_date <= to_date_obj:
                            amount = float(payment.get('amount', 0))
                            method = payment.get('payment_method', 'cash').lower()
                            
                            customer_total_collection += amount
                            
                            if method == 'cash':
                                customer_cash_collection += amount
                                
                    except:
                        continue
        except:
            continue

    # Calculate WALK-IN COST from invoice items (same as walk-in invoice display: 70% of selling price)
    walkin_total_cost = 0.0
    
    # Query walk-in invoices (SIN- prefix) for the date range
    walkin_statement = select(Invoice).where(
        and_(
            Invoice.invoice_no.like("SIN-%"),
            func.date(Invoice.created_at) >= from_date_obj,
            func.date(Invoice.created_at) <= to_date_obj
        )
    )
    walkin_result = await db.execute(walkin_statement)
    walkin_invoices = walkin_result.scalars().all()
    
    for inv in walkin_invoices:
        try:
            items = json.loads(inv.items) if inv.items else []
            for item in items:
                # Same calculation as walk-in invoice display (line 69)
                quantity = item.get('quantity', 0)
                unit_price = item.get('unit_price', 0)
                item_discount = float(item.get('discount', 0))
                item_total = quantity * unit_price - item_discount
                item_cost = item_total * 0.7  # 70% cost (same as display)
                walkin_total_cost += item_cost
        except:
            continue

    # Combined totals (walk-in + customer payments)
    total_sales = walkin_total_sales + customer_total_collection
    
    # Calculate gross profit using ACTUAL walk-in cost ONLY
    # Gross Profit = Total Sales - Total Cost (customer invoices have NO cost tracking)
    gross_profit = total_sales - walkin_total_cost
    
    # Total purchase/cost = ONLY walk-in cost (customer invoices don't have cost tracking)
    total_purchase = walkin_total_cost

    # Get total cash recovery
    total_cash_sales = walkin_cash_sales + customer_cash_collection

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

    # Calculate net profit = Gross Profit - Expenses
    net_profit = gross_profit - total_expenses

    return {
        "opening": opening,
        "totalSale": total_sales,
        "grossProfit": gross_profit,
        "totalExpense": total_expenses,
        "totalRecovery": total_cash_sales,
        "vendorPayments": 0.0,
        "netCash": net_cash,
        "totalPurchase": total_purchase,  # Now actual cost from walk-in invoices
        "totalRefund": 0.0,
        "netProfit": net_profit,
        # Breakdown for reference
        "walkin_sales": walkin_total_sales,
        "customer_payments": customer_total_collection,
        "walkin_cost": walkin_total_cost  # Actual cost for reference
    }


# ==================== REPORT ENDPOINTS ====================

@router.get("/walkin-invoices/pdf")
async def get_walkin_invoices_pdf(
    from_date: str = Query(...),
    to_date: str = Query(...),
    branch: str = Query("European Sports Light House"),
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate PDF report for walk-in invoices (date-wise)
    """
    import base64
    from datetime import datetime
    
    try:
        from_date_obj = datetime.fromisoformat(from_date).date()
        to_date_obj = datetime.fromisoformat(to_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Query walk-in invoices
    statement = select(Invoice).where(
        and_(
            Invoice.invoice_no.like("SIN-%"),
            func.date(Invoice.created_at) >= from_date_obj,
            func.date(Invoice.created_at) <= to_date_obj
        )
    )
    result = await db.execute(statement)
    invoices = result.scalars().all()
    
    # Build invoice rows for PDF
    invoice_rows = ""
    total_amount = 0.0
    total_cost = 0.0
    
    for inv in invoices:
        try:
            items = json.loads(inv.items) if inv.items else []
            totals = json.loads(inv.totals) if inv.totals else {}
            
            for item in items:
                product_name = item.get('product_name', item.get('pro_name', 'N/A'))
                quantity = item.get('quantity', 0)
                unit_price = item.get('unit_price', 0)
                item_discount = float(item.get('discount', 0))
                item_total = quantity * unit_price - item_discount
                item_cost = item_total * 0.7
                
                invoice_rows += f"""
                <tr>
                    <td class="border">{inv.invoice_no}</td>
                    <td class="border">{inv.created_at.strftime('%Y-%m-%d') if inv.created_at else ''}</td>
                    <td class="border">{product_name}</td>
                    <td class="border text-right">{quantity}</td>
                    <td class="border text-right">{unit_price:.0f}</td>
                    <td class="border text-right">{item_discount:.0f}</td>
                    <td class="border text-right">{item_total:.0f}</td>
                    <td class="border text-right">{item_cost:.0f}</td>
                    <td class="border">{inv.created_at.strftime('%I:%M %p') if inv.created_at else ''}</td>
                </tr>
                """
                total_amount += item_total
                total_cost += item_cost
        except:
            continue
    
    # Calculate totals
    gross_profit = total_amount - total_cost
    
    # Create HTML content for PDF
    current_date = datetime.now().strftime('%d-%m-%Y %I:%M %p')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4 landscape;
                margin: 15mm;
            }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 11px;
                margin: 0;
                padding: 0;
            }}
            h1 {{
                text-align: center;
                color: #333;
                margin: 0 0 10px 0;
                font-size: 24px;
                font-weight: bold;
            }}
            .date-range {{
                text-align: center;
                margin: 0 0 15px 0;
                color: #666;
                font-size: 12px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            .border {{
                border: 1px solid #000;
                padding: 6px;
            }}
            th {{
                background-color: #444;
                color: white;
                font-weight: bold;
                text-align: left;
                padding: 8px;
                font-size: 11px;
            }}
            .text-right {{
                text-align: right;
            }}
            .total-row {{
                background-color: #f0f0f0;
                font-weight: bold;
            }}
            .summary {{
                margin-top: 20px;
                border: 2px solid #333;
                padding: 10px;
            }}
            .summary-row {{
                display: flex;
                justify-content: space-between;
                margin-bottom: 5px;
            }}
            .summary-label {{
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h1>Walk-in Invoice Report</h1>
        <p class="date-range">From: {from_date} To: {to_date} | Generated: {current_date}</p>
        
        <table>
            <thead>
                <tr>
                    <th style="width: 12%;">Invoice No</th>
                    <th style="width: 12%;">Date</th>
                    <th style="width: 23%;">Product</th>
                    <th style="width: 7%;">Qty</th>
                    <th style="width: 9%;">Price</th>
                    <th style="width: 9%;">Discount</th>
                    <th style="width: 11%;">Total</th>
                    <th style="width: 11%;">Cost</th>
                    <th style="width: 10%;">Time</th>
                </tr>
            </thead>
            <tbody>
                {invoice_rows}
                <tr class="total-row">
                    <td class="border" colspan="3" style="text-align: left; font-weight: bold;">TOTAL</td>
                    <td class="border"></td>
                    <td class="border"></td>
                    <td class="border"></td>
                    <td class="border text-right" style="font-weight: bold;">{total_amount:.0f}</td>
                    <td class="border text-right" style="font-weight: bold;">{total_cost:.0f}</td>
                    <td class="border"></td>
                </tr>
            </tbody>
        </table>
        
        <div class="summary">
            <div class="summary-row">
                <span class="summary-label">Total Sales:</span>
                <span>Rs. {total_amount:.0f}</span>
            </div>
            <div class="summary-row">
                <span class="summary-label">Total Cost:</span>
                <span>Rs. {total_cost:.0f}</span>
            </div>
            <div class="summary-row">
                <span class="summary-label">Gross Profit:</span>
                <span>Rs. {gross_profit:.0f}</span>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Generate PDF using weasyprint
    try:
        from weasyprint import HTML
        pdf_doc = HTML(string=html_content)
        pdf_bytes = pdf_doc.write_pdf()
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
        print(f"PDF generated, length: {len(encoded_pdf)}")
    except Exception as e:
        print(f"weasyprint failed: {e}")
        # Fallback - return simple PDF
        pdf_content = f"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] >>\nendobj\nxref\n0 4\ntrailer\n<< /Size 4 /Root 1 0 R >>\n%%EOF"
        encoded_pdf = base64.b64encode(pdf_content.encode()).decode()
    
    return {"pdf": encoded_pdf}


@router.get("/walkin-invoices/excel")
async def get_walkin_invoices_excel(
    from_date: str = Query(...),
    to_date: str = Query(...),
    branch: str = Query("European Sports Light House"),
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate Excel report for walk-in invoices (date-wise)
    Returns actual .xlsx file
    """
    import io
    import base64
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    
    try:
        from_date_obj = datetime.fromisoformat(from_date).date()
        to_date_obj = datetime.fromisoformat(to_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Query walk-in invoices
    statement = select(Invoice).where(
        and_(
            Invoice.invoice_no.like("SIN-%"),
            func.date(Invoice.created_at) >= from_date_obj,
            func.date(Invoice.created_at) <= to_date_obj
        )
    )
    result = await db.execute(statement)
    invoices = result.scalars().all()
    
    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Walk-in Invoices"
    
    # Define styles
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="444444", end_color="444444", fill_type="solid")
    header_alignment = Alignment(horizontal="left", vertical="center")
    cell_alignment = Alignment(vertical="center")
    right_alignment = Alignment(horizontal="right", vertical="center")
    
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Write header
    headers = [
        'Invoice No',
        'Date',
        'Product Name',
        'Quantity',
        'Unit Price',
        'Discount',
        'Total Amount',
        'Cost',
        'Time'
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # Set column widths
    column_widths = [15, 12, 30, 10, 12, 12, 15, 12, 10]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[chr(64 + col)].width = width
    
    total_amount = 0.0
    total_cost = 0.0
    row_num = 2
    
    # Write data rows
    for inv in invoices:
        try:
            items = json.loads(inv.items) if inv.items else []
            
            for item in items:
                product_name = item.get('product_name', item.get('pro_name', 'N/A'))
                quantity = item.get('quantity', 0)
                unit_price = item.get('unit_price', 0)
                item_discount = float(item.get('discount', 0))
                item_total = quantity * unit_price - item_discount
                item_cost = item_total * 0.7
                
                # Write row data
                ws.cell(row=row_num, column=1, value=inv.invoice_no).border = thin_border
                ws.cell(row=row_num, column=2, value=inv.created_at.strftime('%Y-%m-%d') if inv.created_at else '').border = thin_border
                ws.cell(row=row_num, column=3, value=product_name).border = thin_border
                ws.cell(row=row_num, column=4, value=quantity).border = thin_border
                ws.cell(row=row_num, column=5, value=round(unit_price, 2)).border = thin_border
                ws.cell(row=row_num, column=6, value=round(item_discount, 2)).border = thin_border
                ws.cell(row=row_num, column=7, value=round(item_total, 2)).border = thin_border
                ws.cell(row=row_num, column=8, value=round(item_cost, 2)).border = thin_border
                ws.cell(row=row_num, column=9, value=inv.created_at.strftime('%I:%M %p') if inv.created_at else '').border = thin_border
                
                # Apply alignments
                for col in range(1, 10):
                    if col in [4]:  # Quantity
                        ws.cell(row=row_num, column=col).alignment = cell_alignment
                    elif col in [5, 6, 7, 8]:  # Numeric columns
                        ws.cell(row=row_num, column=col).alignment = right_alignment
                    else:
                        ws.cell(row=row_num, column=col).alignment = cell_alignment
                
                total_amount += item_total
                total_cost += item_cost
                row_num += 1
        except:
            continue
    
    # Write total row
    total_row = row_num
    ws.cell(row=total_row, column=1, value='TOTAL').font = Font(bold=True)
    ws.cell(row=total_row, column=7, value=round(total_amount, 2)).font = Font(bold=True)
    ws.cell(row=total_row, column=8, value=round(total_cost, 2)).font = Font(bold=True)
    
    # Merge cells for TOTAL label
    ws.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=6)
    
    # Apply border to total row
    for col in range(1, 10):
        ws.cell(row=total_row, column=col).border = thin_border
    
    # Add summary section
    summary_row = total_row + 2
    ws.cell(row=summary_row, column=1, value='Total Sales:').font = Font(bold=True)
    ws.cell(row=summary_row, column=2, value=round(total_amount, 2)).font = Font(bold=True)
    
    ws.cell(row=summary_row + 1, column=1, value='Total Cost:').font = Font(bold=True)
    ws.cell(row=summary_row + 1, column=2, value=round(total_cost, 2)).font = Font(bold=True)
    
    ws.cell(row=summary_row + 2, column=1, value='Gross Profit:').font = Font(bold=True)
    ws.cell(row=summary_row + 2, column=2, value=round(total_amount - total_cost, 2)).font = Font(bold=True)
    
    # Save to bytes
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    excel_bytes = excel_buffer.read()
    
    # Encode to base64
    encoded_excel = base64.b64encode(excel_bytes).decode()
    
    return {
        "excel": encoded_excel,
        "filename": f"walkin_invoices_{from_date}_to_{to_date}.xlsx"
    }


@router.get("/customized-invoices/pdf")
async def get_customized_invoices_pdf(
    from_date: str = Query(...),
    to_date: str = Query(...),
    branch: str = Query("European Sports Light House"),
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate PDF report for customer invoices (date-wise payments)
    """
    import base64
    from datetime import datetime
    
    try:
        from_date_obj = datetime.fromisoformat(from_date).date()
        to_date_obj = datetime.fromisoformat(to_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Query customer invoices
    statement = select(CustomerInvoice).where(
        CustomerInvoice.invoice_no.like("CIN-%")
    )
    result = await db.execute(statement)
    all_invoices = result.scalars().all()
    
    # Build invoice rows for PDF
    invoice_rows = ""
    total_collection = 0.0
    invoice_count = 0
    
    for inv in all_invoices:
        try:
            # Parse payment history
            payment_history = []
            if inv.payments_history:
                try:
                    payment_history = json.loads(inv.payments_history)
                except:
                    payment_history = []
            
            # Filter payments within selected date range
            for payment in payment_history:
                payment_date_str = payment.get('date', '')
                if payment_date_str:
                    try:
                        if 'T' in payment_date_str:
                            payment_date = datetime.fromisoformat(payment_date_str).date()
                        else:
                            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
                        
                        if from_date_obj <= payment_date <= to_date_obj:
                            amount = float(payment.get('amount', 0))
                            method = payment.get('payment_method', 'cash')
                            
                            invoice_rows += f"""
                            <tr>
                                <td class="border">{inv.invoice_no}</td>
                                <td class="border">{payment_date.strftime('%Y-%m-%d')}</td>
                                <td class="border">{inv.customer_name or 'N/A'}</td>
                                <td class="border text-right">{amount:.0f}</td>
                                <td class="border">{method}</td>
                                <td class="border">{payment_date.strftime('%I:%M %p') if 'T' in payment_date_str else '12:00 AM'}</td>
                            </tr>
                            """
                            total_collection += amount
                            invoice_count += 1
                    except:
                        continue
        except:
            continue
    
    # Create HTML content for PDF
    current_date = datetime.now().strftime('%d-%m-%Y %I:%M %p')
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @page {{
                size: A4 landscape;
                margin: 15mm;
            }}
            body {{
                font-family: Arial, sans-serif;
                font-size: 11px;
                margin: 0;
                padding: 0;
            }}
            h1 {{
                text-align: center;
                color: #333;
                margin: 0 0 10px 0;
                font-size: 24px;
                font-weight: bold;
            }}
            .date-range {{
                text-align: center;
                margin: 0 0 15px 0;
                color: #666;
                font-size: 12px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            .border {{
                border: 1px solid #000;
                padding: 6px;
            }}
            th {{
                background-color: #444;
                color: white;
                font-weight: bold;
                text-align: left;
                padding: 8px;
                font-size: 11px;
            }}
            .text-right {{
                text-align: right;
            }}
            .total-row {{
                background-color: #f0f0f0;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <h1>Customer Invoice Payment Report</h1>
        <p class="date-range">From: {from_date} To: {to_date} | Generated: {current_date}</p>
        
        <table>
            <thead>
                <tr>
                    <th style="width: 13%;">Invoice No</th>
                    <th style="width: 15%;">Payment Date</th>
                    <th style="width: 22%;">Customer Name</th>
                    <th style="width: 15%;">Payment Amount</th>
                    <th style="width: 15%;">Payment Method</th>
                    <th style="width: 15%;">Time</th>
                </tr>
            </thead>
            <tbody>
                {invoice_rows}
                <tr class="total-row">
                    <td class="border" colspan="3" style="text-align: left; font-weight: bold;">TOTAL ({invoice_count} payments)</td>
                    <td class="border text-right" style="font-weight: bold;">{total_collection:.0f}</td>
                    <td class="border" colspan="2"></td>
                </tr>
            </tbody>
        </table>
        
        <div style="margin-top: 20px; border: 2px solid #333; padding: 10px;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
                <span style="font-weight: bold;">Total Collection:</span>
                <span>Rs. {total_collection:.0f}</span>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Generate PDF using weasyprint
    try:
        from weasyprint import HTML
        pdf_doc = HTML(string=html_content)
        pdf_bytes = pdf_doc.write_pdf()
        encoded_pdf = base64.b64encode(pdf_bytes).decode()
        print(f"PDF generated, length: {len(encoded_pdf)}")
    except Exception as e:
        print(f"weasyprint failed: {e}")
        pdf_content = f"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] >>\nendobj\nxref\n0 4\ntrailer\n<< /Size 4 /Root 1 0 R >>\n%%EOF"
        encoded_pdf = base64.b64encode(pdf_content.encode()).decode()
    
    return {"pdf": encoded_pdf}


@router.get("/customized-invoices/excel")
async def get_customized_invoices_excel(
    from_date: str = Query(...),
    to_date: str = Query(...),
    branch: str = Query("European Sports Light House"),
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate Excel report for customer invoices (date-wise payments)
    Returns actual .xlsx file
    """
    import io
    import base64
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    
    try:
        from_date_obj = datetime.fromisoformat(from_date).date()
        to_date_obj = datetime.fromisoformat(to_date).date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    # Query customer invoices
    statement = select(CustomerInvoice).where(
        CustomerInvoice.invoice_no.like("CIN-%")
    )
    result = await db.execute(statement)
    all_invoices = result.scalars().all()
    
    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Customer Invoice Payments"
    
    # Define styles
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="444444", end_color="444444", fill_type="solid")
    header_alignment = Alignment(horizontal="left", vertical="center")
    cell_alignment = Alignment(vertical="center")
    right_alignment = Alignment(horizontal="right", vertical="center")
    
    thin_border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Write header
    headers = [
        'Invoice No',
        'Payment Date',
        'Customer Name',
        'Payment Amount',
        'Payment Method',
        'Time'
    ]
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # Set column widths
    column_widths = [15, 15, 30, 15, 18, 12]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[chr(64 + col)].width = width
    
    total_collection = 0.0
    invoice_count = 0
    row_num = 2
    
    # Write data rows
    for inv in all_invoices:
        try:
            payment_history = []
            if inv.payments_history:
                try:
                    payment_history = json.loads(inv.payments_history)
                except:
                    payment_history = []
            
            for payment in payment_history:
                payment_date_str = payment.get('date', '')
                if payment_date_str:
                    try:
                        if 'T' in payment_date_str:
                            payment_date = datetime.fromisoformat(payment_date_str).date()
                        else:
                            payment_date = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
                        
                        if from_date_obj <= payment_date <= to_date_obj:
                            amount = float(payment.get('amount', 0))
                            method = payment.get('payment_method', 'cash')
                            
                            # Write row data
                            ws.cell(row=row_num, column=1, value=inv.invoice_no).border = thin_border
                            ws.cell(row=row_num, column=2, value=payment_date.strftime('%Y-%m-%d')).border = thin_border
                            ws.cell(row=row_num, column=3, value=inv.customer_name or 'N/A').border = thin_border
                            ws.cell(row=row_num, column=4, value=round(amount, 2)).border = thin_border
                            ws.cell(row=row_num, column=5, value=method).border = thin_border
                            ws.cell(row=row_num, column=6, value=payment_date.strftime('%I:%M %p') if 'T' in payment_date_str else '12:00 AM').border = thin_border
                            
                            # Apply alignments
                            for col in range(1, 7):
                                if col in [4]:  # Amount column
                                    ws.cell(row=row_num, column=col).alignment = right_alignment
                                else:
                                    ws.cell(row=row_num, column=col).alignment = cell_alignment
                            
                            total_collection += amount
                            invoice_count += 1
                            row_num += 1
                    except:
                        continue
        except:
            continue
    
    # Write total row
    total_row = row_num
    ws.cell(row=total_row, column=1, value=f'TOTAL ({invoice_count} payments)').font = Font(bold=True)
    ws.cell(row=total_row, column=4, value=round(total_collection, 2)).font = Font(bold=True)
    
    # Apply border to all cells in total row
    for col in range(1, 7):
        cell = ws.cell(row=total_row, column=col)
        cell.border = thin_border
        if col != 4:  # Set empty cells for columns without data
            if col > 4:
                cell.value = ''
    
    # Merge cells for TOTAL label (columns 1-3)
    ws.merge_cells(start_row=total_row, start_column=1, end_row=total_row, end_column=3)
    # Merge empty cells (columns 5-6)
    ws.merge_cells(start_row=total_row, start_column=5, end_row=total_row, end_column=6)
    
    # Add summary section
    summary_row = total_row + 2
    ws.cell(row=summary_row, column=1, value='Total Collection:').font = Font(bold=True)
    ws.cell(row=summary_row, column=2, value=round(total_collection, 2)).font = Font(bold=True)
    
    # Save to bytes
    excel_buffer = io.BytesIO()
    wb.save(excel_buffer)
    excel_buffer.seek(0)
    excel_bytes = excel_buffer.read()
    
    # Encode to base64
    encoded_excel = base64.b64encode(excel_bytes).decode()
    
    return {
        "excel": encoded_excel,
        "filename": f"customer_invoices_{from_date}_to_{to_date}.xlsx"
    }
