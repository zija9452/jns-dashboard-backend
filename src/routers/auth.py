from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta, datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from pydantic import BaseModel
import uuid
from jose import jwt
from passlib.context import CryptContext
import hashlib
import os

from ..database.database import get_db
from ..models.user import User
from ..config.settings import settings
from ..middleware.security import session_manager
from ..utils.session import create_session, invalidate_session
from ..services.biometric_service import BiometricService
from ..auth.session_auth import get_current_user_from_session
from ..utils.rate_limiter import auth_rate_limiter, get_client_ip
from ..config.branches import BRANCHES, DEFAULT_BRANCH, BRANCH_COOKIE, current_branch

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
    role: str = None  # Optional role parameter for filtering or validation
    branch: Optional[str] = None  # Branch code from the login dropdown (default: Light House)

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

class BiometricLoginRequest(BaseModel):
    thumb_data: str
    company_id: str

@router.post("/traditional-login", response_model=TokenResponse)
async def traditional_login(
    response: Response,
    login_request: LoginRequest,
    db: AsyncSession = Depends(get_db),
    request: Request = None
):
    """
    Traditional login for admin/cashier users
    """
    from sqlalchemy import select
    from ..auth.auth import authenticate_user

    # Get client IP for rate limiting
    client_ip = get_client_ip(request) if request else "unknown"

    # Security: Check if credentials were passed in URL parameters (which is insecure)
    if request and request.query_params:
        if 'username' in request.query_params or 'password' in request.query_params:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credentials must be sent in request body, not URL parameters"
            )

    # Re-fetch user with role joined to avoid lazy loading issues
    user = await authenticate_user(login_request.username, login_request.password, db)
    if not user:
        # Record failed login attempt
        if auth_rate_limiter.record_failed_login(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Account temporarily locked."
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Record successful login to reset failed attempts counter
    auth_rate_limiter.record_successful_login(client_ip)

    # Re-query user with role joined to avoid lazy loading issues in async context
    statement = select(User).options(selectinload(User.role)).where(User.id == user.id)
    result = await db.execute(statement)
    user_with_role = result.scalar_one_or_none()
    
    if not user_with_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Check if user has biometric enabled - if so, password login should be disabled
    if user_with_role.is_biometric_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Biometric authentication required. Password login disabled."
        )

    # Check if user is employee (should not use password login in biometric-enabled system)
    if user_with_role.role.name == "employee" and user_with_role.is_biometric_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Employee users must use biometric authentication"
        )

    # If a role was specified in the login request, validate that it matches the user's role (case-insensitive)
    if login_request.role and user_with_role.role.name.lower() != login_request.role.lower():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User role does not match selected role. Expected: {login_request.role}, Actual: {user_with_role.role.name}"
        )

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_data = {"sub": user_with_role.username, "user_id": str(user_with_role.id)}
    access_token = create_access_token(data=access_data, expires_delta=access_token_expires)

    # Create refresh token
    from ..auth.auth import create_refresh_token
    refresh_token_expires = timedelta(days=30)  # 30 days
    refresh_data = {"user_id": str(user_with_role.id)}
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


@router.get("/branches")
async def list_branches():
    """Public list of available branches for the login dropdown (no DB access)."""
    from ..database.database import session_factories
    from ..config.branches import BRANCHES
    return [
        {"code": b.code, "name": b.name}
        for code, b in BRANCHES.items()
        if code in session_factories
    ]


def _set_branch_cookie(response: Response, branch_code: str):
    """Same lifetime/flags as the session_token cookie it travels with."""
    response.set_cookie(
        key=BRANCH_COOKIE,
        value=branch_code,
        httponly=True,
        secure=os.getenv("ENVIRONMENT", "development") == "production",
        samesite="lax",
        max_age=36000,  # 10 hours, same as session_token
        path="/"
    )


@router.post("/login")
async def session_login(
    response: Response,
    login_request: LoginRequest,
    request: Request = None
):
    """
    Session-based login. The branch chosen on the login page decides which
    database the credentials are checked against and the session is stored in.
    """
    from ..database.database import session_factories

    branch_code = login_request.branch or DEFAULT_BRANCH
    if branch_code not in BRANCHES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown branch")
    if branch_code not in session_factories:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Branch is not available")

    current_branch.set(branch_code)
    async with session_factories[branch_code]() as db:
        result = await _session_login(response, login_request, db, request)

    _set_branch_cookie(response, branch_code)
    result["branch"] = {"code": branch_code, "name": BRANCHES[branch_code].name}
    return result


