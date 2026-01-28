from sqlmodel import Session, select
from typing import List, Optional
from uuid import UUID
from decimal import Decimal
from ..models.product import Product, ProductCreate, ProductUpdate
from ..utils.audit_logger import audit_log

class ProductService:
    """
    Service class for handling product-related operations
    """

    @staticmethod
    async def create_product(db: Session, product_create: ProductCreate) -> Product:
        """
        Create a new product
        """
        db_product = Product(
            sku=product_create.sku,
            name=product_create.name,
            desc=product_create.desc,
            unit_price=product_create.unit_price,
            cost_price=product_create.cost_price,
            tax_rate=product_create.tax_rate,
            vendor_id=product_create.vendor_id,
            stock_level=product_create.stock_level,
            attributes=product_create.attributes,
            barcode=product_create.barcode,
            discount=product_create.discount,
            category=product_create.category,
            branch=product_create.branch,
            limited_qty=product_create.limited_qty,
            brand_action=product_create.brand_action
        )

        db.add(db_product)
        await db.commit()
        await db.refresh(db_product)

        # Log the action
        await audit_log(
            db=db,
            user_id="",  # Need to pass actual user ID from context
            entity="Product",
            action="CREATE",
            changes={
                "sku": product_create.sku,
                "name": product_create.name,
                "unit_price": str(product_create.unit_price),
                "stock_level": product_create.stock_level
            }
        )

        return db_product

    @staticmethod
    async def get_product(db: Session, product_id: UUID) -> Optional[Product]:
        """
        Get a product by ID
        """
        statement = select(Product).where(Product.id == product_id)
        product = db.exec(statement).first()
        return product

    @staticmethod
    async def get_product_by_sku(db: Session, sku: str) -> Optional[Product]:
        """
        Get a product by SKU
        """
        statement = select(Product).where(Product.sku == sku)
        product = db.exec(statement).first()
        return product

    @staticmethod
    async def get_products(db: Session, skip: int = 0, limit: int = 100) -> List[Product]:
        """
        Get a list of products with pagination
        """
        statement = select(Product).offset(skip).limit(limit)
        products = db.exec(statement).all()
        return products

    @staticmethod
    async def update_product(db: Session, product_id: UUID, product_update: ProductUpdate) -> Optional[Product]:
        """
        Update a product
        """
        db_product = await ProductService.get_product(db, product_id)
        if not db_product:
            return None

        # Prepare update data
        update_data = product_update.dict(exclude_unset=True)

        # Update the product
        for field, value in update_data.items():
            setattr(db_product, field, value)

        await db.commit()
        await db.refresh(db_product)

        # Log the action
        await audit_log(
            db=db,
            user_id="",  # Need to pass actual user ID from context
            entity="Product",
            action="UPDATE",
            changes=update_data
        )

        return db_product

    @staticmethod
    async def delete_product(db: Session, product_id: UUID) -> bool:
        """
        Delete a product
        """
        db_product = await ProductService.get_product(db, product_id)
        if not db_product:
            return False

        await db.delete(db_product)
        await db.commit()

        # Log the action
        await audit_log(
            db=db,
            user_id="",  # Need to pass actual user ID from context
            entity="Product",
            action="DELETE",
            changes={"id": str(product_id)}
        )

        return True

    @staticmethod
    async def adjust_stock(db: Session, product_id: UUID, adjustment: int) -> Optional[Product]:
        """
        Adjust product stock level
        """
        db_product = await ProductService.get_product(db, product_id)
        if not db_product:
            return None

        # Update stock level
        db_product.stock_level += adjustment

        await db.commit()
        await db.refresh(db_product)

        # Log the action
        await audit_log(
            db=db,
            user_id="",  # Need to pass actual user ID from context
            entity="Product",
            action="UPDATE",
            changes={"stock_level": db_product.stock_level, "adjustment": adjustment}
        )

        return db_product