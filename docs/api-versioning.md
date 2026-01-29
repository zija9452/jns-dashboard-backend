# API Versioning Strategy for Regal POS Backend

## Overview
This document defines the API versioning strategy for the Regal POS Backend system. The strategy ensures backward compatibility while allowing for controlled evolution of the API.

## Versioning Approach

### URI Path Versioning
The system will use URI path versioning to indicate the API version:

```
https://api.regalpos.com/v1/users
https://api.regalpos.com/v2/users
```

### Version Format
- Semantic versioning: MAJOR.MINOR.PATCH (e.g., v1.0.0)
- For API paths: only MAJOR version in URI (e.g., /v1/, /v2/)
- MINOR and PATCH versions managed through changelog and documentation

## Implementation Strategy

### 1. Current Version (v1)
- All existing endpoints will be accessible under `/api/v1/`
- Backward compatibility maintained for existing clients
- New features added as optional parameters or new endpoints

### 2. Version Declaration
```python
# In main application
API_V1_PREFIX = "/api/v1"
API_V2_PREFIX = "/api/v2"  # Future version

# Example router setup
from fastapi import FastAPI
from src.routers.v1 import users as users_v1
from src.routers.v1 import products as products_v1
# ... other v1 routers

app = FastAPI(title="Regal POS Backend")

# Mount v1 API
app.include_router(users_v1.router, prefix=API_V1_PREFIX)
app.include_router(products_v1.router, prefix=API_V1_PREFIX)
```

### 3. Version-Specific Routers
Create version-specific router directories:

```
src/
└── routers/
    ├── v1/
    │   ├── __init__.py
    │   ├── users.py
    │   ├── products.py
    │   └── ...
    └── v2/
        ├── __init__.py
        ├── users.py  # Potentially different schema
        └── ...
```

## Version Lifecycle Management

### Deprecation Policy
- **Announcement**: 6 months before deprecation
- **Support Period**: 12 months after announcement
- **Removal**: After support period ends
- **Migration Assistance**: Provided during transition

### Deprecation Process
1. Add deprecation headers to affected endpoints:
   ```
   X-API-Version: v1
   X-API-Deprecated: true
   X-API-Deprecation-Date: YYYY-MM-DD
   X-API-Alternative: /api/v2/new-endpoint
   ```

2. Update documentation with deprecation notices

3. Add console/log warnings for deprecated usage

4. Monitor usage of deprecated endpoints

## Backward Compatibility Guidelines

### Maintaining Compatibility
- **Safe Changes**: Adding optional fields, new endpoints
- **Breaking Changes**: Removing/renaming fields, changing response structure
- **Major Versions**: For breaking changes
- **Minor Versions**: For backward-compatible additions

### Version Negotiation
```python
from fastapi import Header, HTTPException
from typing import Optional

def get_api_version(x_api_version: Optional[str] = Header(None)):
    """
    Extract API version from header or default to latest
    """
    if x_api_version and x_api_version.startswith('v'):
        version = x_api_version[1:]  # Remove 'v' prefix
        if version.isdigit():
            return int(version)

    # Default to latest version (v1 for now)
    return 1
```

## Implementation Example

### Versioned Router (v1)
```python
# src/routers/v1/users.py
from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import List

from ...database.database import get_db
from ...models.v1.user import UserRead, UserCreate
from ...services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])

@router.get("/", response_model=List[UserRead])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get list of users (v1)
    """
    return await UserService.get_users(db, skip=skip, limit=limit)

@router.post("/", response_model=UserRead)
async def create_user(
    user: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new user (v1)
    """
    return await UserService.create_user(db, user)
```

### Versioned Models
```python
# src/models/v1/user.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    created_at: datetime
    is_active: bool = True

    class Config:
        from_attributes = True
```

## Monitoring and Analytics

### Version Usage Tracking
- Track API version usage in metrics
- Monitor deprecated version usage
- Alert on unusual patterns in version adoption

```python
from ...utils.metrics import REQUEST_COUNT

# In each endpoint
REQUEST_COUNT.labels(
    method=request.method,
    path=request.url.path,
    status_code=response.status_code,
    api_version="v1"  # or extracted version
).inc()
```

## Documentation Strategy

### API Documentation
- Separate documentation for each version
- Changelog tracking changes between versions
- Migration guides for version upgrades
- Interactive API explorer for each version

### Client Communication
- Email notifications for upcoming deprecations
- Dashboard showing client version usage
- SDK updates with version-specific features

## Future Enhancements

### Advanced Versioning
- Header-based versioning as alternative to URI
- Query parameter versioning for specific requests
- Feature flags tied to API versions
- Automated testing across versions

## Compliance and Standards

### Industry Standards
- Follow REST API best practices
- Align with OpenAPI Specification
- Maintain consistency with industry standards
- Regular review against evolving best practices

## Rollback Procedures

### Version Rollback
- Maintain ability to rollback to previous version
- Database migration scripts for version rollback
- Configuration management for version-specific settings
- Testing procedures for rollback scenarios

## Contact and Support

For questions about API versioning:
- API Team: api-team@regalpos.com
- Documentation: https://docs.regalpos.com/api-versioning
- Changelog: https://api.regalpos.com/changelog