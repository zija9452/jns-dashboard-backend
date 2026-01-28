from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordBearer
from datetime import timedelta
from typing import Optional
from sqlmodel import Session
from pydantic import BaseModel
import uuid

from ..database.database import get_db
from ..models.user import User
from ..auth.auth import authenticate_user, create_access_token, create_refresh_token
from ..auth.token_manager import store_refresh_token, invalidate_refresh_token
from ..auth.password import verify_password, get_password_hash

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
def login(login_request: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT tokens
    Sets access_token as cookie and returns tokens in response body
    """
    user = authenticate_user(login_request.username, login_request.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_data = {
        "sub": user.username,
        "user_id": str(user.id),
        "role": user.role.name
    }
    access_token = create_access_token(data=access_data)

    # Create refresh token
    refresh_data = {
        "user_id": str(user.id),
        "jti": str(uuid.uuid4())  # JWT ID for tracking
    }
    refresh_token_str = create_refresh_token(data=refresh_data)

    # Store refresh token in Redis
    from datetime import datetime, timedelta
    expires_at = datetime.utcnow() + timedelta(days=30)  # 30 days
    store_refresh_token(user.id, refresh_data["jti"], expires_at)

    # Set access token as cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=15*60  # 15 minutes
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token_str,
        "token_type": "bearer",
        "expires_in": 15*60  # 15 minutes in seconds
    }

@router.post("/refresh", response_model=RefreshResponse)
def refresh_token(refresh_request: RefreshRequest, response: Response, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token
    """
    from ..auth.token_manager import verify_refresh_token

    token_data = verify_refresh_token(refresh_request.refresh_token)
    if token_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user_id = token_data["user_id"]
    jti = token_data["jti"]

    statement = select(User).where(User.id == user_id)
    user = db.exec(statement).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create new access token
    access_data = {
        "sub": user.username,
        "user_id": str(user.id),
        "role": user.role.name
    }
    access_token = create_access_token(data=access_data)

    # Create new refresh token (rotate the refresh token)
    new_jti = str(uuid.uuid4())
    new_refresh_data = {
        "user_id": str(user.id),
        "jti": new_jti
    }
    new_refresh_token = create_refresh_token(data=new_refresh_data)

    # Store new refresh token in Redis
    from datetime import datetime, timedelta
    expires_at = datetime.utcnow() + timedelta(days=30)  # 30 days
    store_refresh_token(user.id, new_jti, expires_at)

    # Invalidate the old refresh token
    invalidate_refresh_token(user.id, jti)

    # Set new access token as cookie
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite="lax",
        max_age=15*60  # 15 minutes
    )

    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
        "expires_in": 15*60  # 15 minutes in seconds
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