from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from ..models.customer import Customer, CustomerCreate, CustomerUpdate
from ..utils.audit_logger import audit_log

class CustomerService:
    """
    Service class for handling customer-related operations
    """

    @staticmethod
    async def create_customer(db: AsyncSession, customer_create: CustomerCreate) -> Customer:
        """
        Create a new customer
        """
        db_customer = Customer(
            name=customer_create.name,
            contacts=customer_create.contacts,
            billing_addr=customer_create.billing_addr,
            shipping_addr=customer_create.shipping_addr,
            credit_limit=customer_create.credit_limit
        )

        db.add(db_customer)
        await db.commit()
        await db.refresh(db_customer)

        # Log the action
        await audit_log(
            db=db,
            user_id="",  # Need to pass actual user ID from context
            entity="Customer",
            action="CREATE",
            changes={
                "name": customer_create.name,
                "contacts": customer_create.contacts,
                "credit_limit": str(customer_create.credit_limit)
            }
        )

        return db_customer

    @staticmethod
    async def get_customer(db: AsyncSession, customer_id: UUID) -> Optional[Customer]:
        """
        Get a customer by ID
        """
        statement = select(Customer).where(Customer.id == customer_id)
        result = await db.execute(statement)
        customer = result.scalar_one_or_none()
        return customer

    @staticmethod
    async def get_customers(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Customer]:
        """
        Get a list of customers with pagination
        """
        statement = select(Customer).offset(skip).limit(limit)
        result = await db.execute(statement)
        customers = result.scalars().all()
        return customers

    @staticmethod
    async def update_customer(db: AsyncSession, customer_id: UUID, customer_update: CustomerUpdate) -> Optional[Customer]:
        """
        Update a customer
        """
        db_customer = await CustomerService.get_customer(db, customer_id)
        if not db_customer:
            return None

        # Prepare update data
        update_data = customer_update.dict(exclude_unset=True)

        # Update the customer
        for field, value in update_data.items():
            setattr(db_customer, field, value)

        await db.commit()
        await db.refresh(db_customer)

        # Log the action
        await audit_log(
            db=db,
            user_id="",  # Need to pass actual user ID from context
            entity="Customer",
            action="UPDATE",
            changes=update_data
        )

        return db_customer

    @staticmethod
    async def delete_customer(db: AsyncSession, customer_id: UUID) -> bool:
        """
        Delete a customer
        """
        db_customer = await CustomerService.get_customer(db, customer_id)
        if not db_customer:
            return False

        await db.delete(db_customer)
        await db.commit()

        # Log the action
        await audit_log(
            db=db,
            user_id="",  # Need to pass actual user ID from context
            entity="Customer",
            action="DELETE",
            changes={"id": str(customer_id)}
        )

        return True