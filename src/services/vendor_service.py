from sqlmodel import Session, select
from typing import List, Optional
from uuid import UUID
from ..models.vendor import Vendor, VendorCreate, VendorUpdate
from ..utils.audit_logger import audit_log

class VendorService:
    """
    Service class for handling vendor-related operations
    """

    @staticmethod
    async def create_vendor(db: Session, vendor_create: VendorCreate) -> Vendor:
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
            user_id="",  # Need to pass actual user ID from context
            entity="Vendor",
            action="CREATE",
            changes={
                "name": vendor_create.name,
                "contacts": vendor_create.contacts
            }
        )

        return db_vendor

    @staticmethod
    async def get_vendor(db: Session, vendor_id: UUID) -> Optional[Vendor]:
        """
        Get a vendor by ID
        """
        statement = select(Vendor).where(Vendor.id == vendor_id)
        vendor = db.exec(statement).first()
        return vendor

    @staticmethod
    async def get_vendors(db: Session, skip: int = 0, limit: int = 100) -> List[Vendor]:
        """
        Get a list of vendors with pagination
        """
        statement = select(Vendor).offset(skip).limit(limit)
        vendors = db.exec(statement).all()
        return vendors

    @staticmethod
    async def update_vendor(db: Session, vendor_id: UUID, vendor_update: VendorUpdate) -> Optional[Vendor]:
        """
        Update a vendor
        """
        db_vendor = await VendorService.get_vendor(db, vendor_id)
        if not db_vendor:
            return None

        # Prepare update data
        update_data = vendor_update.dict(exclude_unset=True)

        # Update the vendor
        for field, value in update_data.items():
            setattr(db_vendor, field, value)

        await db.commit()
        await db.refresh(db_vendor)

        # Log the action
        await audit_log(
            db=db,
            user_id="",  # Need to pass actual user ID from context
            entity="Vendor",
            action="UPDATE",
            changes=update_data
        )

        return db_vendor

    @staticmethod
    async def delete_vendor(db: Session, vendor_id: UUID) -> bool:
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
            user_id="",  # Need to pass actual user ID from context
            entity="Vendor",
            action="DELETE",
            changes={"id": str(vendor_id)}
        )

        return True