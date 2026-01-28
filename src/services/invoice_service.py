from sqlmodel import Session, select
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
import uuid
from ..models.invoice import Invoice, InvoiceCreate, InvoiceUpdate, InvoiceStatus
from ..models.customer import Customer
from ..models.product import Product
from ..models.stock_entry import StockEntryCreate, StockEntryType
from ..services.stock_service import StockService
from ..utils.audit_logger import audit_log

class InvoiceService:
    """
    Service class for handling invoice-related operations
    """

    @staticmethod
    async def create_invoice(db: Session, invoice_create: InvoiceCreate, user_id: UUID) -> Invoice:
        """
        Create a new invoice and update stock levels accordingly
        """
        # Generate invoice number
        invoice_no = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        db_invoice = Invoice(
            invoice_no=invoice_no,
            customer_id=invoice_create.customer_id,
            items=invoice_create.items,
            totals=invoice_create.totals,
            taxes=invoice_create.taxes,
            discounts=invoice_create.discounts,
            status=invoice_create.status
        )

        db.add(db_invoice)
        await db.commit()
        await db.refresh(db_invoice)

        # Update stock levels for products in the invoice
        await InvoiceService._update_stock_levels_for_invoice(db, db_invoice, decrease=True)

        # Log the action
        await audit_log(
            db=db,
            user_id=str(user_id),
            entity="Invoice",
            action="CREATE",
            changes={
                "invoice_no": invoice_no,
                "customer_id": str(invoice_create.customer_id),
                "items_count": len(invoice_create.items) if isinstance(invoice_create.items, list) else "unknown"
            }
        )

        return db_invoice

    @staticmethod
    async def _update_stock_levels_for_invoice(db: Session, invoice: Invoice, decrease: bool = True):
        """
        Internal method to update stock levels based on invoice items
        """
        # Parse the items from the JSON string
        import json
        try:
            items = json.loads(invoice.items)
        except:
            # If parsing fails, skip stock update
            return

        for item in items:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 0)

            if product_id and quantity:
                # Get the product to update its stock
                statement = select(Product).where(Product.id == UUID(product_id))
                product = db.exec(statement).first()

                if product:
                    # Update stock level (decrease for sales, increase for returns)
                    adjustment = -quantity if decrease else quantity
                    product.stock_level += adjustment
                    await db.commit()

    @staticmethod
    async def get_invoice(db: Session, invoice_id: UUID) -> Optional[Invoice]:
        """
        Get an invoice by ID
        """
        statement = select(Invoice).where(Invoice.id == invoice_id)
        invoice = db.exec(statement).first()
        return invoice

    @staticmethod
    async def get_invoices(db: Session, customer_id: Optional[UUID] = None, skip: int = 0, limit: int = 100) -> List[Invoice]:
        """
        Get a list of invoices with pagination, optionally filtered by customer
        """
        statement = select(Invoice)
        if customer_id:
            statement = statement.where(Invoice.customer_id == customer_id)
        statement = statement.order_by(Invoice.created_at.desc()).offset(skip).limit(limit)
        invoices = db.exec(statement).all()
        return invoices

    @staticmethod
    async def update_invoice(db: Session, invoice_id: UUID, invoice_update: InvoiceUpdate, user_id: UUID) -> Optional[Invoice]:
        """
        Update an invoice
        """
        db_invoice = await InvoiceService.get_invoice(db, invoice_id)
        if not db_invoice:
            return None

        # Get the old values for audit purposes
        old_values = {
            "status": db_invoice.status.value,
            "items": db_invoice.items,
            "totals": db_invoice.totals
        }

        # Prepare update data
        update_data = invoice_update.dict(exclude_unset=True)

        # Handle stock level updates if status is changing from DRAFT to ISSUED or PAID
        if 'status' in update_data and db_invoice.status == InvoiceStatus.DRAFT:
            if update_data['status'] in [InvoiceStatus.ISSUED, InvoiceStatus.PAID]:
                # This is a sale, decrease stock
                await InvoiceService._update_stock_levels_for_invoice(db, db_invoice, decrease=True)
            elif update_data['status'] in [InvoiceStatus.CANCELLED]:
                # This is cancelled, increase stock back
                await InvoiceService._update_stock_levels_for_invoice(db, db_invoice, decrease=False)

        # Update the invoice
        for field, value in update_data.items():
            setattr(db_invoice, field, value)

        await db.commit()
        await db.refresh(db_invoice)

        # Log the action
        await audit_log(
            db=db,
            user_id=str(user_id),
            entity="Invoice",
            action="UPDATE",
            changes={**old_values, **update_data}
        )

        return db_invoice

    @staticmethod
    async def delete_invoice(db: Session, invoice_id: UUID, user_id: UUID) -> bool:
        """
        Delete an invoice and restore stock levels
        """
        db_invoice = await InvoiceService.get_invoice(db, invoice_id)
        if not db_invoice:
            return False

        # Restore stock levels since we're deleting the invoice
        await InvoiceService._update_stock_levels_for_invoice(db, db_invoice, decrease=False)

        await db.delete(db_invoice)
        await db.commit()

        # Log the action
        await audit_log(
            db=db,
            user_id=str(user_id),
            entity="Invoice",
            action="DELETE",
            changes={"id": str(invoice_id)}
        )

        return True

    @staticmethod
    async def mark_invoice_paid(db: Session, invoice_id: UUID, user_id: UUID) -> Optional[Invoice]:
        """
        Mark an invoice as paid
        """
        db_invoice = await InvoiceService.get_invoice(db, invoice_id)
        if not db_invoice:
            return None

        if db_invoice.status != InvoiceStatus.ISSUED:
            # Can only mark issued invoices as paid
            return None

        old_status = db_invoice.status
        db_invoice.status = InvoiceStatus.PAID

        await db.commit()
        await db.refresh(db_invoice)

        # Log the action
        await audit_log(
            db=db,
            user_id=str(user_id),
            entity="Invoice",
            action="UPDATE",
            changes={"status": f"{old_status.value} -> {db_invoice.status.value}"}
        )

        return db_invoice