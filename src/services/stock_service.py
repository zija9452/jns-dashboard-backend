from sqlmodel import Session, select
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from ..models.stock_entry import StockEntry, StockEntryCreate, StockEntryUpdate, StockEntryType
from ..models.product import Product
from ..utils.audit_logger import audit_log

class StockService:
    """
    Service class for handling stock-related operations
    """

    @staticmethod
    async def create_stock_entry(db: Session, stock_entry_create: StockEntryCreate) -> StockEntry:
        """
        Create a new stock entry
        """
        db_stock_entry = StockEntry(
            product_id=stock_entry_create.product_id,
            qty=stock_entry_create.qty,
            type=stock_entry_create.type,
            location=stock_entry_create.location,
            batch=stock_entry_create.batch,
            expiry=stock_entry_create.expiry,
            ref=stock_entry_create.ref
        )

        db.add(db_stock_entry)
        await db.commit()
        await db.refresh(db_stock_entry)

        # Update product stock level based on the type of entry
        await StockService._update_product_stock(db, stock_entry_create.product_id, stock_entry_create.qty)

        # Log the action
        await audit_log(
            db=db,
            user_id="",  # Need to pass actual user ID from context
            entity="StockEntry",
            action="CREATE",
            changes={
                "product_id": str(stock_entry_create.product_id),
                "qty": stock_entry_create.qty,
                "type": stock_entry_create.type.value
            }
        )

        return db_stock_entry

    @staticmethod
    async def _update_product_stock(db: Session, product_id: UUID, qty: int):
        """
        Internal method to update product stock level
        """
        statement = select(Product).where(Product.id == product_id)
        product = db.exec(statement).first()
        if product:
            product.stock_level += qty
            await db.commit()

    @staticmethod
    async def get_stock_entry(db: Session, stock_id: UUID) -> Optional[StockEntry]:
        """
        Get a stock entry by ID
        """
        statement = select(StockEntry).where(StockEntry.id == stock_id)
        stock_entry = db.exec(statement).first()
        return stock_entry

    @staticmethod
    async def get_stock_entries(db: Session, product_id: Optional[UUID] = None, skip: int = 0, limit: int = 100) -> List[StockEntry]:
        """
        Get a list of stock entries with pagination, optionally filtered by product
        """
        statement = select(StockEntry)
        if product_id:
            statement = statement.where(StockEntry.product_id == product_id)
        statement = statement.offset(skip).limit(limit)
        stock_entries = db.exec(statement).all()
        return stock_entries

    @staticmethod
    async def update_stock_entry(db: Session, stock_id: UUID, stock_update: StockEntryUpdate) -> Optional[StockEntry]:
        """
        Update a stock entry
        """
        db_stock_entry = await StockService.get_stock_entry(db, stock_id)
        if not db_stock_entry:
            return None

        # Get the old values for audit purposes
        old_values = {
            "qty": db_stock_entry.qty,
            "type": db_stock_entry.type.value,
            "location": db_stock_entry.location
        }

        # Prepare update data
        update_data = stock_update.dict(exclude_unset=True)

        # Update the stock entry
        for field, value in update_data.items():
            setattr(db_stock_entry, field, value)

        await db.commit()
        await db.refresh(db_stock_entry)

        # Log the action
        await audit_log(
            db=db,
            user_id="",  # Need to pass actual user ID from context
            entity="StockEntry",
            action="UPDATE",
            changes={**old_values, **update_data}
        )

        return db_stock_entry

    @staticmethod
    async def delete_stock_entry(db: Session, stock_id: UUID) -> bool:
        """
        Delete a stock entry
        """
        db_stock_entry = await StockService.get_stock_entry(db, stock_id)
        if not db_stock_entry:
            return False

        # Adjust product stock level back
        await StockService._update_product_stock(db, db_stock_entry.product_id, -db_stock_entry.qty)

        await db.delete(db_stock_entry)
        await db.commit()

        # Log the action
        await audit_log(
            db=db,
            user_id="",  # Need to pass actual user ID from context
            entity="StockEntry",
            action="DELETE",
            changes={"id": str(stock_id)}
        )

        return True

    @staticmethod
    async def get_product_stock_level(db: Session, product_id: UUID) -> Optional[int]:
        """
        Get the current stock level for a product
        """
        statement = select(Product).where(Product.id == product_id)
        product = db.exec(statement).first()
        if product:
            return product.stock_level
        return None