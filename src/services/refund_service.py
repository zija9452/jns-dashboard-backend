from sqlmodel import Session, select
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime
import uuid
from ..models.refund import Refund, RefundCreate, RefundUpdate
from ..models.invoice import Invoice
from ..models.product import Product
from ..services.invoice_service import InvoiceService
from ..utils.audit_logger import audit_log

class RefundService:
    """
    Service class for handling refund-related operations
    """

    @staticmethod
    async def create_refund(db: Session, refund_create: RefundCreate, user_id: UUID) -> Refund:
        """
        Create a new refund and update stock levels accordingly
        """
        db_refund = Refund(
            invoice_id=refund_create.invoice_id,
            items=refund_create.items,
            amount=refund_create.amount,
            reason=refund_create.reason,
            processed_by=refund_create.processed_by
        )

        db.add(db_refund)
        await db.commit()
        await db.refresh(db_refund)

        # Update stock levels for products in the refund (increase stock back)
        await RefundService._update_stock_levels_for_refund(db, refund_create.invoice_id, increase=True)

        # Update invoice status if needed
        await RefundService._update_invoice_after_refund(db, refund_create.invoice_id)

        # Log the action
        await audit_log(
            db=db,
            user_id=str(user_id),
            entity="Refund",
            action="CREATE",
            changes={
                "invoice_id": str(refund_create.invoice_id),
                "amount": str(refund_create.amount),
                "reason": refund_create.reason
            }
        )

        return db_refund

    @staticmethod
    async def _update_stock_levels_for_refund(db: Session, invoice_id: UUID, increase: bool = True):
        """
        Internal method to update stock levels based on refund items
        """
        # Get the original invoice
        statement = select(Invoice).where(Invoice.id == invoice_id)
        invoice = db.exec(statement).first()
        if not invoice:
            return

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
                    # Update stock level (increase for refunds)
                    adjustment = quantity if increase else -quantity
                    product.stock_level += adjustment
                    await db.commit()

    @staticmethod
    async def _update_invoice_after_refund(db: Session, invoice_id: UUID):
        """
        Internal method to update invoice status after refund
        """
        statement = select(Invoice).where(Invoice.id == invoice_id)
        invoice = db.exec(statement).first()
        if invoice:
            # For simplicity, we'll mark the invoice as having a refund
            # In a real system, you might have more complex status logic
            if invoice.status != "refunded":
                old_status = invoice.status
                invoice.status = "refunded"  # This might be a custom status
                await db.commit()

    @staticmethod
    async def get_refund(db: Session, refund_id: UUID) -> Optional[Refund]:
        """
        Get a refund by ID
        """
        statement = select(Refund).where(Refund.id == refund_id)
        refund = db.exec(statement).first()
        return refund

    @staticmethod
    async def get_refunds(db: Session, invoice_id: Optional[UUID] = None, skip: int = 0, limit: int = 100) -> List[Refund]:
        """
        Get a list of refunds with pagination, optionally filtered by invoice
        """
        statement = select(Refund)
        if invoice_id:
            statement = statement.where(Refund.invoice_id == invoice_id)
        statement = statement.order_by(Refund.created_at.desc()).offset(skip).limit(limit)
        refunds = db.exec(statement).all()
        return refunds

    @staticmethod
    async def update_refund(db: Session, refund_id: UUID, refund_update: RefundUpdate, user_id: UUID) -> Optional[Refund]:
        """
        Update a refund
        """
        db_refund = await RefundService.get_refund(db, refund_id)
        if not db_refund:
            return None

        # Get the old values for audit purposes
        old_values = {
            "amount": str(db_refund.amount),
            "reason": db_refund.reason
        }

        # Prepare update data
        update_data = refund_update.dict(exclude_unset=True)

        # Update the refund
        for field, value in update_data.items():
            setattr(db_refund, field, value)

        await db.commit()
        await db.refresh(db_refund)

        # Log the action
        await audit_log(
            db=db,
            user_id=str(user_id),
            entity="Refund",
            action="UPDATE",
            changes={**old_values, **update_data}
        )

        return db_refund

    @staticmethod
    async def delete_refund(db: Session, refund_id: UUID, user_id: UUID) -> bool:
        """
        Delete a refund and restore stock levels
        """
        db_refund = await RefundService.get_refund(db, refund_id)
        if not db_refund:
            return False

        # Restore stock levels since we're deleting the refund
        await RefundService._update_stock_levels_for_refund(db, db_refund.invoice_id, increase=False)

        await db.delete(db_refund)
        await db.commit()

        # Log the action
        await audit_log(
            db=db,
            user_id=str(user_id),
            entity="Refund",
            action="DELETE",
            changes={"id": str(refund_id)}
        )

        return True