from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
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
    def calculate_check_digit(barcode: str) -> int:
        """
        Calculate EAN-13 check digit
        """
        sum_val = 0
        for i, digit in enumerate(barcode):
            sum_val += int(digit) * (1 if i % 2 == 0 else 3)
        return (10 - (sum_val % 10)) % 10

    @staticmethod
    async def generate_unique_barcode(db: AsyncSession) -> str:
        """
        Generate a unique barcode using auto-increment approach
        Format: 690 + 5 digit sequence + 1 check digit = 9 digits

        Real-world best practices:
        - Sequential numbering for easy tracking
        - Check digit algorithm for error detection
        - Prefix 690 is a standard GS1 prefix
        - Unique constraint in database ensures no duplicates
        """
        from sqlalchemy import text

        # Get the last product with highest barcode using raw SQL to avoid recursion
        try:
            result = await db.execute(
                text("SELECT barcode FROM products WHERE barcode IS NOT NULL AND barcode != '' ORDER BY barcode DESC LIMIT 1")
            )
            row = result.first()
            last_barcode = row[0] if row else None
        except Exception as e:
            # Fallback: use timestamp-based approach
            import time
            last_barcode = None

        if not last_barcode:
            # Start from 69000000 (8 digits without check digit)
            base_code = "69000000"
        else:
            # Handle 9-digit barcode format: 690 + 5 digits + check digit
            if last_barcode.startswith('690') and len(last_barcode) == 9:
                # Get the 5-digit sequence number
                last_num_str = last_barcode[3:-1]  # Remove prefix and check digit
                try:
                    last_num = int(last_num_str)
                    next_num = last_num + 1
                    base_code = f"690{next_num:05d}"
                except ValueError as e:
                    import time
                    base_code = f"690{int(time.time() * 1000) % 100000:05d}"
            else:
                # Start fresh if format doesn't match
                base_code = "69000000"

        # Calculate check digit (8 digits input for 9-digit barcode)
        check_digit = ProductService.calculate_check_digit(base_code)
        barcode = f"{base_code}{check_digit}"

        return barcode

    @staticmethod
    async def create_product(db: AsyncSession, product_create: ProductCreate, user_id: str = "") -> Product:
        """
        Create a new product
        """
        db_product = Product(
            sku=product_create.sku,
            name=product_create.name,
            unit_price=product_create.unit_price,
            cost_price=product_create.cost_price,
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
            user_id=user_id,
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
    async def get_product(db: AsyncSession, product_id: UUID) -> Optional[Product]:
        """
        Get a product by ID
        """
        statement = select(Product).where(Product.id == product_id)
        result = await db.execute(statement)
        product = result.scalar_one_or_none()
        return product

    @staticmethod
    async def get_product_by_sku(db: AsyncSession, sku: str) -> Optional[Product]:
        """
        Get a product by SKU
        """
        statement = select(Product).where(Product.sku == sku)
        result = await db.execute(statement)
        product = result.scalar_one_or_none()
        return product

    @staticmethod
    async def get_products(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Product]:
        """
        Get a list of products with pagination
        """
        statement = select(Product).offset(skip).limit(limit)
        result = await db.execute(statement)
        products = result.scalars().all()
        return products

    @staticmethod
    async def update_product(db: AsyncSession, product_id: UUID, product_update: ProductUpdate, user_id: str = "") -> Optional[Product]:
        """
        Update a product
        """
        db_product = await ProductService.get_product(db, product_id)
        if not db_product:
            return None

        # Prepare update data
        update_data = product_update.model_dump(exclude_unset=True)

        # Update the product with special handling for Decimal fields
        for field, value in update_data.items():
            if value is not None:  # Only update non-None values
                # Handle Decimal fields specifically to ensure proper type
                if field in ['unit_price', 'cost_price', 'discount']:
                    if isinstance(value, (int, float)):
                        from decimal import Decimal
                        setattr(db_product, field, Decimal(str(value)))
                    elif isinstance(value, str):
                        from decimal import Decimal
                        setattr(db_product, field, Decimal(value))
                    else:
                        setattr(db_product, field, value)
                else:
                    setattr(db_product, field, value)

        await db.commit()
        await db.refresh(db_product)

        # Log the action
        await audit_log(
            db=db,
            user_id=user_id,
            entity="Product",
            action="UPDATE",
            changes=update_data
        )

        return db_product

    @staticmethod
    async def delete_product(db: AsyncSession, product_id: UUID, user_id: str = "") -> bool:
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
            user_id=user_id,
            entity="Product",
            action="DELETE",
            changes={"id": str(product_id)}
        )

        return True

    @staticmethod
    async def adjust_stock(db: AsyncSession, product_id: UUID, adjustment: int, user_id: str = "") -> Optional[Product]:
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
            user_id=user_id,
            entity="Product",
            action="UPDATE",
            changes={"stock_level": db_product.stock_level, "adjustment": adjustment}
        )

        return db_product