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

    # pg advisory lock ids (per branch DB) for auto barcodes
    BARCODE_LOCK = 765437
    MAX_SEQ = 99999  # 5-digit sequence: prefix + 00000..99999 + check digit

    @staticmethod
    def make_barcode(prefix: str, seq: int) -> str:
        base = f"{prefix}{seq:05d}"
        return f"{base}{ProductService.calculate_check_digit(base)}"

    @staticmethod
    def auto_seq(barcode: str, prefix: str) -> Optional[int]:
        """The sequence of an auto barcode of this prefix (prefix + 5 digits + right check
        digit), else None (typed / imported barcode)."""
        if not barcode or len(barcode) != len(prefix) + 6 or not barcode.isdigit() or not barcode.startswith(prefix):
            return None
        seq = int(barcode[len(prefix):len(prefix) + 5])
        return seq if ProductService.make_barcode(prefix, seq) == barcode else None

    @staticmethod
    async def barcode_taken(db: AsyncSession, barcode: str) -> bool:
        from ..models.batch import ProductBatch
        if (await db.execute(select(Product.id).where(Product.barcode == barcode).limit(1))).first():
            return True
        return (await db.execute(select(ProductBatch.id).where(ProductBatch.barcode == barcode).limit(1))).first() is not None

    @staticmethod
    async def _last_seq(db: AsyncSession, prefix: str) -> int:
        from sqlalchemy import text
        row = (await db.execute(text("SELECT last_seq FROM barcode_counters WHERE prefix = :p"), {"p": prefix})).first()
        if row:
            return row[0]
        # No counter yet (migration not run): the highest auto barcode, as before
        row = (await db.execute(text("""
            SELECT COALESCE(MAX(SUBSTRING(barcode FROM 4 FOR 5)::int), -1) FROM products
            WHERE barcode ~ :pattern AND SUBSTRING(barcode FROM 4 FOR 5)::int < 10000
        """), {"pattern": f"^{prefix}[0-9]{{6}}$"})).first()
        return row[0] if row else -1

    @staticmethod
    async def generate_unique_barcode(db: AsyncSession) -> str:
        """
        Next free auto barcode: branch prefix (Light House 690, Karim Abad 691) + 5 digit
        sequence + 1 check digit = 9 digits. The sequence comes from barcode_counters, which
        only moves forward when a product is saved (reserve_barcode) - opening the form
        reserves nothing (no numbers wasted), a deleted product's barcode is never given
        again, and barcodes already taken (old imported ones) are skipped.
        """
        from ..config.branches import this_branch
        prefix = this_branch().barcode_prefix
        seq = await ProductService._last_seq(db, prefix) + 1
        while seq <= ProductService.MAX_SEQ:
            barcode = ProductService.make_barcode(prefix, seq)
            if not await ProductService.barcode_taken(db, barcode):
                return barcode
            seq += 1
        raise Exception(f"All {prefix} barcodes are used")

    @staticmethod
    async def lock_barcodes(db: AsyncSession):
        """Held until this transaction commits: two saves never take one barcode."""
        from sqlalchemy import func as sa_func
        await db.execute(select(sa_func.pg_advisory_xact_lock(ProductService.BARCODE_LOCK)))

    @staticmethod
    async def reserve_barcode(db: AsyncSession, barcode: str):
        """A product with this barcode is being saved: move the counter past it (if it is an
        auto barcode of this branch). Call after lock_barcodes; the caller commits."""
        from sqlalchemy import text
        from ..config.branches import this_branch
        prefix = this_branch().barcode_prefix
        seq = ProductService.auto_seq(barcode, prefix)
        if seq is None:
            return
        await db.execute(text("""
            INSERT INTO barcode_counters (prefix, last_seq, updated_at) VALUES (:p, :s, now())
            ON CONFLICT (prefix) DO UPDATE SET last_seq = GREATEST(barcode_counters.last_seq, EXCLUDED.last_seq),
                                               updated_at = now()
        """), {"p": prefix, "s": seq})

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
            brand_action=product_create.brand_action,
            is_warehouse_product=product_create.is_warehouse_product,
            article_no=product_create.article_no,
            warehouse_stock=product_create.warehouse_stock,
            warehouse_cost=product_create.warehouse_cost,
            warehouse_limited_qty=product_create.warehouse_limited_qty
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
    async def bulk_create_products(db: AsyncSession, products_create: List[ProductCreate], user_id: str = "") -> List[Product]:
        """
        Create multiple products in a batch
        """
        # Collect all SKUs, names, and barcodes to check against DB in bulk
        skus = [p.sku for p in products_create]
        names = [p.name for p in products_create]
        barcodes = [p.barcode for p in products_create if p.barcode]

        # Check for duplicates in the batch itself
        if len(skus) != len(set(skus)):
            raise Exception("Duplicate SKUs found in the input list")
        if len(names) != len(set(names)):
            raise Exception("Duplicate product names found in the input list")
        if len(barcodes) != len(set(barcodes)):
            raise Exception("Duplicate barcodes found in the input list")

        # Check for existing SKUs in DB
        sku_stmt = select(Product).where(Product.sku.in_(skus))
        sku_result = await db.execute(sku_stmt)
        existing_skus = sku_result.scalars().all()
        if existing_skus:
            sku_list = ", ".join([p.sku for p in existing_skus])
            raise Exception(f"Existing SKUs found in DB: {sku_list}")

        # Check for existing Names in DB
        name_stmt = select(Product).where(Product.name.in_(names))
        name_result = await db.execute(name_stmt)
        existing_names = name_result.scalars().all()
        if existing_names:
            name_list = ", ".join([p.name for p in existing_names])
            raise Exception(f"Existing product names found in DB: {name_list}")

        # Check for existing Barcodes in DB
        if barcodes:
            barcode_stmt = select(Product).where(Product.barcode.in_(barcodes))
            barcode_result = await db.execute(barcode_stmt)
            existing_barcodes = barcode_result.scalars().all()
            if existing_barcodes:
                barcode_list = ", ".join([p.barcode for p in existing_barcodes])
                raise Exception(f"Existing barcodes found in DB: {barcode_list}")

        db_products = []
        for p in products_create:
            db_product = Product(
                sku=p.sku,
                name=p.name,
                unit_price=p.unit_price,
                cost_price=p.cost_price,
                stock_level=p.stock_level,
                attributes=p.attributes,
                barcode=p.barcode,
                discount=p.discount,
                category=p.category,
                branch=p.branch,
                limited_qty=p.limited_qty,
                brand_action=p.brand_action,
                is_warehouse_product=p.is_warehouse_product,
                article_no=p.article_no,
                warehouse_stock=p.warehouse_stock,
                warehouse_cost=p.warehouse_cost,
                warehouse_limited_qty=p.warehouse_limited_qty
            )
            db.add(db_product)
            db_products.append(db_product)

        await db.commit()
        
        # Refresh all products to get their IDs
        for p in db_products:
            await db.refresh(p)

        # Log the action (bulk summary)
        await audit_log(
            db=db,
            user_id=user_id,
            entity="Product",
            action="BULK_CREATE",
            changes={
                "count": len(products_create),
                "skus": skus[:10]  # Log first 10 SKUs for brevity
            }
        )

        return db_products

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

        # Delete related stock_entries first to avoid foreign key constraint error
        from ..models.stock_entry import StockEntry
        from sqlmodel import delete
        
        # Delete all stock entries for this product
        delete_stmt = delete(StockEntry).where(StockEntry.product_id == product_id)
        await db.execute(delete_stmt)
        
        # Commit stock entries deletion before deleting product
        await db.commit()
        
        # Now delete the product
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