from sqlmodel import Session, select
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from ..models.custom_order import CustomOrder, CustomOrderCreate, CustomOrderUpdate, CustomOrderStatus
from ..utils.audit_logger import audit_log

class CustomOrderService:
    """
    Service class for handling custom order-related operations
    """

    @staticmethod
    async def create_custom_order(db: Session, custom_order_create: CustomOrderCreate, user_id: UUID) -> CustomOrder:
        """
        Create a new custom order
        """
        db_custom_order = CustomOrder(
            fields=custom_order_create.fields,
            status=custom_order_create.status,
            linked_invoice=custom_order_create.linked_invoice
        )

        db.add(db_custom_order)
        await db.commit()
        await db.refresh(db_custom_order)

        # Log the action
        await audit_log(
            db=db,
            user_id=str(user_id),
            entity="CustomOrder",
            action="CREATE",
            changes={
                "status": custom_order_create.status.value,
                "linked_invoice": str(custom_order_create.linked_invoice) if custom_order_create.linked_invoice else None
            }
        )

        return db_custom_order

    @staticmethod
    async def get_custom_order(db: Session, custom_order_id: UUID) -> Optional[CustomOrder]:
        """
        Get a custom order by ID
        """
        statement = select(CustomOrder).where(CustomOrder.id == custom_order_id)
        custom_order = db.exec(statement).first()
        return custom_order

    @staticmethod
    async def get_custom_orders(db: Session, status: Optional[CustomOrderStatus] = None, skip: int = 0, limit: int = 100) -> List[CustomOrder]:
        """
        Get a list of custom orders with pagination, optionally filtered by status
        """
        statement = select(CustomOrder)
        if status:
            statement = statement.where(CustomOrder.status == status)
        statement = statement.order_by(CustomOrder.created_at.desc()).offset(skip).limit(limit)
        custom_orders = db.exec(statement).all()
        return custom_orders

    @staticmethod
    async def update_custom_order(db: Session, custom_order_id: UUID, custom_order_update: CustomOrderUpdate, user_id: UUID) -> Optional[CustomOrder]:
        """
        Update a custom order
        """
        db_custom_order = await CustomOrderService.get_custom_order(db, custom_order_id)
        if not db_custom_order:
            return None

        # Get the old values for audit purposes
        old_values = {
            "status": db_custom_order.status.value,
            "fields": db_custom_order.fields,
            "linked_invoice": str(db_custom_order.linked_invoice) if db_custom_order.linked_invoice else None
        }

        # Prepare update data
        update_data = custom_order_update.dict(exclude_unset=True)

        # Update the custom order
        for field, value in update_data.items():
            setattr(db_custom_order, field, value)

        await db.commit()
        await db.refresh(db_custom_order)

        # Log the action
        await audit_log(
            db=db,
            user_id=str(user_id),
            entity="CustomOrder",
            action="UPDATE",
            changes={**old_values, **update_data}
        )

        return db_custom_order

    @staticmethod
    async def delete_custom_order(db: Session, custom_order_id: UUID, user_id: UUID) -> bool:
        """
        Delete a custom order
        """
        db_custom_order = await CustomOrderService.get_custom_order(db, custom_order_id)
        if not db_custom_order:
            return False

        await db.delete(db_custom_order)
        await db.commit()

        # Log the action
        await audit_log(
            db=db,
            user_id=str(user_id),
            entity="CustomOrder",
            action="DELETE",
            changes={"id": str(custom_order_id)}
        )

        return True

    @staticmethod
    async def link_invoice_to_custom_order(db: Session, custom_order_id: UUID, invoice_id: UUID, user_id: UUID) -> Optional[CustomOrder]:
        """
        Link an invoice to a custom order
        """
        db_custom_order = await CustomOrderService.get_custom_order(db, custom_order_id)
        if not db_custom_order:
            return None

        old_linked_invoice = db_custom_order.linked_invoice
        db_custom_order.linked_invoice = invoice_id

        await db.commit()
        await db.refresh(db_custom_order)

        # Log the action
        await audit_log(
            db=db,
            user_id=str(user_id),
            entity="CustomOrder",
            action="UPDATE",
            changes={
                "linked_invoice": f"{str(old_linked_invoice)} -> {str(invoice_id)}"
            }
        )

        return db_custom_order