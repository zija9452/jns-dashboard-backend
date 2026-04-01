import asyncio
import os
from sqlmodel import SQLModel
from .database.database import engine
from .models.user import User
from .models.role import Role
from .models.product import Product
from .models.customer import Customer
from .models.vendor import Vendor
from .models.salesman import Salesman
from .models.stock_entry import StockEntry
from .models.expense import Expense
from .models.invoice import Invoice
from .models.refund import Refund
from .models.audit_log import AuditLog
from .models.category import Category
from .models.brand import Brand
from .auth.password import get_password_hash


async def create_tables():
    """
    Create all tables in the database using the proper async pattern
    """
    async with engine.begin() as conn:
        # Use run_sync to properly handle the sync operation in an async context
        await conn.run_sync(SQLModel.metadata.create_all)


async def create_indexes():
    """
    Create database indexes for performance optimization
    """
    # For now, this is a placeholder - actual index creation would go here
    pass


async def create_default_roles(db_session):
    """
    Create default roles if they don't exist
    """
    from sqlmodel import select

    # Check if roles already exist
    result = await db_session.execute(select(Role))
    existing_roles = result.scalars().all()

    if not existing_roles:
        # Create default roles
        admin_role = Role(name="admin", permissions='{"all": true}')
        cashier_role = Role(name="cashier", permissions='{"pos": true, "view_inventory": true}')
        employee_role = Role(name="employee", permissions='{"view_products": true, "view_customers": true}')

        db_session.add(admin_role)
        db_session.add(cashier_role)
        db_session.add(employee_role)
        await db_session.commit()


async def create_admin_user(db_session):
    """
    Create a default admin user if no users exist
    """
    from sqlmodel import select

    # Check if any users exist
    result = await db_session.execute(select(User))
    existing_users = result.scalars().all()

    if not existing_users:
        # Create admin role first if it doesn't exist
        role_result = await db_session.execute(select(Role).where(Role.name == "admin"))
        admin_role = role_result.scalar_one_or_none()

        if not admin_role:
            admin_role = Role(name="admin", permissions='{"all": true}')
            db_session.add(admin_role)
            await db_session.commit()
            await db_session.refresh(admin_role)

        # Get admin credentials from environment variables
        admin_username = os.getenv('ADMIN_USERNAME')
        admin_password = os.getenv('ADMIN_PASSWORD')
        
        # Create default admin user
        admin_user = User(
            full_name="Admin User",
            username=admin_username,
            password_hash=get_password_hash(admin_password),  # Use password from environment
            role_id=admin_role.id,
            is_active=True
        )

        db_session.add(admin_user)
        await db_session.commit()


async def initialize_database():
    """
    Initialize the database with tables and default data
    """
    # Create tables first
    await create_tables()
    await create_indexes()  # Create indexes for performance

    # Create a session to add default data
    from .database.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db_session:
        await create_default_roles(db_session)
        await create_admin_user(db_session)


if __name__ == "__main__":
    asyncio.run(initialize_database())