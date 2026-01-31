# Administrative API Documentation

This document provides comprehensive documentation for all administrative endpoints in the Regal POS Backend, including curl commands for testing and integration.

## Authentication

All admin endpoints require authentication with a valid JWT access token. Obtain a token by logging in:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Use the returned `access_token` in the Authorization header:

```bash
-H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## Admin User Management Endpoints

### 1. Get Admin User Details

**Endpoint**: `GET /admin/getadmin/{id}`

**Description**: Retrieve details of a specific admin user by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the admin user

**Example**:
```bash
curl -X GET http://localhost:8000/admin/getadmin/8fc7528b-c3a2-4b36-a39a-68c13699de80 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "ad_id": "8fc7528b-c3a2-4b36-a39a-68c13699de80",
  "ad_name": "Admin User",
  "ad_role": "admin",
  "ad_phone": "",
  "ad_address": "",
  "ad_password": "",
  "ad_cnic": "",
  "ad_branch": ""
}
```

### 2. Create Admin User

**Endpoint**: `POST /admin/createadmin`

**Description**: Create a new admin user.

**Authentication**: Admin role required

**Query Parameters**:
- `ad_name`: Full name of the admin user
- `ad_role`: Role (admin, cashier, employee)
- `ad_phone`: Phone number (optional)
- `ad_address`: Address (optional)
- `ad_password`: Password (optional, defaults to "default_password123")
- `ad_cnic`: CNIC number (optional)
- `ad_branch`: Branch (optional)

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/createadmin?ad_name=New%20Admin&ad_role=admin&ad_phone=1234567890&ad_address=New%20Address&ad_cnic=123456789&ad_branch=Main%20Branch" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "ad_id": "uuid-string",
  "ad_name": "New Admin",
  "ad_role": "admin",
  "ad_phone": "1234567890",
  "ad_address": "New Address",
  "ad_cnic": "123456789",
  "ad_branch": "Main Branch",
  "message": "Admin user created successfully"
}
```

### 3. Update Admin User

**Endpoint**: `PUT /admin/updateadmin/{id}`

**Description**: Update details of an existing admin user.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the admin user to update

**Query Parameters** (all optional):
- `ad_name`: Updated full name
- `ad_role`: Updated role
- `ad_phone`: Updated phone number
- `ad_address`: Updated address
- `ad_password`: Updated password
- `ad_cnic`: Updated CNIC number
- `ad_branch`: Updated branch

**Example**:
```bash
curl -X PUT "http://localhost:8000/admin/updateadmin/uuid-string?ad_name=Updated%20Name&ad_phone=0987654321" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "ad_id": "uuid-string",
  "ad_name": "Updated Name",
  "ad_role": "admin",
  "ad_phone": "0987654321",
  "ad_address": "Previous Address",
  "ad_cnic": "Previous CNIC",
  "ad_branch": "Previous Branch",
  "message": "Admin user updated successfully"
}
```

### 4. Delete Admin User

**Endpoint**: `POST /admin/deleteadmin/{id}`

**Description**: Delete an admin user by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the admin user to delete

**Note**: Users with audit logs cannot be deleted due to foreign key constraints for compliance purposes.

**Example**:
```bash
curl -X POST http://localhost:8000/admin/deleteadmin/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

### 5. View All Admin Users

**Endpoint**: `GET /admin/viewadmins`

**Description**: Get a list of all admin users with optional search functionality.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `search_string`: Search term to filter users
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/viewadmins?search_string=admin&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
[
  {
    "ad_id": "uuid-string",
    "ad_name": "Admin User",
    "ad_role": "admin",
    "ad_phone": "1234567890",
    "ad_address": "Address",
    "ad_cnic": "123456789",
    "ad_branch": "Branch",
    "is_active": true,
    "created_at": "2026-01-30T10:31:18.150552"
  }
]
```

### 6. View All Salesmen

**Endpoint**: `GET /admin/viewsalesman`

**Description**: Get a list of all salesmen with optional search functionality.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `search_string`: Search term to filter salesmen
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/viewsalesman?search_string=john&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
[
  {
    "id": "uuid-string",
    "name": "John Doe",
    "code": "JD001",
    "commission_rate": "5.00",
    "created_at": "2026-01-30T10:31:18.150552",
    "updated_at": "2026-01-30T10:31:18.150552"
  }
]
```

## Compatibility Endpoints

The following endpoints are also available for JavaScript frontend compatibility (capitalized versions):

- `GET /admin/GetAdmin/{id}` - Same as `/admin/getadmin/{id}`
- `POST /admin/DeleteAdmin/{id}` - Same as `/admin/deleteadmin/{id}`
- `GET /admin/ViewSalesman` - Same as `/admin/viewsalesman`
- `GET /admin/ViewAdmins` - Same as `/admin/viewadmins`
- `POST /admin/CreateAdmin` - Same as `/admin/createadmin`
- `PUT /admin/UpdateAdmin/{id}` - Same as `/admin/updateadmin/{id}`

## Error Handling

All endpoints return standardized error responses:

```json
{
  "error": {
    "type": "error_type",
    "message": "Human-readable error message",
    "status_code": 400,
    "path": "/endpoint/path",
    "timestamp": "2026-01-31T11:00:00.000000"
  }
}
```

## Security Notes

- All endpoints require admin role authentication
- Passwords are never returned in responses
- User data is protected by role-based access control
- Audit logs are maintained for all administrative actions
- Foreign key constraints prevent deletion of users with historical records

## Production Ready Features

- Async/await implementation for high concurrency
- Pydantic v2 validation
- Proper error handling and logging
- Database transaction safety
- JWT token-based authentication
- Role-based access control
- Input sanitization and validation