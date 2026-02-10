from datetime import datetime
from decimal import Decimal
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
import json
from ..models.audit_log import AuditLog
from ..models.user import User


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

class AuditLogger:
    """
    Utility class for creating audit logs
    """

    @staticmethod
    async def log_action(
        db: AsyncSession,
        user_id: str,
        entity: str,
        action: str,
        changes: Dict[str, Any] = None,
        entity_id: str = None
    ):
        """
        Create an audit log entry

        Args:
            db: Database session
            user_id: ID of the user performing the action
            entity: Name of the entity being acted upon (e.g., 'User', 'Product', 'Invoice')
            action: Type of action (CREATE, UPDATE, DELETE, ACCESS)
            changes: Dictionary of changes made (for UPDATE actions)
            entity_id: ID of the entity being acted upon (optional)
        """
        audit_entry = AuditLog(
            entity=entity,
            action=action,
            user_id=user_id,
            changes=json.dumps(changes, cls=DecimalEncoder) if changes else "{}",
            timestamp=datetime.utcnow()
        )

        db.add(audit_entry)
        await db.commit()
        await db.refresh(audit_entry)

        return audit_entry

# Convenience function for use throughout the application
async def audit_log(
    db: AsyncSession,
    user_id: str,
    entity: str,
    action: str,
    changes: Dict[str, Any] = None,
    entity_id: str = None
):
    """
    Convenience function to create audit logs

    Args:
        db: Database session
        user_id: ID of the user performing the action
        entity: Name of the entity being acted upon
        action: Type of action (CREATE, UPDATE, DELETE, ACCESS)
        changes: Dictionary of changes made
        entity_id: ID of the entity being acted upon (optional)
    """
    return await AuditLogger.log_action(db, user_id, entity, action, changes, entity_id)