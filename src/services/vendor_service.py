from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from ..models.vendor import Vendor, VendorCreate, VendorUpdate
from ..utils.audit_logger import audit_log

class VendorService:
    """
    Service class for handling vendor-related operations
    """

    @staticmethod
    async def create_vendor(db: AsyncSession, vendor_create: VendorCreate, user_id: str) -> Vendor:
        """
        Create a new vendor
        """
        db_vendor = Vendor(
            name=vendor_create.name,
            contacts=vendor_create.contacts,
            terms=vendor_create.terms
        )

        db.add(db_vendor)
        await db.commit()
        await db.refresh(db_vendor)

        # Log the action
        await audit_log(
            db=db,
            user_id=user_id,
            entity="Vendor",
            action="CREATE",
            changes={
                "name": vendor_create.name,
                "contacts": vendor_create.contacts
            }
        )

        return db_vendor

    @staticmethod
    async def get_vendor(db: AsyncSession, vendor_id: UUID) -> Optional[Vendor]:
        """
        Get a vendor by ID
        """
        statement = select(Vendor).where(Vendor.id == vendor_id)
        result = await db.execute(statement)
        vendor = result.scalar_one_or_none()
        return vendor

    @staticmethod
    async def get_vendors(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Vendor]:
        """
        Get a list of vendors with pagination
        """
        statement = select(Vendor).offset(skip).limit(limit)
        result = await db.execute(statement)
        vendors = result.scalars().all()
        return vendors

    @staticmethod
    async def update_vendor(db: AsyncSession, vendor_id: UUID, vendor_update: VendorUpdate, user_id: str) -> Optional[Vendor]:
        """
        Update a vendor
        """
        db_vendor = await VendorService.get_vendor(db, vendor_id)
        if not db_vendor:
            return None

        # Prepare update data
        update_data = vendor_update.model_dump(exclude_unset=True)

        # Update the vendor
        for field, value in update_data.items():
            setattr(db_vendor, field, value)

        await db.commit()
        await db.refresh(db_vendor)

        # Log the action
        await audit_log(
            db=db,
            user_id=user_id,
            entity="Vendor",
            action="UPDATE",
            changes=update_data
        )

        return db_vendor

    @staticmethod
    async def delete_vendor(db: AsyncSession, vendor_id: UUID, user_id: str) -> bool:
        """
        Delete a vendor
        """
        db_vendor = await VendorService.get_vendor(db, vendor_id)
        if not db_vendor:
            return False

        await db.delete(db_vendor)
        await db.commit()

        # Log the action
        await audit_log(
            db=db,
            user_id=user_id,
            entity="Vendor",
            action="DELETE",
            changes={"id": str(vendor_id)}
        )

        return True