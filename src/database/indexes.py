from sqlalchemy import Index
from sqlalchemy.ext.declarative import declarative_base
from src.models.user import User
from src.models.product import Product
from src.models.invoice import Invoice
from src.models.customer import Customer
from src.models.audit_log import AuditLog

# Define database indexes for performance optimization

# User table indexes
user_email_index = Index('idx_user_email', User.email)
user_username_index = Index('idx_user_username', User.username)
user_role_index = Index('idx_user_role_id', User.role_id)

# Product table indexes
product_sku_index = Index('idx_product_sku', Product.sku)
product_name_index = Index('idx_product_name', Product.name)
product_category_index = Index('idx_product_category', Product.category)
product_stock_index = Index('idx_product_stock_level', Product.stock_level)

# Invoice table indexes
invoice_customer_index = Index('idx_invoice_customer_id', Invoice.customer_id)
invoice_date_index = Index('idx_invoice_created_at', Invoice.created_at)
invoice_status_index = Index('idx_invoice_status', Invoice.status)
invoice_number_index = Index('idx_invoice_number', Invoice.invoice_no)

# Customer table indexes
customer_name_index = Index('idx_customer_name', Customer.name)
customer_email_index = Index('idx_customer_email', Customer.contacts)  # Assuming email is in contacts JSON

# Audit log table indexes
audit_entity_index = Index('idx_audit_entity', AuditLog.entity)
audit_action_index = Index('idx_audit_action', AuditLog.action)
audit_user_index = Index('idx_audit_user_id', AuditLog.user_id)
audit_timestamp_index = Index('idx_audit_timestamp', AuditLog.timestamp)

def create_indexes(engine):
    """
    Create all defined indexes in the database
    """
    # Create indexes for User table
    user_email_index.create(engine, checkfirst=True)
    user_username_index.create(engine, checkfirst=True)
    user_role_index.create(engine, checkfirst=True)

    # Create indexes for Product table
    product_sku_index.create(engine, checkfirst=True)
    product_name_index.create(engine, checkfirst=True)
    product_category_index.create(engine, checkfirst=True)
    product_stock_index.create(engine, checkfirst=True)

    # Create indexes for Invoice table
    invoice_customer_index.create(engine, checkfirst=True)
    invoice_date_index.create(engine, checkfirst=True)
    invoice_status_index.create(engine, checkfirst=True)
    invoice_number_index.create(engine, checkfirst=True)

    # Create indexes for Customer table
    customer_name_index.create(engine, checkfirst=True)
    customer_email_index.create(engine, checkfirst=True)

    # Create indexes for AuditLog table
    audit_entity_index.create(engine, checkfirst=True)
    audit_action_index.create(engine, checkfirst=True)
    audit_user_index.create(engine, checkfirst=True)
    audit_timestamp_index.create(engine, checkfirst=True)

def drop_indexes(engine):
    """
    Drop all defined indexes from the database
    """
    # Drop indexes for User table
    user_email_index.drop(engine, checkfirst=True)
    user_username_index.drop(engine, checkfirst=True)
    user_role_index.drop(engine, checkfirst=True)

    # Drop indexes for Product table
    product_sku_index.drop(engine, checkfirst=True)
    product_name_index.drop(engine, checkfirst=True)
    product_category_index.drop(engine, checkfirst=True)
    product_stock_index.drop(engine, checkfirst=True)

    # Drop indexes for Invoice table
    invoice_customer_index.drop(engine, checkfirst=True)
    invoice_date_index.drop(engine, checkfirst=True)
    invoice_status_index.drop(engine, checkfirst=True)
    invoice_number_index.drop(engine, checkfirst=True)

    # Drop indexes for Customer table
    customer_name_index.drop(engine, checkfirst=True)
    customer_email_index.drop(engine, checkfirst=True)

    # Drop indexes for AuditLog table
    audit_entity_index.drop(engine, checkfirst=True)
    audit_action_index.drop(engine, checkfirst=True)
    audit_user_index.drop(engine, checkfirst=True)
    audit_timestamp_index.drop(engine, checkfirst=True)