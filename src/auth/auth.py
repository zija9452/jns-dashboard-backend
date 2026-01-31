from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
import os

from ..database.database import get_db
from ..models.user import User
from ..config.settings import settings
from ..middleware.security import session_manager
from ..auth.password import verify_password, get_password_hash

# Use the settings for configuration
SECRET_KEY = settings.access_token_secret_key
REFRESH_SECRET_KEY = settings.refresh_token_secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.refresh_token_expire_days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")  # Kept for compatibility with other parts of auth module
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class OAuth2PasswordCookieBearer(OAuth2PasswordBearer):
    """
    Custom OAuth2 scheme that checks both Authorization header and cookies
    """
    def __init__(self, tokenUrl: str, scheme_name: str = None, scopes: dict = None, auto_error: bool = True):
        super().__init__(tokenUrl=tokenUrl, scheme_name=scheme_name, scopes=scopes, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        # First check Authorization header
        authorization_header = await super().__call__(request)
        if authorization_header:
            return authorization_header

        # If not in header, check for access_token cookie
        cookie_token = request.cookies.get("access_token")
        if cookie_token:
            return cookie_token

        # If auto_error is True, this will raise an exception
        if self.auto_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            return None

# Use the custom scheme that checks both headers and cookies
oauth2_scheme = OAuth2PasswordCookieBearer(tokenUrl="auth/login")

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[str] = None

class RefreshToken(BaseModel):
    refresh_token: str

# Note: verify_password and get_password_hash are imported from ..auth.password

async def authenticate_user(username: str, password: str, db: AsyncSession):
    # This function retrieves the user from the database
    # Using async operations with SQLModel since the db parameter is an AsyncSession
    statement = select(User).where(User.username == username)
    result = await db.execute(statement)
    user = result.scalar_one_or_none()
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    # Add a unique identifier for the refresh token
    import uuid
    to_encode.update({"exp": expire, "jti": str(uuid.uuid4())})
    encoded_jwt = jwt.encode(to_encode, REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str, secret_key: str = SECRET_KEY):
    try:
        payload = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if username is None or user_id is None:
            return None
        token_data = TokenData(username=username, user_id=user_id)
        return token_data
    except JWTError:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = verify_token(token)
    if token_data is None:
        raise credentials_exception

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    # Load user with role relationship for proper RBAC checks
    statement = select(User).options(selectinload(User.role)).where(User.id == token_data.user_id)
    result = await db.execute(statement)
    user = result.scalar_one_or_none()

    if user is None:
        # Check if user was found in token but not in DB - this could indicate account deactivation
        # Raise a clear error that the user exists in the token but not in the database
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user