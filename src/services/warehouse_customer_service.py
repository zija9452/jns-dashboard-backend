from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from ..models.warehouse_customer import WarehouseCustomer, WarehouseCustomerCreate, WarehouseCustomerUpdate
from ..utils.audit_logger import audit_log

class WarehouseCustomerService:
    """
    Service class for handling warehouse customer-related operations
    """

    @staticmethod
    async def create_customer(db: AsyncSession, customer_create: WarehouseCustomerCreate, user_id: str) -> WarehouseCustomer:
        """
        Create a new warehouse customer
        """
        db_customer = WarehouseCustomer(
            name=customer_create.name,
            contacts=customer_create.contacts,
            cnic=customer_create.cnic,
            branch=customer_create.branch
        )

        db.add(db_customer)
        await db.commit()
        await db.refresh(db_customer)

        # Log the action
        await audit_log(
            db=db,
            user_id=user_id,
            entity="WarehouseCustomer",
            action="CREATE",
            changes={
                "name": customer_create.name,
                "contacts": customer_create.contacts,
                "cnic": customer_create.cnic,
                "branch": customer_create.branch
            }
        )

        return db_customer

    @staticmethod
    async def get_customer(db: AsyncSession, customer_id: UUID) -> Optional[WarehouseCustomer]:
        """
        Get a warehouse customer by ID
        """
        statement = select(WarehouseCustomer).where(WarehouseCustomer.id == customer_id)
        result = await db.execute(statement)
        customer = result.scalar_one_or_none()
        return customer

    @staticmethod
    async def get_customers(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[WarehouseCustomer]:
        """
        Get a list of warehouse customers with pagination
        """
        statement = select(WarehouseCustomer).offset(skip).limit(limit)
        result = await db.execute(statement)
        customers = result.scalars().all()
        return customers

    @staticmethod
    async def update_customer(db: AsyncSession, customer_id: UUID, customer_update: WarehouseCustomerUpdate, user_id: str) -> Optional[WarehouseCustomer]:
        """
        Update a warehouse customer
        """
        db_customer = await WarehouseCustomerService.get_customer(db, customer_id)
        if not db_customer:
            return None

        # Prepare update data
        update_data = customer_update.model_dump(exclude_unset=True)

        # Update the customer
        for field, value in update_data.items():
            setattr(db_customer, field, value)

        await db.commit()
        await db.refresh(db_customer)

        # Log the action
        await audit_log(
            db=db,
            user_id=user_id,
            entity="WarehouseCustomer",
            action="UPDATE",
            changes=update_data
        )

        return db_customer

    @staticmethod
    async def delete_customer(db: AsyncSession, customer_id: UUID, user_id: str) -> bool:
        """
        Delete a warehouse customer
        """
        db_customer = await WarehouseCustomerService.get_customer(db, customer_id)
        if not db_customer:
            return False

        await db.delete(db_customer)
        await db.commit()

        # Log the action
        await audit_log(
            db=db,
            user_id=user_id,
            entity="WarehouseCustomer",
            action="DELETE",
            changes={"id": str(customer_id)}
        )

        return True