async def _session_login(
    response: Response,
    login_request: LoginRequest,
    db: AsyncSession,
    request: Request = None
):
    """
    Session-based login for admin/cashier users (traditional login)
    """
    from sqlalchemy import select
    from ..auth.auth import authenticate_user

    # Get client IP for rate limiting
    client_ip = get_client_ip(request) if request else "unknown"

    # Security: Check if credentials were passed in URL parameters (which is insecure)
    if request and request.query_params:
        if 'username' in request.query_params or 'password' in request.query_params:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Credentials must be sent in request body, not URL parameters"
            )

    # Re-fetch user with role loaded to avoid lazy loading issues in async context
    user = await authenticate_user(login_request.username, login_request.password, db)
    if not user:
        # Record failed login attempt
        if auth_rate_limiter.record_failed_login(client_ip):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed login attempts. Account temporarily locked."
            )
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Record successful login to reset failed attempts counter
    auth_rate_limiter.record_successful_login(client_ip)

    # Re-query user with role joined to avoid lazy loading issues
    statement = select(User).options(selectinload(User.role)).where(User.id == user.id)
    result = await db.execute(statement)
    user_with_role = result.scalar_one_or_none()
    
    if not user_with_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Check if user has biometric enabled - if so, password login should be disabled
    if user_with_role.is_biometric_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Biometric authentication required. Password login disabled."
        )

    # Check if user is employee (should not use password login in biometric-enabled system)
    if user_with_role.role.name == "employee" and user_with_role.is_biometric_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Employee users must use biometric authentication"
        )

    # If a role was specified in the login request, validate that it matches the user's role (case-insensitive)
    if login_request.role and user_with_role.role.name.lower() != login_request.role.lower():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"User role does not match selected role. Expected: {login_request.role}, Actual: {user_with_role.role.name}"
        )

    # Create session
    ip_address = request.client.host if request else None
    user_agent = request.headers.get("user-agent") if request else None

    session = await create_session(
        user_id=str(user_with_role.id),
        db=db,
        ip_address=ip_address,
        user_agent=user_agent,
        company_id=str(user_with_role.company_id) if user_with_role.company_id else None,
        biometric_verified=False  # Traditional login
    )

    # Set session cookie - secure flag based on environment
    is_production = os.getenv("ENVIRONMENT", "development") == "production"
    
    response.set_cookie(
        key="session_token",
        value=session.session_token,
        httponly=True,
        secure=is_production,  # True only in production
        samesite="lax",
        max_age=36000,  # 10 hours (36000 seconds)
        path="/"
    )

    return {
        "message": "Login successful",
        "user": {
            "id": str(user_with_role.id),
            "username": user_with_role.username,
            "role": user_with_role.role.name,
            "company_id": str(user_with_role.company_id) if user_with_role.company_id else None
        }
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


@router.post("/biometric/thumb-login")
async def biometric_thumb_login(
    request: Request,
    response: Response,
    thumb_data: str,  # Thumb scan data from device
    company_id: str,  # Company ID from device or form
    db: AsyncSession = Depends(get_db)
):
    """
    Biometric login for employee users only
    """
    # Verify biometric data
    user = await BiometricService.verify_employee_biometric(
        thumb_data=thumb_data,
        company_id=company_id,
        db=db
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid thumb scan or company mismatch"
        )

    if user.role.name != "employee":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Biometric authentication only available for employee users"
        )

    # Create session with biometric verification flag
    ip_address = request.client.host
    user_agent = request.headers.get("user-agent")

    session = await create_session(
        user_id=str(user.id),
        db=db,
        ip_address=ip_address,
        user_agent=user_agent,
        company_id=company_id,
        biometric_verified=True  # Biometric login
    )

    # Set session cookie
    response.set_cookie(
        key="session_token",
        value=session.session_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=86400
    )

    return {
        "message": "Biometric login successful",
        "user": {
            "id": str(user.id),
            "username": user.username,
            "role": user.role.name,
            "company_id": str(user.company_id)
        }
    }

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user_from_session),  # Using session-based auth
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user and invalidate session
    """
    # Get session token from request cookies
    session_token = request.cookies.get("session_token")

    if session_token:
        await invalidate_session(session_token, db)

    # Clear session cookie
    response.set_cookie(
        key="session_token",
        value="",
        httponly=True,
        secure=True,
        samesite="lax",
        expires=0
    )

    # Clear branch cookie
    response.set_cookie(
        key=BRANCH_COOKIE,
        value="",
        httponly=True,
        secure=True,
        samesite="lax",
        expires=0,
        path="/"
    )

    # Also clear the old JWT cookie for backward compatibility
    response.set_cookie(
        key="access_token",
        value="",
        httponly=True,
        max_age=0,
        expires=0
    )

    return {"message": "Logged out successfully"}


@router.post("/jwt-logout")
def jwt_logout(response: Response):
    """
    Legacy JWT logout - clears the access token cookie
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


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user information
    Returns user details including role
    """
    branch_code = current_branch.get()
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "role": current_user.role.name,
        "branch": {"code": branch_code, "name": BRANCHES[branch_code].name},
    }


class SwitchBranchRequest(BaseModel):
    branch: str


# Roles that get the branch dropdown (must match BranchSwitcher.tsx)
BRANCH_SWITCH_ROLES = {"admin", "sales", "production"}


@router.post("/switch-branch")
async def switch_branch(
    switch_request: SwitchBranchRequest,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user_from_session),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin, sales and production: move the current login to another branch. Each
    branch has its own users table, so the target branch must have an active user
    with the same username and the same role; a new session is created there and
    the cookies are swapped.
    """
    from ..database.database import session_factories

    role_name = current_user.role.name
    if role_name not in BRANCH_SWITCH_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot switch branch")

    target = switch_request.branch
    if target not in BRANCHES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown branch")
    if target not in session_factories:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Branch is not available")

    async with session_factories[target]() as target_db:
        result = await target_db.execute(
            select(User).options(selectinload(User.role)).where(User.username == current_user.username)
        )
        target_user = result.scalar_one_or_none()
        if not target_user or not target_user.is_active or target_user.role.name != role_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Is branch me aapka account nahi hai"
            )
        new_session = await create_session(
            user_id=str(target_user.id),
            db=target_db,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            company_id=str(target_user.company_id) if target_user.company_id else None,
            biometric_verified=False
        )

    # End the session in the branch being left
    old_token = request.cookies.get("session_token")
    if old_token:
        await invalidate_session(old_token, db)

    response.set_cookie(
        key="session_token",
        value=new_session.session_token,
        httponly=True,
        secure=os.getenv("ENVIRONMENT", "development") == "production",
        samesite="lax",
        max_age=36000,  # 10 hours (36000 seconds)
        path="/"
    )
    _set_branch_cookie(response, target)

    return {"branch": {"code": target, "name": BRANCHES[target].name}}
