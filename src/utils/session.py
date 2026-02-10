import secrets
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from ..models.session import UserSession
from ..models.user import User


def generate_session_token():
    """Generate a secure random session token"""
    return secrets.token_urlsafe(32)


async def create_session(user_id: str, db: AsyncSession, ip_address: str = None,
                        user_agent: str = None, company_id: str = None,
                        biometric_verified: bool = False):
    """Create a new user session"""
    session_token = generate_session_token()
    expires_at = datetime.now() + timedelta(hours=24)  # 24-hour session

    session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at,
        ip_address=ip_address,
        user_agent=user_agent,
        company_id=company_id,
        biometric_verified=biometric_verified
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return session


async def get_session_by_token(session_token: str, db: AsyncSession):
    """Get active session by token"""
    statement = select(UserSession).where(
        UserSession.session_token == session_token,
        UserSession.is_active == True,
        UserSession.expires_at > datetime.now()
    )
    result = await db.execute(statement)
    return result.scalar_one_or_none()


async def invalidate_session(session_token: str, db: AsyncSession):
    """Invalidate a session (logout)"""
    session = await get_session_by_token(session_token, db)
    if session:
        session.is_active = False
        await db.commit()
        return True
    return False


async def cleanup_expired_sessions(db: AsyncSession):
    """Remove expired sessions from database"""
    statement = select(UserSession).where(UserSession.expires_at < datetime.now())
    result = await db.execute(statement)
    expired_sessions = result.scalars().all()

    for session in expired_sessions:
        await db.delete(session)

    await db.commit()