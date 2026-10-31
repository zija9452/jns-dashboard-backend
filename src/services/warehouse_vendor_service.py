from sqlmodel import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from typing import List, Optional
from uuid import UUID
from ..models.warehouse_vendor import WarehouseVendor, WarehouseVendorCreate, WarehouseVendorUpdate, vendor_code_for
from ..utils.audit_logger import audit_log

VENDOR_NO_LOCK = 765433  # pg advisory lock id for warehouse vendor number generation


class WarehouseVendorService:
    """
    Service class for handling warehouse vendor-related operations
    """

    @staticmethod
    async def ensure_unique_name(db: AsyncSession, name: str, exclude_id: Optional[UUID] = None):
        """Vendor names are unique like usernames: "Ali", "ali " and "ALI" are the same."""
        name = (name or "").strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vendor name is required")
        statement = select(WarehouseVendor.name).where(func.lower(func.trim(WarehouseVendor.name)) == name.lower())
        if exclude_id:
            statement = statement.where(WarehouseVendor.id != exclude_id)
        existing = (await db.execute(statement.limit(1))).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"A warehouse vendor named '{existing.strip()}' already exists",
            )

    @staticmethod
    async def next_vendor_no(db: AsyncSession) -> int:
        # Transaction-level lock: held until commit, so two creates never get the same number
        await db.execute(select(func.pg_advisory_xact_lock(VENDOR_NO_LOCK)))
        max_no = (await db.execute(select(func.max(WarehouseVendor.vendor_no)))).scalar_one_or_none()
        return (max_no or 0) + 1

    @staticmethod
    async def create_vendor(db: AsyncSession, vendor_create: WarehouseVendorCreate, user_id: str) -> WarehouseVendor:
        """
        Create a new warehouse vendor
        """
        await WarehouseVendorService.ensure_unique_name(db, vendor_create.name)
        vendor_no = await WarehouseVendorService.next_vendor_no(db)
        db_vendor = WarehouseVendor(
            name=vendor_create.name.strip(),
            vendor_no=vendor_no,
            vendor_code=vendor_code_for(vendor_no),
            contacts=vendor_create.contacts,
            branch=vendor_create.branch,
            terms=vendor_create.terms
        )

        db.add(db_vendor)
        await db.commit()
        await db.refresh(db_vendor)

        # Log the action
        await audit_log(
            db=db,
            user_id=user_id,
            entity="WarehouseVendor",
            action="CREATE",
            changes={
                "name": vendor_create.name,
                "contacts": vendor_create.contacts,
                "branch": vendor_create.branch
            }
        )

        return db_vendor

    @staticmethod
    async def get_vendor(db: AsyncSession, vendor_id: UUID) -> Optional[WarehouseVendor]:
        """
        Get a warehouse vendor by ID
        """
        statement = select(WarehouseVendor).where(WarehouseVendor.id == vendor_id)
        result = await db.execute(statement)
        vendor = result.scalar_one_or_none()
        return vendor

    @staticmethod
    async def get_vendors(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[WarehouseVendor]:
        """
        Get a list of warehouse vendors with pagination
        """
        statement = select(WarehouseVendor).offset(skip).limit(limit)
        result = await db.execute(statement)
        vendors = result.scalars().all()
        return vendors

    @staticmethod
    async def update_vendor(db: AsyncSession, vendor_id: UUID, vendor_update: WarehouseVendorUpdate, user_id: str) -> Optional[WarehouseVendor]:
        """
        Update a warehouse vendor
        """
        db_vendor = await WarehouseVendorService.get_vendor(db, vendor_id)
        if not db_vendor:
            return None

        # Prepare update data
        update_data = vendor_update.model_dump(exclude_unset=True)
        if "name" in update_data:
            await WarehouseVendorService.ensure_unique_name(db, update_data["name"], exclude_id=vendor_id)
            update_data["name"] = update_data["name"].strip()

        # Update the vendor
        for field, value in update_data.items():
            setattr(db_vendor, field, value)

        await db.commit()
        await db.refresh(db_vendor)

        # Log the action
        await audit_log(
            db=db,
            user_id=user_id,
            entity="WarehouseVendor",
            action="UPDATE",
            changes=update_data
        )

        return db_vendor

    @staticmethod
    async def delete_vendor(db: AsyncSession, vendor_id: UUID, user_id: str) -> bool:
        """
        Delete a warehouse vendor
        """
        db_vendor = await WarehouseVendorService.get_vendor(db, vendor_id)
        if not db_vendor:
            return False

        try:
            await db.delete(db_vendor)
            await db.commit()

            # Log the action
            await audit_log(
                db=db,
                user_id=user_id,
                entity="WarehouseVendor",
                action="DELETE",
                changes={"id": str(vendor_id)}
            )

            return True
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete warehouse vendor because it has associated records. Please delete those first."
            )
        except Exception as e:
            await db.rollback()
            raise e
