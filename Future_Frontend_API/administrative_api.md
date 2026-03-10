# User Management API (Administration)

## 🔐 Authentication & Authorization

### Login Required

Before using any of these endpoints, you **MUST** login first:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }' \
  -c cookies.txt
```

**Save the cookie!** All subsequent requests require the session cookie (`-b cookies.txt`).

---

### 🔑 Access Control

These endpoints use **session-based authentication** with role checks:

| Decorator | Allowed Roles | Used By |
|-----------|--------------|---------|
| `admin_required_from_session()` | `admin` only | GET all, DELETE |
| `get_current_user_from_session()` | `admin`, `cashier`, `employee` | GET single, PUT (own profile) |

**Important Notes:**

1. **GET /users/** - Requires **admin** role
   - Only admins can view all users
   - Cashiers and employees cannot access this endpoint

2. **GET /users/{id}** - Requires **any authenticated user**
   - Users can view their own profile
   - Admins can view any user's profile

3. **PUT /users/{id}** - Requires **any authenticated user**
   - Users can update their own profile
   - Admins can update any user
   - **Only admins can update roles**

4. **DELETE /users/{id}** - Requires **admin** role
   - Only admins can delete users
   - Users cannot delete their own account

---

## API Endpoints

All user CRUD operations are handled through `/users/` endpoints.

---

### 1. GET /users/ - View All Users

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Get list of all users (admin, cashier, employee) with pagination and search.

**Endpoint**: `GET /users/?skip=0&limit=100&search_string=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | int | 0 | Number of records to skip |
| `limit` | int | 100 | Max records to return (max: 200) |
| `search_string` | string | - | Search by username, full_name, phone, cnic, branch, address |

**Example**:
```bash
curl -X GET "http://localhost:8000/users/?skip=0&limit=100&search_string=admin" \
  -b cookies.txt
```

**Response** (200 OK):
```json
[
  {
    "id": "8fc7528b-c3a2-4b36-a39a-68c13699de80",
    "full_name": "Admin User",
    "username": "admin",
    "role_id": "33128819-80ae-4a6a-9ab7-7eff272a81ff",
    "role_name": "admin",
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

**Error** (403 Forbidden):
```json
{
  "detail": "Admin or cashier access required"
}
```

---

### 2. POST /users/ - Create User

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Create a new user (admin, cashier, or employee).

**Endpoint**: `POST /users/`

**Request Body**:
```json
{
  "full_name": "John Doe",
  "username": "johndoe",
  "password": "secure_password123",
  "role_name": "cashier",
  "phone": "1234567890",
  "address": "123 Main St",
  "cnic": "1234567890123",
  "branch": "Main Branch"
}
```

**Request Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | ✅ Yes | Unique username |
| `password` | string | ✅ Yes | Plain text password (will be hashed) |
| `role_name` | string | ✅ Yes | `admin`, `cashier`, or `employee` |
| `full_name` | string | ❌ No | Full name |
| `phone` | string | ❌ No | Phone number |
| `cnic` | string | ❌ No | CNIC number |
| `address` | string | ❌ No | Address |
| `branch` | string | ❌ No | Branch name |

**Example**:
```bash
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "full_name": "John Doe",
    "username": "johndoe",
    "password": "secure_password123",
    "role_name": "cashier",
    "phone": "1234567890",
    "cnic": "1234567890123",
    "branch": "Main Branch"
  }'
```

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "full_name": "John Doe",
  "username": "johndoe",
  "role_id": "42a87026-09e0-40d2-8c21-23df1914e34d",
  "role_name": "cashier",
  "phone": "1234567890",
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

**Errors**:

**400 Bad Request** - Username taken:
```json
{
  "detail": "Username already taken"
}
```

**400 Bad Request** - Invalid role:
```json
{
  "detail": "Role 'cashier' does not exist. Available roles: admin, cashier, employee"
}
```

---

### 3. PUT /users/{user_id} - Update User

**Access**: `get_current_user_from_session()` - **Any authenticated user**

**Description**: Update user details. Users can update their own profile. Admins can update any user.

**Endpoint**: `PUT /users/{user_id}`

**Path Parameter**: `user_id` - UUID of the user

**Request Body** (all fields optional):
```json
{
  "full_name": "Updated Name",
  "username": "new_username",
  "password": "new_password123",
  "role_name": "admin",
  "phone": "9876543210",
  "cnic": "9876543210123",
  "address": "New Address",
  "branch": "New Branch"
}
```

**Important Rules**:
- ✅ Any user can update their own profile
- ✅ Admins can update any user
- ⚠️ **Only admins can update roles**
- ⚠️ **Users cannot update their own role**

**Example** - Admin updates another user:
```bash
curl -X PUT "http://localhost:8000/users/8fc7528b-c3a2-4b36-a39a-68c13699de80" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "full_name": "Updated Name",
    "phone": "9876543210",
    "role_name": "admin"
  }'
