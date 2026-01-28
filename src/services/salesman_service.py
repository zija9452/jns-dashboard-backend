from sqlmodel import Session, select
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from ..models.salesman import Salesman, SalesmanCreate, SalesmanUpdate
from ..utils.audit_logger import audit_log

class SalesmanService:
    """
    Service class for handling salesman-related operations
    """

    @staticmethod
    async def create_salesman(db: Session, salesman_create: SalesmanCreate) -> Salesman:
        """
        Create a new salesman
        """
        db_salesman = Salesman(
            name=salesman_create.name,
            code=salesman_create.code,
            commission_rate=salesman_create.commission_rate
        )

        db.add(db_salesman)
        await db.commit()
        await db.refresh(db_salesman)

        # Log the action
        await audit_log(
            db=db,
            user_id="",  # Need to pass actual user ID from context
            entity="Salesman",
            action="CREATE",
            changes={
                "name": salesman_create.name,
                "code": salesman_create.code,
                "commission_rate": str(salesman_create.commission_rate)
            }
        )

        return db_salesman

    @staticmethod
    async def get_salesman(db: Session, salesman_id: UUID) -> Optional[Salesman]:
        """
        Get a salesman by ID
        """
        statement = select(Salesman).where(Salesman.id == salesman_id)
        salesman = db.exec(statement).first()
        return salesman

    @staticmethod
    async def get_salesman_by_code(db: Session, code: str) -> Optional[Salesman]:
        """
        Get a salesman by code
        """
        statement = select(Salesman).where(Salesman.code == code)
        salesman = db.exec(statement).first()
        return salesman

    @staticmethod
    async def get_salesmen(db: Session, skip: int = 0, limit: int = 100) -> List[Salesman]:
        """
        Get a list of salesmen with pagination
        """
        statement = select(Salesman).offset(skip).limit(limit)
        salesmen = db.exec(statement).all()
        return salesmen

    @staticmethod
    async def update_salesman(db: Session, salesman_id: UUID, salesman_update: SalesmanUpdate) -> Optional[Salesman]:
        """
        Update a salesman
        """
        db_salesman = await SalesmanService.get_salesman(db, salesman_id)
        if not db_salesman:
            return None

        # Prepare update data
        update_data = salesman_update.dict(exclude_unset=True)

        # Update the salesman
        for field, value in update_data.items():
            setattr(db_salesman, field, value)

        await db.commit()
        await db.refresh(db_salesman)

        # Log the action
        await audit_log(
            db=db,
            user_id="",  # Need to pass actual user ID from context
            entity="Salesman",
            action="UPDATE",
            changes=update_data
        )

        return db_salesman

    @staticmethod
    async def delete_salesman(db: Session, salesman_id: UUID) -> bool:
        """
        Delete a salesman
        """
        db_salesman = await SalesmanService.get_salesman(db, salesman_id)
        if not db_salesman:
            return False

        await db.delete(db_salesman)
        await db.commit()

        # Log the action
        await audit_log(
            db=db,
            user_id="",  # Need to pass actual user ID from context
            entity="Salesman",
            action="DELETE",
            changes={"id": str(salesman_id)}
        )

        return True