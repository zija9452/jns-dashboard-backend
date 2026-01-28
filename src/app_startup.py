import asyncio
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
from .models.custom_order import CustomOrder
from .models.refund import Refund
from .models.audit_log import AuditLog
from .auth.password import get_password_hash

async def create_tables():
    """
    Create all tables in the database
    """
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def create_indexes():
    """
    Create database indexes for performance optimization
    """
    from .database.indexes import create_indexes
    create_indexes(engine.sync_engine)  # Use sync engine for index creation

async def create_default_roles(db_session):
    """
    Create default roles if they don't exist
    """
    from sqlmodel import select

    # Check if roles already exist
    result = await db_session.exec(select(Role))
    existing_roles = result.all()

    if not existing_roles:
        # Create default roles
        admin_role = Role(name="admin", permissions='{"all": true}')
        cashier_role = Role(name="cashier", permissions='{"pos": true, "view_inventory": true}')
        employee_role = Role(name="employee", permissions='{"view_products": true, "view_customers": true}')

        db_session.add(admin_role)
        db_session.add(cashier_role)
        db_session.add(employee_role)
        await db_session.commit()

        print("Default roles created: admin, cashier, employee")

async def create_admin_user(db_session):
    """
    Create a default admin user if no users exist
    """
    from sqlmodel import select

    # Check if any users exist
    result = await db_session.exec(select(User))
    existing_users = result.all()

    if not existing_users:
        # Create admin role first if it doesn't exist
        from .models.role import Role
        role_result = await db_session.exec(select(Role).where(Role.name == "admin"))
        admin_role = role_result.first()

        if not admin_role:
            admin_role = Role(name="admin", permissions='{"all": true}')
            db_session.add(admin_role)
            await db_session.commit()
            await db_session.refresh(admin_role)

        # Create default admin user
        admin_user = User(
            full_name="Admin User",
            email="admin@regalpos.com",
            username="admin",
            password_hash=get_password_hash("admin123"),  # Default password
            role_id=admin_role.id,
            is_active=True
        )

        db_session.add(admin_user)
        await db_session.commit()

        print("Default admin user created: username: admin, password: admin123")

async def initialize_database():
    """
    Initialize the database with tables and default data
    """
    await create_tables()
    await create_indexes()  # Create indexes for performance

    # Create a session to add default data
    from .database.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await create_default_roles(session)
        await create_admin_user(session)

    print("Database initialized successfully!")

if __name__ == "__main__":
    asyncio.run(initialize_database())