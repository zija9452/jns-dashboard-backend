from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Optional, Any
import uuid
import json
import base64
import io
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import select, func, or_, and_
import logging
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from weasyprint import HTML

from ..database.database import get_db
from ..models.warehouse_invoice import WarehouseInvoice
from ..models.product import Product
from ..models.vendor import Vendor
from ..models.warehouse_customer import WarehouseCustomer
from ..models.salesman import Salesman
from ..models.user import User
from ..models.stock_entry import StockEntry, StockEntryType
from ..models.batch import Batch, BatchVendor, ProductBatch
from ..models.warehouse_vendor import WarehouseVendor
from ..auth.session_auth import admin_cashier_employee_required_from_session, admin_employee_required_from_session
from ..config.branches import DEFAULT_BRANCH
from ..database.database import session_factories
from ..services.branch_transfer import transfer_invoice_stock
from ..services.batch_service import product_batch_label

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/warehouse-invoice", tags=["warehouse-invoice"])


def is_direct_customer(customer: Optional[WarehouseCustomer]) -> bool:
    """A warehouse customer with no destination branch buys straight from the warehouse
    (Light House / Karim Abad customers have their branch code)."""
    return bool(customer) and not customer.destination_branch

@router.post("/create")
async def create_warehouse_invoice(
    request_data: dict,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new warehouse invoice and save to warehouse_invoices table.
    Decreases warehouse_stock and, for a branch customer, increases that branch's shop
    stock. A direct customer (no destination branch) buys straight from the warehouse:
    the stock goes to no shop.
    """
    # Extract data from request body
    order_items = request_data.get('items', [])
    customer_id = request_data.get('customer_id')
    payment_method = request_data.get('payment_method', 'cash')
    payment_date_str = request_data.get('payment_date', datetime.now().isoformat())
    
    selected_date = datetime.fromisoformat(payment_date_str).date()
    current_time = datetime.now().time()
    payment_date = datetime.combine(selected_date, current_time)

    manual_discount = float(request_data.get('manual_discount', 0))
    # Get amount_paid from request, if not provided it will be calculated later
    requested_amount_paid = request_data.get('amount_paid')
    notes = request_data.get('notes', '')

    if not order_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order items are required"
        )

    # Validate warehouse customer
    customer_name = "European Sports"
    customer_id_uuid = None
    customer_obj = None
    if customer_id:
        try:
            customer_id_uuid = uuid.UUID(str(customer_id))
            customer_result = await db.execute(select(WarehouseCustomer).where(WarehouseCustomer.id == customer_id_uuid))
            customer_obj = customer_result.scalar_one_or_none()
            if customer_obj:
                customer_name = customer_obj.name
            else:
                logger.error(f"Warehouse customer with ID {customer_id} not found")
        except ValueError:
            logger.error(f"Invalid UUID format for customer_id: {customer_id}")

    # Customer mapped to another branch (e.g. Karim Abad): stock goes to that
    # branch's database instead of the Light House shop (MULTI_BRANCH_PLAN Phase 7).
    # A customer with no branch is a direct customer: a sale, no shop gets the stock.
    # (No customer chosen keeps the old way: the Light House shop.)
    is_direct = is_direct_customer(customer_obj)
    destination_branch = customer_obj.destination_branch if customer_obj else None
    if destination_branch == DEFAULT_BRANCH:
        destination_branch = None
    if destination_branch and destination_branch not in session_factories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Branch '{destination_branch}' is not configured; cannot transfer stock"
        )

    # Fetch default vendor "J&S Sports"
    vendor_result = await db.execute(select(Vendor).where(Vendor.name == "J&S Sports"))
    js_vendor = vendor_result.scalar_one_or_none()
    js_vendor_id = js_vendor.id if js_vendor else None

    # Process each order item and update inventory (Transfer logic)
    items_list = []
    total_amount = Decimal('0')
    total_discount = 0.0

    try:
        for item in order_items:
            pro_name = item.get('pro_name')
            quantity = int(item.get('pro_quantity', 0))
            unit_price = float(item.get('unit_price', 0))
            shop_price = float(item.get('shop_price') or 0)
            discount = float(item.get('discount', 0))

            # Branch: Rate = the shop's cost; with the shop selling price it is set on the
            # destination branch's product, so both must be filled.
            # Direct customer: Rate = the price it is sold at; no shop price.
            if is_direct:
                shop_price = 0.0
                if unit_price <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Set the Rate for '{pro_name}'"
                    )
            elif unit_price <= 0 or shop_price <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Set Rate (shop cost) and Shop Selling Price for '{pro_name}'"
                )

            # The line picked: a batch (its own barcode / stock) or the product's stock
            # outside batches ("Old Stock"). Older clients send only the name.
            product_batch = None
            if item.get('product_batch_id'):
                product_batch = await db.get(ProductBatch, uuid.UUID(str(item['product_batch_id'])))
                if not product_batch:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch of '{pro_name}' not found")
                product = await db.get(Product, product_batch.product_id)
            elif item.get('product_id'):
                product = await db.get(Product, uuid.UUID(str(item['product_id'])))
            else:
                product_result = await db.execute(select(Product).where(Product.name == pro_name))
                product = product_result.scalar_one_or_none()
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product '{pro_name}' not found"
                )

            # Check warehouse stock of the picked line
            if product_batch:
                available = product_batch.warehouse_stock or 0
                line_name = f"{pro_name} ({product_batch.barcode})"
            else:
                in_batches = (await db.execute(
                    select(func.coalesce(func.sum(ProductBatch.warehouse_stock), 0))
                    .where(ProductBatch.product_id == product.id, ProductBatch.batch_id.isnot(None))
                )).scalar() or 0
                available = (product.warehouse_stock or 0) - in_batches
                line_name = pro_name
            if available < quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient warehouse stock for '{line_name}'. Available: {available}"
                )

            # Branch transfer matches the product by barcode in the other DB
            if destination_branch and not product.barcode:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product '{pro_name}' has no barcode; add a barcode before transferring to another branch"
                )

            # TRANSFER LOGIC: Warehouse -> Shop (a direct sale only leaves the warehouse)
            product.warehouse_stock = (product.warehouse_stock or 0) - quantity
            if not destination_branch and not is_direct:
                product.stock_level = (product.stock_level or 0) + quantity
                if product_batch:
                    # The batch keeps its own shop cost / price; the product's stay for
                    # its old stock
                    product_batch.stock_level = (product_batch.stock_level or 0) + quantity
                    product_batch.shop_cost = Decimal(str(unit_price))
                    product_batch.shop_price = Decimal(str(shop_price))
                else:
                    product.cost_price = Decimal(str(unit_price))
                    product.unit_price = Decimal(str(shop_price))
                product.updated_at = datetime.now()
            db.add(product)
            if product_batch:
                product_batch.warehouse_stock = (product_batch.warehouse_stock or 0) - quantity
                product_batch.updated_at = datetime.now()
                db.add(product_batch)
            # The cost as entered at Stock In (freight / cartage only go into the selling price)
            warehouse_cost = product_batch.cost if product_batch else product.warehouse_cost

            # Stock Entries (on the invoice date, with cost so stock reports total them)
            transfer_ref = f"W_INV_{'SALE' if is_direct else 'TRANSFER'}_{payment_date.strftime('%Y%m%d')}"
            stock_out = StockEntry(
                product_id=product.id,
                qty=-quantity,
                cost_price=warehouse_cost,
                type=StockEntryType.OUT,
                location="warehouse",
                ref=transfer_ref,
                product_batch_id=product_batch.id if product_batch else None,
                created_at=payment_date
            )
            db.add(stock_out)

            # Other branch gets its Stock In entry in its own DB (branch_transfer); a
            # direct sale has no shop Stock In
            if not destination_branch and not is_direct:
                stock_in = StockEntry(
                    product_id=product.id,
                    qty=quantity,
                    cost_price=Decimal(str(unit_price)),
                    unit_price=Decimal(str(shop_price)),
                    type=StockEntryType.IN,
                    location="Stock In",
                    vendor_id=js_vendor_id,
                    ref=transfer_ref,
                    product_batch_id=product_batch.id if product_batch else None,
                    created_at=payment_date
                )
                db.add(stock_in)

            item_total_before_discount = quantity * unit_price
            item_obj = {
                "product_name": str(pro_name),
                "product_id": str(product.id),
                "quantity": quantity,
                "unit_price": unit_price,
                "shop_price": shop_price or None,  # none for a direct sale
                "total_price": item_total_before_discount,
                "discount": discount,
                "cat_name": str(item.get('cat_name', '')),
                "cost_price": float(warehouse_cost) if warehouse_cost else 0.0,
            }
            if product_batch:
                # The other branch makes its copy of the batch line from these
                item_obj.update({
                    "product_batch_id": str(product_batch.id),
                    "batch_barcode": product_batch.barcode,
                    "batch_label": await product_batch_label(db, product_batch),
                })
            items_list.append(item_obj)
            total_amount += Decimal(str(item_total_before_discount))
            total_discount += discount

        total_discount += manual_discount
        net_total = total_amount - Decimal(str(total_discount))
        
        # Use requested amount paid or default to net_total
        if requested_amount_paid is not None:
            amount_paid = Decimal(str(requested_amount_paid))
        else:
            amount_paid = net_total
            
        balance_due = net_total - amount_paid
        
        # Update customer balance if there is a balance due
        if customer_obj and balance_due != 0:
            customer_obj.cus_balance = (customer_obj.cus_balance or Decimal('0')) + balance_due
            db.add(customer_obj)

        # Determine payment status
        payment_status = "paid"
        if balance_due > 0:
            payment_status = "partial" if amount_paid > 0 else "unpaid"
        elif balance_due < 0:
            payment_status = "overpaid"

        # Generate unique invoice number (WIN prefix)
        await db.execute(select(func.pg_advisory_lock(123461)))
        try:
            prefix_pattern = "WIN-%"
            statement = select(WarehouseInvoice.invoice_no).where(
                WarehouseInvoice.invoice_no.like(prefix_pattern)
            ).order_by(
                # Numeric max: longer number first, so e.g. WIN-10000 beats WIN-9999
                func.length(WarehouseInvoice.invoice_no).desc(), WarehouseInvoice.invoice_no.desc()
            ).limit(1)
            result = await db.execute(statement)
            max_invoice_no = result.scalar_one_or_none()

            if max_invoice_no:
                try:
                    parts = max_invoice_no.split("-")
                    next_seq = int(parts[-1]) + 1
                    seq_number = f"{next_seq:04d}"
                except:
                    seq_number = "0001"
            else:
                seq_number = "0001"
            
            invoice_no = f"WIN-{seq_number}"

            # Create WarehouseInvoice
            invoice_obj = WarehouseInvoice(
                id=uuid.uuid4(),
                invoice_no=invoice_no,
                customer_id=customer_id_uuid,
                customer_name=customer_name,
                items=json.dumps(items_list),
                totals=json.dumps({
                    "subtotal": float(total_amount),
                    "tax": 0.0,
                    "discount": float(total_discount),
                    "total": float(net_total),
                    "amount_paid": float(amount_paid),
                    "balance_due": float(balance_due),
                    "payment_status": payment_status
                }),
                total_amount=net_total,
                amount_paid=amount_paid,
                payment_status=payment_status,
                payments_history=json.dumps([{
                    "amount": float(amount_paid),
                    "payment_method": payment_method,
                    "date": payment_date.isoformat(),
                    "description": "Warehouse Direct Sale Payment" if is_direct else "Warehouse Transfer Payment"
                }]),
                discounts=Decimal(str(total_discount)),
                payment_method=payment_method,
                payment_date=payment_date,
                notes=notes,
                transfer_status="pending" if destination_branch else None,
                created_by=current_user.id
            )
            
            db.add(invoice_obj)
            await db.commit()
            await db.refresh(invoice_obj)

            # Invoice is committed; now add the stock in the other branch's DB.
            # A failure leaves the invoice "pending" for Retry, never undone.
            transfer_status, transfer_error = invoice_obj.transfer_status, None
            if destination_branch:
                try:
                    transfer_status, transfer_error = await transfer_invoice_stock(db, invoice_obj.id, destination_branch)
                except Exception as e:
                    logger.exception(f"Transfer of {invoice_no} to {destination_branch} failed")
                    await db.rollback()
                    transfer_status, transfer_error = "pending", str(e)

            # Generate PDF receipt
            from .walkin_invoice import generate_walkin_receipt_pdf
            pdf_data = generate_walkin_receipt_pdf(
                invoice_no=invoice_no,
                customer_name=customer_name,
                team_name="",
                items=items_list,
                total_amount=float(total_amount),
                total_discount=float(total_discount),
                amount_paid=float(amount_paid),
                balance_due=float(balance_due),
                payment_method=payment_method,
                payment_status=payment_status,
                created_at=payment_date,
                bill_type="WAREHOUSE RECEIPT"
            )
            
            return {
                "pdf": pdf_data,
                "invoice_no": invoice_no,
                "invoice_id": str(invoice_obj.id),
                "transfer_status": transfer_status,
                "transfer_error": transfer_error,
            }
        finally:
            await db.execute(select(func.pg_advisory_unlock(123461)))
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        logger.error(f"Error creating warehouse invoice: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error creating warehouse invoice: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )

@router.get("/products")
async def get_warehouse_products(
    customer_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get products that belong to warehouse and have stock, with the shop cost
    ("price") and shop selling price of the branch `customer_id` stocks
    (Light House if the customer has no other destination branch).
    """
    statement = select(Product).where(
        Product.is_warehouse_product == True,
        Product.warehouse_stock > 0
    )
    result = await db.execute(statement)
    products = result.scalars().all()

    # Light House: the warehouse row is also the shop product
    shop_prices = {p.barcode: (p.cost_price, p.unit_price) for p in products}
    destination_branch = None
    customer = None
    if customer_id:
        try:
            customer = await db.get(WarehouseCustomer, uuid.UUID(customer_id))
        except ValueError:
            customer = None
        destination_branch = customer.destination_branch if customer else None
    # Direct customer: sold at the selling price (Rate), no shop price
    direct = is_direct_customer(customer)
    if direct:
        shop_prices = {p.barcode: (p.unit_price, p.unit_price) for p in products}
    if destination_branch and destination_branch != DEFAULT_BRANCH and destination_branch in session_factories:
        barcodes = [p.barcode for p in products if p.barcode]
        async with session_factories[destination_branch]() as branch_db:
            rows = await branch_db.execute(
                select(Product.barcode, Product.cost_price, Product.unit_price).where(Product.barcode.in_(barcodes))
            )
            shop_prices = {r.barcode: (r.cost_price, r.unit_price) for r in rows}

    def as_float(value):
        return float(value) if value else 0.0

    # Batch lines with warehouse stock, oldest batch first
    batch_lines: Dict[uuid.UUID, list] = {}
    if products:
        rows = await db.execute(
            select(ProductBatch, Batch.batch_no, WarehouseVendor.name)
            .join(Batch, ProductBatch.batch_id == Batch.id)
            .outerjoin(BatchVendor, ProductBatch.batch_vendor_id == BatchVendor.id)
            .outerjoin(WarehouseVendor, BatchVendor.warehouse_vendor_id == WarehouseVendor.id)
            .where(ProductBatch.product_id.in_([p.id for p in products]), ProductBatch.warehouse_stock > 0)
            .order_by(Batch.batch_no, ProductBatch.created_at)
        )
        for pb, batch_no, vendor_name in rows.all():
            # Only the batch no under the name; two vendors' lines differ by barcode
            label = f"Batch {batch_no:03d}"
            batch_lines.setdefault(pb.product_id, []).append((pb, label))

    # One line for the product's stock outside batches ("Old Stock") and one per batch,
    # each with its own barcode and stock, so the invoice moves exactly that stock
    lines = []
    for p in products:
        batches = batch_lines.get(p.id, [])
        old_stock = (p.warehouse_stock or 0) - sum(pb.warehouse_stock for pb, _ in batches)
        if old_stock > 0:
            lines.append({
                "id": str(p.id),
                "product_id": str(p.id),
                "product_batch_id": None,
                "batch_label": "Old Stock" if batches else None,
                "product_name": p.name,
                "category": p.category,
                "price": as_float(shop_prices.get(p.barcode, (0, 0))[0]),
                "shop_price": as_float(shop_prices.get(p.barcode, (0, 0))[1]),
                "stock": old_stock,
                "barcode": p.barcode
            })
        for pb, label in batches:
            lines.append({
                "id": str(pb.id),
                "product_id": str(p.id),
                "product_batch_id": str(pb.id),
                "batch_label": label,
                "product_name": p.name,
                "category": p.category,
                # Direct: the batch's selling price. Branch: last invoice rate / price of
                # this batch, else its cost / selling price
                "price": as_float(pb.shop_price or pb.selling_price) if direct else as_float(pb.shop_cost or pb.cost),
                "shop_price": as_float(pb.shop_price or pb.selling_price),
                "stock": pb.warehouse_stock,
                "barcode": pb.barcode
            })
    return lines

@router.get("/all-invoices")
async def get_all_warehouse_invoices(
    payment_status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all warehouse invoices with optional payment status filter
    """
    statement = select(WarehouseInvoice)
    
    if payment_status:
        statuses = payment_status.split(',')
        statement = statement.where(WarehouseInvoice.payment_status.in_(statuses))
    
    statement = statement.order_by(WarehouseInvoice.created_at.asc())
    
    result = await db.execute(statement)
    invoices = result.scalars().all()
    
    result_list = []
    for inv in invoices:
        try:
            totals = json.loads(inv.totals)
            balance_due = totals.get('balance_due', 0.0)
        except:
            balance_due = float(inv.total_amount - inv.amount_paid)

        result_list.append({
            "orderid": str(inv.id),
            "invoice_no": inv.invoice_no,
            "status": "completed",
            "customer": inv.customer_name,
            "teamname": "",
            "quantity": 0,
            "total_amount": float(inv.total_amount),
            "amount_paid": float(inv.amount_paid),
            "balance_due": float(balance_due),
            "payment_status": inv.payment_status,
            "transfer_status": inv.transfer_status,
            "transfer_error": inv.transfer_error,
            "date": inv.payment_date.strftime('%Y-%m-%d') if inv.payment_date else inv.created_at.strftime('%Y-%m-%d'),
            "created_at": inv.created_at.isoformat()
        })
    
    return result_list

@router.get("/customer-invoices/{customer_id}")
async def get_customer_invoices(
    customer_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all invoices for a specific warehouse customer that have balance due
    """
    try:
        customer_uuid = uuid.UUID(customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid customer ID format")

    statement = select(WarehouseInvoice).where(
        WarehouseInvoice.customer_id == customer_uuid
    ).order_by(WarehouseInvoice.created_at.desc())
    
    result = await db.execute(statement)
    invoices = result.scalars().all()
    
    result_list = []
    for inv in invoices:
        # Extract balance from totals JSON or use amount_paid/total_amount
        try:
            totals = json.loads(inv.totals)
            balance_due = totals.get('balance_due', 0.0)
        except:
            balance_due = float(inv.total_amount - inv.amount_paid)

        result_list.append({
            "orderid": str(inv.id),
            "invoice_no": inv.invoice_no,
            "status": "completed", # Warehouse invoices are usually completed on creation
            "customer": inv.customer_name,
            "teamname": "",
            "quantity": 0, # Could be calculated from items if needed
            "total_amount": float(inv.total_amount),
            "amount_paid": float(inv.amount_paid),
            "balance_due": float(balance_due),
            "payment_status": inv.payment_status,
            "transfer_status": inv.transfer_status,
            "transfer_error": inv.transfer_error,
            "date": inv.payment_date.strftime('%Y-%m-%d') if inv.payment_date else inv.created_at.strftime('%Y-%m-%d'),
            "created_at": inv.created_at.isoformat()
        })
    
    return result_list

@router.put("/process-payment/{order_id}")
async def process_warehouse_payment(
    order_id: str,
    payment_data: dict,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Process a payment for a warehouse invoice
    """
    try:
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format")

    # Get the invoice
    statement = select(WarehouseInvoice).where(WarehouseInvoice.id == order_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Warehouse invoice not found")

    amount = Decimal(str(payment_data.get("amount", 0)))
    payment_method = payment_data.get("payment_method", "cash")
    description = payment_data.get("description", "")
    payment_date_str = payment_data.get("payment_date")
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than zero")

    # Update invoice fields
    try:
        totals = json.loads(invoice.totals)
    except:
        totals = {
            "subtotal": float(invoice.total_amount),
            "tax": 0.0,
            "discount": float(invoice.discounts),
            "total": float(invoice.total_amount),
            "amount_paid": float(invoice.amount_paid),
            "balance_due": float(invoice.total_amount - invoice.amount_paid),
            "payment_status": invoice.payment_status
        }

    current_balance = Decimal(str(totals.get('balance_due', 0.0)))
    
    if amount > current_balance:
        raise HTTPException(status_code=400, detail=f"Payment exceeds balance due ({current_balance})")

    new_amount_paid = invoice.amount_paid + amount
    new_balance_due = current_balance - amount
    
    # Update payment status
    if new_balance_due <= 0:
        new_status = "paid"
    else:
        new_status = "partial"

    # Add to payment history
    try:
        history = json.loads(invoice.payments_history)
    except:
        history = []
    
    payment_date = datetime.fromisoformat(payment_date_str) if payment_date_str else datetime.now()
    
    new_payment = {
        "amount": float(amount),
        "payment_method": payment_method,
        "date": payment_date.isoformat(),
        "description": description
    }
    history.append(new_payment)

    # Update totals JSON
    totals['amount_paid'] = float(new_amount_paid)
    totals['balance_due'] = float(new_balance_due)
    totals['payment_status'] = new_status

    invoice.amount_paid = new_amount_paid
    invoice.payment_status = new_status
    invoice.payments_history = json.dumps(history)
    invoice.totals = json.dumps(totals)
    invoice.updated_at = datetime.now()

    # Update WarehouseCustomer balance
    if invoice.customer_id:
        customer_stmt = select(WarehouseCustomer).where(WarehouseCustomer.id == invoice.customer_id)
        customer_result = await db.execute(customer_stmt)
        customer = customer_result.scalar_one_or_none()
        if customer:
            customer.cus_balance = (customer.cus_balance or Decimal('0')) - amount
            db.add(customer)

    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)

    return {"message": "Payment processed successfully", "new_balance": float(new_balance_due)}

@router.post("/retry-transfer/{invoice_id}")
async def retry_warehouse_transfer(
    invoice_id: str,
    current_user: User = Depends(admin_cashier_employee_required_from_session()),
    db: AsyncSession = Depends(get_db)
):
    """
    Retry a pending warehouse -> branch stock transfer. Safe to call twice:
    the branch DB is checked for this invoice number first, so stock is
    never added twice.
    """
    try:
        invoice_uuid = uuid.UUID(invoice_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid invoice ID format")

    invoice = await db.get(WarehouseInvoice, invoice_uuid)
    if not invoice:
        raise HTTPException(status_code=404, detail="Warehouse invoice not found")
    if invoice.transfer_status != "pending":
        raise HTTPException(status_code=400, detail=f"Invoice {invoice.invoice_no} has no pending transfer")

    customer = await db.get(WarehouseCustomer, invoice.customer_id) if invoice.customer_id else None
    destination_branch = customer.destination_branch if customer else None
    if not destination_branch or destination_branch not in session_factories:
        raise HTTPException(status_code=400, detail="Destination branch for this invoice is not configured")

    transfer_status, transfer_error = await transfer_invoice_stock(db, invoice.id, destination_branch)
    if transfer_status != "done":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Transfer of {invoice.invoice_no} failed: {transfer_error}"
        )
    return {"message": f"Stock of {invoice.invoice_no} transferred", "transfer_status": transfer_status}

@router.get("/payment-history/{order_id}")
async def get_warehouse_payment_history(
    order_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get payment history for a warehouse invoice
    """
    try:
        order_uuid = uuid.UUID(order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format")

    statement = select(WarehouseInvoice).where(WarehouseInvoice.id == order_uuid)
    result = await db.execute(statement)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Warehouse invoice not found")

    try:
        history = json.loads(invoice.payments_history)
    except:
        history = []
    
    try:
        totals = json.loads(invoice.totals)
        balance_due = totals.get('balance_due', 0.0)
    except:
        balance_due = float(invoice.total_amount - invoice.amount_paid)

    return {
        "invoice_id": str(invoice.id),
        "invoice_no": invoice.invoice_no,
        "total_amount": float(invoice.total_amount),
        "amount_paid": float(invoice.amount_paid),
        "balance_due": float(balance_due),
        "payment_status": invoice.payment_status,
        "payments_history": history
    }

