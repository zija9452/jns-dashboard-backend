# Salesman API Documentation

This document provides comprehensive documentation for all salesman-related endpoints in the Regal POS Backend, including curl commands for testing and integration.

## Authentication

All salesman endpoints require authentication with a valid JWT access token. Obtain a token by logging in:

```bash
curl -X POST http://localhost:8000/auth/traditional-login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Use the returned `access_token` in the Authorization header:

```bash
-H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## Salesman Management Endpoints

### 1. Get All Salesmen

**Endpoint**: `GET /salesman/`

**Description**: Get list of all salesmen with pagination.

**Authentication**: Employee role or higher required

**Query Parameters** (optional):
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/salesman/?skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
[
  {
    "id": "uuid-string",
    "name": "John Smith",
    "code": "JS001",
    "phone": "+1234567890",
    "address": "123 Main St, City, Country",
    "branch": "Main Branch",
    "commission_rate": "5.00",
    "created_at": "2026-02-02T07:04:18.497796",
    "updated_at": "2026-02-02T07:04:18.497920"
  }
]
```

### 2. Create Salesman

**Endpoint**: `POST /salesman/`

**Description**: Create a new salesman.

**Authentication**: Admin role required

**Request Body**:
```json
{
  "name": "string",
  "code": "string",
  "phone": "string",
  "address": "string",
  "branch": "string",
  "commission_rate": "decimal"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/salesman/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Smith",
    "code": "JS001",
    "phone": "+1234567890",
    "address": "123 Main St, City, Country",
    "branch": "Main Branch",
    "commission_rate": 5.0
  }'
```

**Response**:
```json
{
  "id": "uuid-string",
  "name": "John Smith",
  "code": "JS001",
  "phone": "+1234567890",
  "address": "123 Main St, City, Country",
  "branch": "Main Branch",
  "commission_rate": "5.00",
  "created_at": "2026-02-02T07:04:18.497796",
  "updated_at": "2026-02-02T07:04:18.497920"
}
```

### 3. Get Salesman by ID

**Endpoint**: `GET /salesman/{id}`

**Description**: Retrieve specific salesman details by ID.

**Authentication**: Employee role or higher required

**Path Parameter**:
- `{id}`: UUID of the salesman

**Example**:
```bash
curl -X GET http://localhost:8000/salesman/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "id": "uuid-string",
  "name": "John Smith",
  "code": "JS001",
  "phone": "+1234567890",
  "address": "123 Main St, City, Country",
  "branch": "Main Branch",
  "commission_rate": "5.00",
  "created_at": "2026-02-02T07:04:18.497796",
  "updated_at": "2026-02-02T07:04:18.497920"
}
```

### 4. Update Salesman

**Endpoint**: `PUT /salesman/{id}`

**Description**: Update a specific salesman by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the salesman to update

**Request Body**:
```json
{
  "name": "string",
  "code": "string",
  "phone": "string",
  "address": "string",
  "branch": "string",
  "commission_rate": "decimal"
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/salesman/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Updated",
    "phone": "+0987654321",
    "address": "456 Updated St, New City, Country",
    "branch": "Downtown Branch",
    "commission_rate": 6.0
  }'
