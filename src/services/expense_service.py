from sqlmodel import Session, select
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
    async def create_expense(db: Session, expense_create: ExpenseCreate) -> Expense:
        """
        Create a new expense
        """
        db_expense = Expense(
            type=expense_create.type,
            amount=expense_create.amount,
            date=expense_create.date or date.today(),
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
                "type": expense_create.type,
                "amount": str(expense_create.amount),
                "date": str(expense_create.date or date.today()),
                "note": expense_create.note
            }
        )

        return db_expense

    @staticmethod
    async def get_expense(db: Session, expense_id: UUID) -> Optional[Expense]:
        """
        Get an expense by ID
        """
        statement = select(Expense).where(Expense.id == expense_id)
        expense = db.exec(statement).first()
        return expense

    @staticmethod
    async def get_expenses(db: Session, created_by: Optional[UUID] = None, skip: int = 0, limit: int = 100) -> List[Expense]:
        """
        Get a list of expenses with pagination, optionally filtered by creator
        """
        statement = select(Expense)
        if created_by:
            statement = statement.where(Expense.created_by == created_by)
        statement = statement.order_by(Expense.date.desc()).offset(skip).limit(limit)
        expenses = db.exec(statement).all()
        return expenses

    @staticmethod
    async def update_expense(db: Session, expense_id: UUID, expense_update: ExpenseUpdate) -> Optional[Expense]:
        """
        Update an expense
        """
        db_expense = await ExpenseService.get_expense(db, expense_id)
        if not db_expense:
            return None

        # Get the old values for audit purposes
        old_values = {
            "type": db_expense.type,
            "amount": str(db_expense.amount),
            "date": str(db_expense.date),
            "note": db_expense.note
        }

        # Prepare update data
        update_data = expense_update.dict(exclude_unset=True)

        # Update the expense
        for field, value in update_data.items():
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
    async def delete_expense(db: Session, expense_id: UUID) -> bool:
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