```

**Example** - User updates own profile:
```bash
curl -X PUT "http://localhost:8000/users/8fc7528b-c3a2-4b36-a39a-68c13699de80" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "phone": "9876543210",
    "address": "New Address"
  }'
```

**Response** (200 OK):
```json
{
  "id": "8fc7528b-c3a2-4b36-a39a-68c13699de80",
  "full_name": "Updated Name",
  "username": "admin",
  "role_id": "33128819-80ae-4a6a-9ab7-7eff272a81ff",
  "role_name": "admin",
  "phone": "9876543210",
  "cnic": "1234567890123",
  "branch": "Main Branch",
  "is_active": true,
  "updated_at": "2026-02-17T05:00:00.000000"
}
```

**Errors**:

**403 Forbidden** - Cannot update role (not admin):
```json
{
  "detail": "Only admins can update user roles"
}
```

**403 Forbidden** - Not authorized:
```json
{
  "detail": "Not authorized to update this user"
}
```

**404 Not Found**:
```json
{
  "detail": "User not found"
}
```

---

### 4. DELETE /users/{user_id} - Delete User

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Delete a user by ID. Users cannot delete their own account.

**Endpoint**: `DELETE /users/{user_id}`

**Path Parameter**: `user_id` - UUID of the user

**Important Rules**:
- ✅ Only admins can delete users
- ❌ **Users cannot delete their own account**
- ⚠️ This action is irreversible

**Example**:
```bash
curl -X DELETE "http://localhost:8000/users/8fc7528b-c3a2-4b36-a39a-68c13699de80" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "message": "User deleted successfully"
}
```

**Errors**:

**400 Bad Request** - Cannot delete self:
```json
{
  "detail": "Cannot delete your own account"
}
```

**404 Not Found**:
```json
{
  "detail": "User not found"
}
```

---

## Role Reference

### Available Roles

| Role Name | UUID | Description |
|-----------|------|-------------|
| `admin` | `33128819-80ae-4a6a-9ab7-7eff272a81ff` | Full system access |
| `cashier` | `42a87026-09e0-40d2-8c21-23df1914e34d` | POS and sales access |
| `employee` | `66ab52f4-391d-43ba-b569-21ec43a74aac` | Limited access |

**Recommendation**: Use `role_name` (string) instead of UUIDs.

---

## Frontend API Routes

The frontend uses Next.js API routes as proxies:

| Frontend Route | Backend Endpoint |
|----------------|------------------|
| `GET /api/users/` | `GET /users/` |
| `POST /api/users/` | `POST /users/` |
| `PUT /api/users/{id}` | `PUT /users/{id}` |
| `DELETE /api/users/{id}` | `DELETE /users/{id}` |

**Example** - Frontend fetch:
```typescript
const fetchUsers = async (searchTerm: string = '') => {
  const params = new URLSearchParams({
    skip: '0',
    limit: '100',
    search_string: searchTerm
  });

  const response = await fetch(`/api/users/?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to fetch users');
  }

  return response.json();
};
```

---

## Error Codes

| HTTP Status | Meaning | Common Causes |
|-------------|---------|---------------|
| 200 | OK | Success |
| 400 | Bad Request | Invalid input, username taken, invalid role |
| 401 | Unauthorized | Not logged in, invalid session |
| 403 | Forbidden | Insufficient permissions, role mismatch |
| 404 | Not Found | User not found |
| 500 | Server Error | Database error, server issue |

---

## Testing Checklist

### Login First
- [ ] Login with admin credentials
- [ ] Save cookies (`-c cookies.txt`)

### Test GET /users/
- [ ] Fetch all users (admin session)
- [ ] Fetch with search term
- [ ] Try with cashier session (should fail with 403)

### Test POST /users/
- [ ] Create new admin user
- [ ] Create new cashier user
- [ ] Create new employee user
- [ ] Try duplicate username (should fail)
- [ ] Try invalid role (should fail)

### Test PUT /users/{id}
- [ ] Update own profile (any user)
- [ ] Update another user (admin)
- [ ] Update role (admin only)
- [ ] Try updating role as non-admin (should fail with 403)

### Test DELETE /users/{id}
- [ ] Delete user (admin)
- [ ] Try deleting self (should fail with 400)
- [ ] Try delete as non-admin (should fail with 403)

---

## Related Documentation

- [Authentication API](../src/auth/session_auth.py) - Session management
- [User Model](../src/models/user.py) - Database schema
- [UserService](../src/services/user_service.py) - Business logic
