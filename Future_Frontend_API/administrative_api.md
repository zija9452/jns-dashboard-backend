# Administrative API Documentation

This document provides comprehensive documentation for all administrative endpoints in the Regal POS Backend with session-based authentication, including curl commands for testing and integration.

## Authentication

All admin endpoints require session-based authentication. Obtain a session by logging in:

```bash
curl -X POST http://localhost:8000/auth/session-login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' \
  -c cookies.txt
```

The login response will include a session cookie that will be automatically sent with subsequent requests when using the `-b` flag with curl.

### Session Expiration
- Session cookies expire after **3 hours**
- Access tokens (JWT) expire after **15 minutes**
- Refresh tokens expire after **30 days**

### Rate Limiting

Authentication endpoints are protected by rate limiting to prevent brute force attacks:
- 5 login attempts per 5 minutes per IP address
- 3 failed attempts trigger a 15-minute temporary lockout
- Successful login resets the failed attempts counter

If rate limits are exceeded, you'll receive a 429 Too Many Requests response:
```json
{
  "detail": "Too many login attempts. Please try again later."
}
```

---

## User Management Endpoints

All user CRUD operations (admin, cashier, employee) are handled through the `/users/` endpoints.

### 1. View All Users

**Endpoint**: `GET /users/`

**Description**: Get list of all users (admin, cashier, employee) with pagination.

**Authentication**: Admin role required (session-based)

**Query Parameters**:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100, max: 200)

**Example**:
```bash
curl -X GET "http://localhost:8000/users/?skip=0&limit=100" \
  -b cookies.txt
```

**Response**:
```json
[
  {
    "id": "8fc7528b-c3a2-4b36-a39a-68c13699de80",
    "full_name": "Admin User",
    "username": "admin",
    "role_id": "33128819-80ae-4a6a-9ab7-7eff272a81ff",
    "phone": "1234567890",
    "address": "Main Office",
    "cnic": "1234567890123",
    "branch": "Main Branch",
    "company_id": null,
    "is_biometric_enabled": false,
    "is_active": true,
    "created_at": "2026-01-30T10:31:18.150552",
    "updated_at": "2026-01-30T10:31:18.150594",
    "original_password": null
  }
]
```

### 2. View Single User

**Endpoint**: `GET /users/{user_id}`

**Description**: Get details of a specific user by ID.

**Authentication**: Session-based (users can view their own profile, admins can view any user)

**Parameters**:
- `{user_id}`: UUID of the user

**Example**:
```bash
curl -X GET "http://localhost:8000/users/8fc7528b-c3a2-4b36-a39a-68c13699de80" \
  -b cookies.txt
```

**Response**:
```json
{
  "id": "8fc7528b-c3a2-4b36-a39a-68c13699de80",
  "full_name": "Admin User",
  "username": "admin",
  "role_id": "33128819-80ae-4a6a-9ab7-7eff272a81ff",
  "phone": "1234567890",
  "address": "Main Office",
  "cnic": "1234567890123",
  "branch": "Main Branch",
  "company_id": null,
  "is_biometric_enabled": false,
  "is_active": true,
  "created_at": "2026-01-30T10:31:18.150552",
  "updated_at": "2026-01-30T10:31:18.150594",
  "original_password": null
}
```

### 3. Create User

**Endpoint**: `POST /users/`

**Description**: Create a new user (admin, cashier, or employee).

**Authentication**: Admin role required (session-based)

**Request Body** (JSON):
```json
{
  "full_name": "John Doe",
  "username": "johndoe",
  "password": "secure_password123",
  "role_id": "42a87026-09e0-40d2-8c21-23df1914e34d",
  "phone": "1234567890",
  "address": "123 Main St",
  "cnic": "1234567890123",
  "branch": "Main Branch"
}
```

**Role IDs**:
- `33128819-80ae-4a6a-9ab7-7eff272a81ff` - Admin
- `42a87026-09e0-40d2-8c21-23df1914e34d` - Cashier
- `66ab52f4-391d-43ba-b569-21ec43a74aac` - Employee

**Example**:
```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "full_name": "John Doe",
    "username": "johndoe",
    "password": "secure_password123",
    "role_id": "42a87026-09e0-40d2-8c21-23df1914e34d",
    "phone": "1234567890",
    "address": "123 Main St",
    "cnic": "1234567890123",
    "branch": "Main Branch"
  }'
```

**Response**:
```json
{
  "id": "uuid-string",
  "full_name": "John Doe",
  "username": "johndoe",
  "role_id": "42a87026-09e0-40d2-8c21-23df1914e34d",
  "phone": "1234567890",
  "address": "123 Main St",
  "cnic": "1234567890123",
  "branch": "Main Branch",
  "company_id": null,
  "is_biometric_enabled": false,
  "is_active": true,
  "created_at": "2026-02-17T05:00:00.000000",
  "updated_at": "2026-02-17T05:00:00.000000",
  "original_password": "secure_password123"
}
```

### 4. Update User

**Endpoint**: `PUT /users/{user_id}`

**Description**: Update an existing user's details.

**Authentication**: Session-based (users can update their own profile, admins can update any user)

**Path Parameter**:
- `{user_id}`: UUID of the user to update

**Request Body** (JSON, all fields optional):
```json
{
  "full_name": "Updated Name",
  "phone": "9876543210",
  "address": "Updated Address",
  "cnic": "9876543210123",
  "branch": "Updated Branch",
  "role_id": "33128819-80ae-4a6a-9ab7-7eff272a81ff",
  "password": "new_password123"
}
```

**Example**:
```bash
curl -X PUT "http://localhost:8000/users/8fc7528b-c3a2-4b36-a39a-68c13699de80" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "full_name": "Updated Name",
    "phone": "9876543210"
  }'
```

**Response**:
```json
{
  "id": "8fc7528b-c3a2-4b36-a39a-68c13699de80",
  "full_name": "Updated Name",
  "username": "admin",
  "role_id": "33128819-80ae-4a6a-9ab7-7eff272a81ff",
  "phone": "9876543210",
  "address": "Main Office",
  "cnic": "1234567890123",
  "branch": "Main Branch",
  "company_id": null,
  "is_biometric_enabled": false,
  "is_active": true,
  "created_at": "2026-01-30T10:31:18.150552",
  "updated_at": "2026-02-17T05:00:00.000000",
  "original_password": null
}
```

### 5. Delete User

**Endpoint**: `DELETE /users/{user_id}`

**Description**: Delete a user by ID.

**Authentication**: Admin role required (session-based)

**Path Parameter**:
- `{user_id}`: UUID of the user to delete

**Note**: Users cannot delete their own account.

**Example**:
```bash
curl -X DELETE "http://localhost:8000/users/8fc7528b-c3a2-4b36-a39a-68c13699de80" \
  -b cookies.txt
```

**Response**:
```json
{
  "message": "User deleted successfully"
}
```

---

## Password Hashing

Passwords are hashed using **Argon2** algorithm before storing in the database.

**Hashing Endpoint**: `src/auth/password.py`

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def get_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)
```

**Note**: For demonstration purposes, the original password is also stored in plain text in the `original_password` field. This is a **MAJOR SECURITY VULNERABILITY** and should be removed in production.

---

## Other Admin Endpoints

The `/admin/` router contains endpoints for:
- Salesman management
- Product management
- Customer management
- Vendor management
- Invoice management
- Expense management
- Stock management
- Reports and dashboards

Refer to specific API documentation files for these endpoints.