```

**Response**:
```json
{
  "id": "uuid-string",
  "name": "John Updated",
  "code": "JS001",
  "phone": "+0987654321",
  "address": "456 Updated St, New City, Country",
  "branch": "Downtown Branch",
  "commission_rate": "6.00",
  "created_at": "2026-02-02T07:04:18.497796",
  "updated_at": "2026-02-02T07:05:18.497920"
}
```

### 5. Delete Salesman

**Endpoint**: `DELETE /salesman/{id}`

**Description**: Delete a salesman by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the salesman to delete

**Example**:
```bash
curl -X DELETE http://localhost:8000/salesman/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "message": "Salesman deleted successfully"
}
```

## Admin-Specific Salesman Endpoints (JavaScript Frontend Compatible)

### 6. Get Salesman by ID (Admin)

**Endpoint**: `GET /admin/GetSalesman/{id}`

**Description**: Retrieve specific salesman details by ID for JavaScript frontend compatibility.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the salesman

**Example**:
```bash
curl -X GET http://localhost:8000/admin/GetSalesman/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "sal_id": "uuid-string",
  "sal_name": "John Smith",
  "sal_phone": "+1234567890",
  "sal_address": "123 Main St, City, Country",
  "branch": "Main Branch"
}
```

### 7. View Salesmen (Admin)

**Endpoint**: `GET /admin/viewsalesman`

**Description**: View salesmen with optional search functionality for JavaScript frontend compatibility.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `search_string`: Search term to filter salesmen by name or code
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/viewsalesman?search_string=John&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
[
  {
    "sal_id": "uuid-string",
    "sal_name": "John Smith",
    "sal_phone": "+1234567890",
    "sal_address": "123 Main St, City, Country",
    "branch": "Main Branch"
  }
]
```

### 8. Create Salesman (Admin)

**Endpoint**: `POST /admin/salesman`

**Description**: Create a new salesman via admin endpoint for JavaScript frontend compatibility.

**Authentication**: Admin role required

**Request Body**:
```json
{
  "name": "string",
  "code": "string",
  "phone": "string",
  "address": "string",
  "branch": "string",
  "commission_rate": "decimal"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/salesman \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Doe",
    "code": "JD001",
    "phone": "+1987654321",
    "address": "456 Oak Ave, Town, Country",
    "branch": "Downtown Branch",
    "commission_rate": 7.5
  }'
```

**Response**:
```json
{
  "sal_id": "uuid-string",
  "sal_name": "Jane Doe",
  "sal_phone": "+1987654321",
  "sal_address": "456 Oak Ave, Town, Country",
  "branch": "Downtown Branch",
  "code": "JD001",
  "commission_rate": "7.50"
}
```

### 9. Update Salesman (Admin)

**Endpoint**: `PUT /admin/salesman/{id}`

**Description**: Update a specific salesman by ID via admin endpoint for JavaScript frontend compatibility.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the salesman to update

**Request Body**:
```json
{
  "name": "string",
  "code": "string",
  "phone": "string",
  "address": "string",
  "branch": "string",
  "commission_rate": "decimal"
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/admin/salesman/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Updated",
    "phone": "+1111111111",
    "address": "789 Updated Ave, New Town, Country",
    "branch": "Uptown Branch",
    "commission_rate": 8.0
  }'
```

**Response**:
```json
{
  "sal_id": "uuid-string",
  "sal_name": "Jane Updated",
  "sal_phone": "+1111111111",
  "sal_address": "789 Updated Ave, New Town, Country",
  "branch": "Uptown Branch",
  "code": "JD001",
  "commission_rate": "8.00"
}
```

### 10. Delete Salesman (Admin)

**Endpoint**: `DELETE /admin/salesman/{id}`

**Description**: Delete a salesman by ID via admin endpoint for JavaScript frontend compatibility.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the salesman to delete

**Example**:
```bash
curl -X DELETE http://localhost:8000/admin/salesman/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "success": true,
  "message": "Salesman deleted successfully"
}
```

## Error Handling

All endpoints return standardized error responses:

```json
{
  "error": {
    "type": "http_error",
    "message": "Human-readable error message",
    "status_code": 400,
    "path": "/endpoint/path",
    "timestamp": "2026-02-02T07:00:00.000000"
  }
}
```

Common error types:
- `400 Bad Request`: Invalid input parameters or format
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: Insufficient permissions for the requested action
- `404 Not Found`: Requested resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate code)

## Security Notes

- All endpoints require appropriate role-based access control
- Salesman data is protected by role-based access control
- Audit logs are maintained for all salesman-related actions
- Commission rates are sensitive data accessible only to authorized users

## Production Ready Features

- Async/await implementation for high concurrency
- Pydantic v2 validation
- Proper error handling and logging
- Database transaction safety
- JWT token-based authentication
- Role-based access control
- Input sanitization and validation