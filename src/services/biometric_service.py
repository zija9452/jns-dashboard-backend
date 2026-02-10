import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.user import User
from ..models.role import Role


class BiometricService:
    @staticmethod
    async def register_employee_biometric(user_id: str, thumb_data: str,
                                        company_id: str, db: AsyncSession):
        """
        Register thumb scan for employee user
        """
        # Hash the thumb data for secure storage
        thumb_hash = hashlib.sha256(thumb_data.encode()).hexdigest()

        # Update user with biometric data
        statement = select(User).where(User.id == user_id)
        result = await db.execute(statement)
        user = result.scalar_one_or_none()

        if user:
            user.biometric_hash = thumb_hash
            user.company_id = company_id
            user.is_biometric_enabled = True
            await db.commit()
            return True
        return False

    @staticmethod
    async def verify_employee_biometric(thumb_data: str, company_id: str,
                                      db: AsyncSession):
        """
        Verify employee thumb scan against stored hash
        """
        thumb_hash = hashlib.sha256(thumb_data.encode()).hexdigest()

        # Get employee role ID
        role_statement = select(Role).where(Role.name == "employee")
        role_result = await db.execute(role_statement)
        employee_role = role_result.scalar_one_or_none()
        
        if not employee_role:
            return None

        statement = select(User).where(
            User.biometric_hash == thumb_hash,
            User.company_id == company_id,
            User.is_active == True,
            User.is_biometric_enabled == True,
            User.role_id == employee_role.id  # Only for employee users
        )

        result = await db.execute(statement)
        user = result.scalar_one_or_none()
        return user