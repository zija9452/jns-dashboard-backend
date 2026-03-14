"""Add indexes to expense and refund tables

Revision ID: add_indexes_expense_refund
Revises: previous_revision
Create Date: 2026-03-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_indexes_expense_refund'
down_revision = None  # Change this to your last migration
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add indexes to expense table
    op.create_index('ix_expenses_expense_type', 'expenses', ['expense_type'], unique=False)
    op.create_index('ix_expenses_expense_date', 'expenses', ['expense_date'], unique=False)
    op.create_index('ix_expenses_branch', 'expenses', ['branch'], unique=False)
    op.create_index('ix_expenses_created_by', 'expenses', ['created_by'], unique=False)
    op.create_index('ix_expenses_created_at', 'expenses', ['created_at'], unique=False)
    
    # Add indexes to refund table
    op.create_index('ix_refunds_invoice_id', 'refunds', ['invoice_id'], unique=False)
    op.create_index('ix_refunds_processed_by', 'refunds', ['processed_by'], unique=False)


def downgrade() -> None:
    # Remove indexes from refund table
    op.drop_index('ix_refunds_processed_by', 'refunds')
    op.drop_index('ix_refunds_invoice_id', 'refunds')
    
    # Remove indexes from expense table
    op.drop_index('ix_expenses_created_at', 'expenses')
    op.drop_index('ix_expenses_created_by', 'expenses')
    op.drop_index('ix_expenses_branch', 'expenses')
    op.drop_index('ix_expenses_expense_date', 'expenses')
    op.drop_index('ix_expenses_expense_type', 'expenses')
