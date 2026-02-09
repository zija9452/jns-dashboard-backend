 yhn nhi mere project me ek file create kr do , shuru se btana us me k filhal jwt pr he session baseed krna he , or employees me biometric bhi

  ✦ Session-Based Authentication and Biometric Integration Documentation

    Overview
    This document describes the implementation of session-based authentication with biometric integration for the Regal POS system. The system will have different authentication methods for
    different user roles:
     - Admin/Cashier: Username/password with session-based authentication
     - Employee: Biometric thumb scan with session-based authentication

    Current State: JWT-Based Authentication
    Currently, the system uses JWT-based authentication where:
     - Users login with username/password
     - Receive JWT access and refresh tokens
     - Tokens are sent in Authorization header
     - No server-side session state is maintained

    Target State: Session-Based Authentication
    After migration, the system will use:
     - Server-side session storage with session IDs in cookies
     - Different authentication flows for different user roles
     - Biometric verification for employee users
     - Traditional username/password for admin/cashier users

    Database Schema Changes

    1. Session Table

      1 CREATE TABLE user_sessions (
      2     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      3     user_id UUID NOT NULL REFERENCES users(id),
      4     session_token VARCHAR(255) UNIQUE NOT NULL,
      5     expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
      6     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      7     updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
      8     ip_address VARCHAR(45),
      9     user_agent TEXT,
     10     is_active BOOLEAN DEFAULT TRUE,
     11     company_id UUID,
     12     biometric_verified BOOLEAN DEFAULT FALSE
     13 );
     14
     15 -- Indexes for performance
     16 CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
     17 CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
     18 CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);
     19 CREATE INDEX idx_user_sessions_company ON user_sessions(company_id);

    2. Company Table

     1 CREATE TABLE companies (
     2     id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
     3     name VARCHAR(255) NOT NULL,
     4     branch VARCHAR(255),
     5     created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
     6     updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
     7 );

    3. User Table Updates

     1 ALTER TABLE users ADD COLUMN company_id UUID REFERENCES companies(id);
     2 ALTER TABLE users ADD COLUMN biometric_hash VARCHAR(255); -- For employee biometric data
     3 ALTER TABLE users ADD COLUMN is_biometric_enabled BOOLEAN DEFAULT FALSE;
     4 ALTER TABLE users ADD COLUMN biometric_device_id VARCHAR(255); -- For device registration

    Implementation Steps

    Step 1: Create Session Models

      1 # src/models/session.py
      2 from sqlmodel import SQLModel, Field
      3 from datetime import datetime
      4 import uuid
      5
      6 class UserSession(SQLModel, table=True):
      7     __tablename__ = "user_sessions"
      8
      9     id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
     10     user_id: uuid.UUID = Field(foreign_key="users.id")
     11     session_token: str = Field(unique=True, index=True)
     12     expires_at: datetime
     13     created_at: datetime = Field(default_factory=datetime.now)
     14     updated_at: datetime = Field(default_factory=datetime.now)
     15     ip_address: str = Field(default=None)
     16     user_agent: str = Field(default=None)
     17     is_active: bool = Field(default=True)
     18     company_id: uuid.UUID = Field(default=None, foreign_key="companies.id")
     19     biometric_verified: bool = Field(default=False)
     20
     21 class UserSessionCreate(SQLModel):
     22     user_id: uuid.UUID
     23     expires_at: datetime
     24     ip_address: str = None
     25     user_agent: str = None
     26     company_id: uuid.UUID = None
     27     biometric_verified: bool = False

    Step 2: Create Session Utilities

      1 # src/utils/session.py
      2 import secrets
      3 from datetime import datetime, timedelta
      4 from sqlalchemy.ext.asyncio import AsyncSession
      5 from sqlalchemy import select
      6 from ..models.session import UserSession
      7 from ..models.user import User
      8
      9 def generate_session_token():
     10     """Generate a secure random session token"""
     11     return secrets.token_urlsafe(32)
     12
     13 async def create_session(user_id: uuid.UUID, db: AsyncSession, ip_address: str = None,
     14                         user_agent: str = None, company_id: uuid.UUID = None,
     15                         biometric_verified: bool = False):
     16     """Create a new user session"""
     17     session_token = generate_session_token()
     18     expires_at = datetime.now() + timedelta(hours=24)  # 24-hour session
     19
     20     session = UserSession(
     21         user_id=user_id,
     22         session_token=session_token,
     23         expires_at=expires_at,
     24         ip_address=ip_address,
     25         user_agent=user_agent,
     26         company_id=company_id,
     27         biometric_verified=biometric_verified
     28     )
     29
     30     db.add(session)
     31     await db.commit()
     32     await db.refresh(session)
     33
     34     return session
     35
     36 async def get_session_by_token(session_token: str, db: AsyncSession):
     37     """Get active session by token"""
     38     statement = select(UserSession).where(
     39         UserSession.session_token == session_token,
     40         UserSession.is_active == True,
     41         UserSession.expires_at > datetime.now()
     42     )
     43     result = await db.execute(statement)
     44     return result.scalar_one_or_none()
     45
     46 async def invalidate_session(session_token: str, db: AsyncSession):
     47     """Invalidate a session (logout)"""
     48     session = await get_session_by_token(session_token, db)
     49     if session:
     50         session.is_active = False
     51         await db.commit()
     52         return True
     53     return False
     54
     55 async def cleanup_expired_sessions(db: AsyncSession):
     56     """Remove expired sessions from database"""
     57     statement = select(UserSession).where(UserSession.expires_at < datetime.now())
     58     result = await db.execute(statement)
     59     expired_sessions = result.scalars().all()
     60
     61     for session in expired_sessions:
     62         await db.delete(session)
     63
     64     await db.commit()

    Step 3: Create Biometric Service

      1 # src/services/biometric_service.py
      2 import hashlib
      3 from sqlalchemy.ext.asyncio import AsyncSession
      4 from sqlalchemy import select
      5 from ..models.user import User
      6
      7 class BiometricService:
      8     @staticmethod
      9     async def register_employee_biometric(user_id: uuid.UUID, thumb_data: str,
     10                                         company_id: uuid.UUID, db: AsyncSession):
     11         """
     12         Register thumb scan for employee user
     13         """
     14         # Hash the thumb data for secure storage
     15         thumb_hash = hashlib.sha256(thumb_data.encode()).hexdigest()
     16
     17         # Update user with biometric data
     18         statement = select(User).where(User.id == user_id)
     19         result = await db.execute(statement)
     20         user = result.scalar_one_or_none()
     21
     22         if user:
     23             user.biometric_hash = thumb_hash
     24             user.company_id = company_id
     25             user.is_biometric_enabled = True
     26             await db.commit()
     27             return True
     28         return False
     29
     30     @staticmethod
     31     async def verify_employee_biometric(thumb_data: str, company_id: uuid.UUID,
     32                                      db: AsyncSession):
     33         """
     34         Verify employee thumb scan against stored hash
     35         """
     36         thumb_hash = hashlib.sha256(thumb_data.encode()).hexdigest()
     37
     38         statement = select(User).where(
     39             User.biometric_hash == thumb_hash,
     40             User.company_id == company_id,
     41             User.is_active == True,
     42             User.is_biometric_enabled == True,
     43             User.role.name == "employee"  # Only for employee users
     44         )
     45
     46         result = await db.execute(statement)
     47         user = result.scalar_one_or_none()
     48         return user

    Step 4: Update Authentication Dependencies

      1 # src/auth/session_auth.py
      2 from fastapi import Request, HTTPException, status, Depends
      3 from ..models.user import User
      4 from ..utils.session import get_session_by_token
      5 from ..database.database import get_db
      1 # src/auth/session_auth.py
      2 from fastapi import Request, HTTPException, status, Depends
      3 from ..models.user import User
      4 from ..utils.session import get_session_by_token
      5 from ..database.database import get_db
      6 from sqlalchemy.ext.asyncio import AsyncSession
      7 from sqlalchemy import select
      8
      9 async def get_current_user_from_session(request: Request, db: AsyncSession = Depends(get_db)):
     10     """Get current user from session"""
     11     session_token = request.cookies.get("session_token")
     12
     13     if not session_token:
     14         raise HTTPException(
     15             status_code=status.HTTP_401_UNAUTHORIZED,
     16             detail="Not authenticated"
     17         )
     18
     19     session = await get_session_by_token(session_token, db)
     20     if not session:
     21         raise HTTPException(
     22             status_code=status.HTTP_401_UNAUTHORIZED,
     23             detail="Invalid session"
     24         )
     25
     26     # Get user associated with session
     27     user_statement = select(User).where(User.id == session.user_id)
     28     user_result = await db.execute(user_statement)
     29     user = user_result.scalar_one_or_none()
     30
     31     if not user or not user.is_active:
     32         raise HTTPException(
     33             status_code=status.HTTP_401_UNAUTHORIZED,
     34             detail="User account inactive"
     35         )
     36
     37     return user
     38
     39 def admin_required_from_session():
     40     """Require admin role from session (admin/cashier can access)"""
     41     async def role_checker(current_user: User = Depends(get_current_user_from_session)):
     42         if current_user.role.name not in ["admin", "cashier"]:
     43             raise HTTPException(
     44                 status_code=status.HTTP_403_FORBIDDEN,
     45                 detail="Admin or cashier access required"
     46             )
     47         return current_user
     48     return role_checker
     49
     50 def employee_required_from_session():
     51     """Require employee role from session (biometric only)"""
     52     async def role_checker(current_user: User = Depends(get_current_user_from_session)):
     53         if current_user.role.name != "employee":
     54             raise HTTPException(
     55                 status_code=status.HTTP_403_FORBIDDEN,
      1 # In auth router (src/routers/auth.py)
      2 from fastapi import Response, Request
      3 from ..utils.session import create_session
      4 from ..services.biometric_service import BiometricService
      5
      6 @router.post("/login")
      7 async def traditional_login(
      8     response: Response,
      9     form_data: OAuth2PasswordRequestForm = Depends(),
     10     db: AsyncSession = Depends(get_db),
     11     request: Request = None
      1 # In auth router (src/routers/auth.py)
      2 from fastapi import Response, Request
      3 from ..utils.session import create_session
      4 from ..services.biometric_service import BiometricService
      5
      6 @router.post("/login")
      7 async def traditional_login(
      8     response: Response,
      9     form_data: OAuth2PasswordRequestForm = Depends(),
       1 # In auth router (src/routers/auth.py)
       2 from fastapi import Response, Request
       3 from ..utils.session import create_session
       4 from ..services.biometric_service import BiometricService
       5
       6 @router.post("/login")
       7 async def traditional_login(
       8     response: Response,
       9     form_data: OAuth2PasswordRequestForm = Depends(),
      10     db: AsyncSession = Depends(get_db),
      11     request: Request = None
      12 ):
      13     """
      14     Traditional login for admin/cashier users
      15     """
      16     user = await authenticate_user(form_data.username, form_data.password, db)
      17     if not user:
      18         raise HTTPException(
      19             status_code=status.HTTP_401_UNAUTHORIZED,
      20             detail="Incorrect username or password"
      21         )
      22
      23     # Check if user has biometric enabled - if so, password login should be disabled
      24     if user.is_biometric_enabled:
      25         raise HTTPException(
      26             status_code=status.HTTP_401_UNAUTHORIZED,
      27             detail="Biometric authentication required. Password login disabled."
      28         )
      29
      30     # Check if user is employee (should not use password login)
      31     if user.role.name == "employee":
      32         raise HTTPException(
      33             status_code=status.HTTP_401_UNAUTHORIZED,
      34             detail="Employee users must use biometric authentication"
      35         )
      36
      37     # Create session
      38     ip_address = request.client.host if request else None
      39     user_agent = request.headers.get("user-agent") if request else None
      40
      41     session = await create_session(
      42         user_id=user.id,
      43         db=db,
      44         ip_address=ip_address,
      45         user_agent=user_agent,
      46         company_id=user.company_id,
      47         biometric_verified=False  # Traditional login
      48     )
      49
      50     # Set session cookie
      51     response.set_cookie(
      52         key="session_token",
      53         value=session.session_token,
      54         httponly=True,
      55         secure=True,  # Set to False in development
      56         samesite="lax",
      57         max_age=86400  # 24 hours
      58     )
      59
      60     return {
      61         "message": "Login successful",
      62         "user": {
      63             "id": str(user.id),
      64             "username": user.username,
      65             "role": user.role.name,
      66             "company_id": str(user.company_id) if user.company_id else None
      67         }
      68     }
      69
      70 @router.post("/biometric/thumb-login")
      71 async def biometric_thumb_login(
      72     request: Request,
      73     response: Response,
      74     thumb_data: str,  # Thumb scan data from device
      75     company_id: str,  # Company ID from device or form
      76     db: AsyncSession = Depends(get_db)
      77 ):
      78     """
      79     Biometric login for employee users only
      80     """
      81     # Verify biometric data
      82     user = await BiometricService.verify_employee_biometric(
      83         thumb_data=thumb_data,
      84         company_id=uuid.UUID(company_id),
      85         db=db
      86     )
      87
      88     if not user:
      89         raise HTTPException(
      90             status_code=status.HTTP_401_UNAUTHORIZED,
      91             detail="Invalid thumb scan or company mismatch"
      92         )
      93
      94     if user.role.name != "employee":
      95         raise HTTPException(
      96             status_code=status.HTTP_401_UNAUTHORIZED,
      97             detail="Biometric authentication only available for employee users"
      98         )
      99
     100     # Create session with biometric verification flag
     101     ip_address = request.client.host
     102     user_agent = request.headers.get("user-agent")
     103
     104     session = await create_session(
     105         user_id=user.id,
     106         db=db,
     107         ip_address=ip_address,
     108         user_agent=user_agent,
     109         company_id=uuid.UUID(company_id),
     110         biometric_verified=True  # Biometric login
     111     )
     112
     113     # Set session cookie
     114     response.set_cookie(
     115         key="session_token",
     116         value=session.session_token,
     117         httponly=True,
     118         secure=True,
     119         samesite="lax",
     120         max_age=86400
     121     )
     122
     123     return {
     124         "message": "Biometric login successful",
     125         "user": {
     126             "id": str(user.id),
     127             "username": user.username,
     128             "role": user.role.name,
     129             "company_id": str(user.company_id)
     130         }
     131     }

    Step 6: Update Logout Endpoint

      1 @router.post("/logout")
      2 async def logout(
      3     response: Response,
      4     current_user: User = Depends(get_current_user_from_session),
      5     db: AsyncSession = Depends(get_db)
      6 ):
      7     """Logout user and invalidate session"""
      8     session_token = response.request.cookies.get("session_token")
      9
     10     if session_token:
     11         await invalidate_session(session_token, db)
     12
     13     # Clear session cookie
     14     response.set_cookie(
     15         key="session_token",
     16         value="",
     17         httponly=True,
     18         secure=True,
     19         samesite="lax",
     20         expires=0
     21     )
     22
     23     return {"message": "Logged out successfully"}

    Step 7: Update All Protected Routes
    Replace all JWT-based dependencies with session-based ones:

     1 # Example: Update walkin-invoice endpoints
     2 @router.post("/walkin-invoices")
     3 async def create_walkin_invoice(
     4     request_data: dict,
     5     current_user: User = Depends(admin_required_from_session()),  # Changed from admin_required()
     6     db: AsyncSession = Depends(get_db)
     7 ):
     8     # ... existing functionality

    Step 8: Frontend Integration

      1 // Traditional login for admin/cashier
      2 async function traditionalLogin(username, password) {
      3   const formData = new FormData();
      4   formData.append('username', username);
      5   formData.append('password', password);
      6
      7   const response = await fetch('/auth/login', {
      8     method: 'POST',
      9     body: formData,
     10     credentials: 'include'  // Important: include cookies
     11   });
     12
     13   return response.json();
     14 }
     15
     16 // Biometric login for employees
     17 async function biometricLogin(thumbData, companyId) {
     18   const response = await fetch('/auth/biometric/thumb-login', {
     19     method: 'POST',
     20     headers: {
     21       'Content-Type': 'application/json',
     22     },
     23     body: JSON.stringify({
     24       thumb_data: thumbData,
     25       company_id: companyId
     26     }),
     27     credentials: 'include'  // Important: include cookies
     28   });
     29
     30   return response.json();
     31 }
     32
     33 // API calls will automatically include session cookies
     34 fetch('/api/protected-endpoint', {
     35   credentials: 'include'  // Automatically includes session cookie
     36 });

    Security Features

    1. Role-Based Session Control
     - Admin/Cashier: Username/password sessions
     - Employee: Biometric-only sessions
     - Company isolation: Users can only access from their registered company

    2. Session Security
     - HttpOnly cookies prevent XSS attacks
     - Secure cookies (HTTPS only in production)
     - SameSite=Lax prevents CSRF
     - Session timeout and automatic cleanup
     - IP binding for sensitive operations

    3. Biometric Security
     - Thumb data hashed and securely stored
     - Company verification required
     - Session tied to biometric verification
     - No password fallback for biometric users

    Migration Plan

    Phase 1: Database Setup
     1. Create session and company tables
     2. Update user table with biometric fields
     3. Add indexes for performance

    Phase 2: Backend Implementation
     1. Implement session utilities
     2. Create biometric service
     3. Update authentication dependencies
     4. Add new login endpoints

    Phase 3: Route Updates
     1. Replace JWT dependencies with session dependencies
     2. Update all protected endpoints
     3. Test authentication flows

    Phase 4: Frontend Integration
     1. Update login forms
     2. Implement biometric device integration
     3. Test session management

    Phase 5: Security Testing
     1. Verify role-based access
     2. Test company isolation
     3. Validate biometric security
     4. Test session cleanup

    Hardware Integration Notes

    Thumb Scanner Device
     - Connect via USB/Serial to backend server
     - Implement device polling or event-based scanning
     - Hash thumb data before sending to server
     - Register devices to specific companies

    Company Validation
     - Each thumb scanner is tied to a specific company
     - Employees can only login from their assigned company location
     - Cross-company access is prevented

    This implementation provides a robust, secure authentication system with different methods for different user roles, ensuring employees use biometric authentication while allowing
    admin/cashier users to continue with traditional login methods.
