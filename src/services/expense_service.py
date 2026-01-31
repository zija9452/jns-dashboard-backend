from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from datetime import datetime, date
from ..models.expense import Expense, ExpenseCreate, ExpenseUpdate
from ..utils.audit_logger import audit_log

class ExpenseService:
    """
    Service class for handling expense-related operations
    """

    @staticmethod
    async def create_expense(db: AsyncSession, expense_create: ExpenseCreate) -> Expense:
        """
        Create a new expense
        """
        db_expense = Expense(
            expense_type=expense_create.expense_type,
            amount=expense_create.amount,
            expense_date=expense_create.date or date.today(),
            note=expense_create.note,
            created_by=expense_create.created_by
        )

        db.add(db_expense)
        await db.commit()
        await db.refresh(db_expense)

        # Log the action
        await audit_log(
            db=db,
            user_id=str(expense_create.created_by),
            entity="Expense",
            action="CREATE",
            changes={
                "expense_type": expense_create.expense_type,
                "amount": str(expense_create.amount),
                "expense_date": str(expense_create.date or date.today()),
                "note": expense_create.note
            }
        )

        return db_expense

    @staticmethod
    async def get_expense(db: AsyncSession, expense_id: UUID) -> Optional[Expense]:
        """
        Get an expense by ID
        """
        statement = select(Expense).where(Expense.id == expense_id)
        result = await db.execute(statement)
        expense = result.scalar_one_or_none()
        return expense

    @staticmethod
    async def get_expenses(db: AsyncSession, created_by: Optional[UUID] = None, skip: int = 0, limit: int = 100) -> List[Expense]:
        """
        Get a list of expenses with pagination, optionally filtered by creator
        """
        statement = select(Expense)
        if created_by:
            statement = statement.where(Expense.created_by == created_by)
        statement = statement.order_by(Expense.expense_date.desc()).offset(skip).limit(limit)
        result = await db.execute(statement)
        expenses = result.scalars().all()
        return expenses

    @staticmethod
    async def update_expense(db: AsyncSession, expense_id: UUID, expense_update: ExpenseUpdate) -> Optional[Expense]:
        """
        Update an expense
        """
        db_expense = await ExpenseService.get_expense(db, expense_id)
        if not db_expense:
            return None

        # Get the old values for audit purposes
        old_values = {
            "expense_type": db_expense.expense_type,
            "amount": str(db_expense.amount),
            "expense_date": str(db_expense.expense_date),
            "note": db_expense.note
        }

        # Prepare update data
        update_data = expense_update.model_dump(exclude_unset=True)

        # Update the expense
        for field, value in update_data.items():
            if hasattr(db_expense, field):
                setattr(db_expense, field, value)

        await db.commit()
        await db.refresh(db_expense)

        # Log the action
        await audit_log(
            db=db,
            user_id=str(db_expense.created_by),
            entity="Expense",
            action="UPDATE",
            changes={**old_values, **update_data}
        )

        return db_expense

    @staticmethod
    async def delete_expense(db: AsyncSession, expense_id: UUID) -> bool:
        """
        Delete an expense
        """
        db_expense = await ExpenseService.get_expense(db, expense_id)
        if not db_expense:
            return False

        await db.delete(db_expense)
        await db.commit()

        # Log the action
        await audit_log(
            db=db,
            user_id=str(db_expense.created_by),
            entity="Expense",
            action="DELETE",
            changes={"id": str(expense_id)}
        )

        return True