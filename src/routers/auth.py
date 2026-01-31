from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from pydantic import BaseModel
import uuid
from jose import jwt
from passlib.context import CryptContext

from ..database.database import get_db
from ..models.user import User
from ..config.settings import settings
from ..middleware.security import session_manager

# Configuration from settings
SECRET_KEY = settings.access_token_secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Remove local function, using the one from auth module
# from ..auth.auth import create_refresh_token

router = APIRouter()

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshRequest(BaseModel):
    refresh_token: str

class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

@router.post("/login", response_model=TokenResponse)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), response: Response = None, db: AsyncSession = Depends(get_db)):
    """
    Authenticate user and return JWT tokens
    Sets access_token as cookie and returns tokens in response body
    """
    from ..auth.auth import authenticate_user

    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_data = {"sub": user.username, "user_id": str(user.id)}
    access_token = create_access_token(data=access_data, expires_delta=access_token_expires)

    # Create refresh token
    from ..auth.auth import create_refresh_token
    refresh_token_expires = timedelta(days=30)  # 30 days
    refresh_data = {"user_id": str(user.id)}
    refresh_token = create_refresh_token(data=refresh_data, expires_delta=refresh_token_expires)

    # Store refresh token (placeholder - would implement actual storage)
    # store_refresh_token(user.id, refresh_token, timedelta(days=30))

    # Set cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=1800  # 30 minutes
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": 1800
    }

@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token_endpoint(refresh_request: RefreshRequest, response: Response, db: AsyncSession = Depends(get_db)):
    """
    Refresh access token using refresh token
    """
    from ..auth.token_manager import verify_refresh_token, is_refresh_token_valid, store_refresh_token, invalidate_refresh_token

    token_data = verify_refresh_token(refresh_request.refresh_token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user_id = token_data["user_id"]

    statement = select(User).where(User.id == user_id)
    result = await db.execute(statement)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new access token
    access_data = {
        "sub": user.username,
        "user_id": str(user.id)
    }
    access_token = create_access_token(data=access_data)

    # Create new refresh token (rotate the refresh token)
    from ..auth.auth import create_refresh_token
    new_refresh_data = {
        "user_id": str(user.id)
    }
    new_refresh_token = create_refresh_token(data=new_refresh_data)

    # Set new access token as cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=1800  # 30 minutes
    )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": 1800  # 30 minutes in seconds
    }

@router.post("/logout")
def logout(response: Response):
    """
    Revoke refresh token and logout user
    Clears the access token cookie
    """
    # Clear the access token cookie
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        max_age=0,
        expires=0
    )

    # Note: In a real implementation, you would also need to invalidate the refresh token
    # which would require passing the refresh token in the request
    return {"message": "Successfully logged out"}

# Import statement needed for the select function
from sqlmodel import select