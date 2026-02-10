# Salesman API Documentation

This document provides comprehensive documentation for all salesman-related endpoints in the Regal POS Backend with session-based authentication, including curl commands for testing and integration.

## Authentication

All salesman endpoints require session-based authentication. Obtain a session by logging in:

```bash
curl -X POST http://localhost:8000/auth/session-login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

The login response will include a session cookie that will be automatically sent with subsequent requests when using the `-b` flag with curl or proper cookie handling in applications.

## Salesman Management Endpoints

### 1. Get All Salesmen

**Endpoint**: `GET /salesmen/`

**Description**: Get list of salesmen with pagination.

**Authentication**: Employee role or higher required

**Query Parameters** (optional):
- `skip`: Number of records to skip (for pagination) - default 0
- `limit`: Maximum number of records to return (default 100, max 200) - default 100

**Example**:
```bash
curl -X GET "http://localhost:8000/salesmen/?limit=10" \
  -b cookies.txt
```

**Response**:
```json
[
  {
    "id": "uuid-string",
    "name": "John Smith",
    "code": "SM001",
    "phone": "1234567890",
    "address": "123 Main St",
    "branch": "Main Branch",
    "commission_rate": 0.05,
    "created_at": "2026-01-31T11:00:00.000000",
    "updated_at": "2026-01-31T11:00:00.000000"
  }
]
```

### 2. Create Salesman

**Endpoint**: `POST /salesmen/`

**Description**: Create a new salesman.

**Authentication**: Admin role required

**Request Body**:
```json
{
  "name": "string (required)",
  "code": "string (required, unique)",
  "phone": "string (optional)",
  "address": "string (optional)",
  "branch": "string (optional)",
  "commission_rate": "decimal (optional, default 0.0)"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/salesmen/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "John Smith",
    "code": "SM001",
    "phone": "1234567890",
    "address": "123 Main St",
    "branch": "Main Branch",
    "commission_rate": 0.05
  }'
```

**Response**:
```json
{
  "id": "uuid-string",
  "name": "John Smith",
  "code": "SM001",
  "phone": "1234567890",
  "address": "123 Main St",
  "branch": "Main Branch",
  "commission_rate": 0.05,
  "created_at": "2026-01-31T11:00:00.000000",
  "updated_at": "2026-01-31T11:00:00.000000"
}
```

### 3. Get Salesman by ID

**Endpoint**: `GET /salesmen/{salesman_id}`

**Description**: Get a specific salesman by ID.

**Authentication**: Employee role or higher required

**Path Parameter**:
- `{salesman_id}`: UUID of the salesman

**Example**:
```bash
curl -X GET http://localhost:8000/salesmen/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "id": "uuid-string",
  "name": "John Smith",
  "code": "SM001",
  "phone": "1234567890",
  "address": "123 Main St",
  "branch": "Main Branch",
  "commission_rate": 0.05,
  "created_at": "2026-01-31T11:00:00.000000",
  "updated_at": "2026-01-31T11:00:00.000000"
}
```

### 4. Update Salesman

**Endpoint**: `PUT /salesmen/{salesman_id}`

**Description**: Update a specific salesman by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{salesman_id}`: UUID of the salesman to update

**Request Body** (all fields optional):
```json
{
  "name": "string (optional)",
  "code": "string (optional, must be unique)",
  "phone": "string (optional)",
  "address": "string (optional)",
  "branch": "string (optional)",
  "commission_rate": "decimal (optional)"
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/salesmen/uuid-string \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "Updated John Smith",
    "phone": "0987654321"
  }'
```

**Response**:
```json
{
  "id": "uuid-string",
  "name": "Updated John Smith",
  "code": "SM001",
  "phone": "0987654321",
  "address": "123 Main St",
  "branch": "Main Branch",
  "commission_rate": 0.05,
  "created_at": "2026-01-31T11:00:00.000000",
  "updated_at": "2026-01-31T11:01:00.000000"
}
```

### 5. Delete Salesman

**Endpoint**: `DELETE /salesmen/{salesman_id}`

**Description**: Delete a specific salesman by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{salesman_id}`: UUID of the salesman to delete

**Example**:
```bash
curl -X DELETE http://localhost:8000/salesmen/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "message": "Salesman deleted successfully"
}
```

## Frontend-Compatible Salesman Endpoints (in Admin Router)

### 6. Get Salesman Details (Frontend Compatible)

**Endpoint**: `GET /admin/GetSalesman/{id}`

**Description**: Get specific salesman details by ID for JavaScript frontend compatibility.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the salesman

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/GetSalesman/uuid-string" \
  -b cookies.txt
```

**Response**:
```json
{
  "sal_id": "uuid-string",
  "sal_name": "John Smith",
  "sal_phone": "1234567890",
  "sal_address": "123 Main St",
  "branch": "Main Branch"
}
```

### 7. View Salesmen (Frontend Compatible)

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
  -b cookies.txt
```

**Response**:
```json
[
  {
    "sal_id": "uuid-string",
    "sal_name": "John Smith",
    "sal_phone": "1234567890",
    "sal_address": "123 Main St",
    "branch": "Main Branch"
  }
]
```

### 8. Create Salesman (Admin Endpoint)

**Endpoint**: `POST /admin/salesman`

**Description**: Create a new salesman via admin endpoint for JavaScript frontend compatibility.

**Authentication**: Admin role required

**Request Body**:
```json
{
  "name": "string (required)",
  "code": "string (required, unique)",
  "phone": "string (optional)",
  "address": "string (optional)",
  "branch": "string (optional)",
  "commission_rate": "decimal (optional, default 0.0)"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/salesman \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "Jane Doe",
    "code": "SM002",
    "phone": "0987654321",
    "address": "456 Oak Ave",
    "branch": "Secondary Branch",
    "commission_rate": 0.07
  }'
```

**Response**:
```json
{
  "sal_id": "uuid-string",
  "sal_name": "Jane Doe",
  "sal_phone": "0987654321",
  "sal_address": "456 Oak Ave",
  "branch": "Secondary Branch",
  "code": "SM002",
  "commission_rate": "0.07"
}
```

### 9. Update Salesman (Admin Endpoint)

**Endpoint**: `PUT /admin/salesman/{id}`

**Description**: Update a specific salesman by ID via admin endpoint for JavaScript frontend compatibility.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the salesman to update

**Request Body** (all fields optional):
```json
{
  "name": "string (optional)",
  "code": "string (optional, must be unique)",
  "phone": "string (optional)",
  "address": "string (optional)",
  "branch": "string (optional)",
  "commission_rate": "decimal (optional)"
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/admin/salesman/uuid-string \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "Updated Jane Doe",
    "phone": "1111111111"
  }'
```

**Response**:
```json
{
  "sal_id": "uuid-string",
  "sal_name": "Updated Jane Doe",
  "sal_phone": "1111111111",
  "sal_address": "456 Oak Ave",
  "branch": "Secondary Branch",
  "code": "SM002",
  "commission_rate": "0.07"
}
```

### 10. Delete Salesman (Admin Endpoint)

**Endpoint**: `DELETE /admin/salesman/{id}`

**Description**: Delete a specific salesman by ID via admin endpoint for JavaScript frontend compatibility.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the salesman to delete

**Example**:
```bash
curl -X DELETE http://localhost:8000/admin/salesman/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
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
    "timestamp": "2026-01-31T11:00:00.000000"
  }
}
```

Common error types:
- `400 Bad Request`: Invalid input parameters or format
- `401 Unauthorized`: Missing or invalid session cookie
- `403 Forbidden`: Insufficient permissions for the requested action
- `404 Not Found`: Requested resource not found
- `409 Conflict`: Salesman code already exists
- `422 Unprocessable Entity`: Validation error in request body
- `500 Internal Server Error`: Unexpected server error

## Security Notes

- All endpoints require appropriate role-based access control using session cookies
- Salesman data is protected by role-based access control
- Only admins can create, update, or delete salesmen
- Employees and above can view salesman information
- Code uniqueness is enforced at the database level
- Session-based authentication with cookie management for enhanced security
- Protection against JWT token theft from client-side storage
- Instant logout capability across all devices
- Full control over active sessions

## Production Ready Features

- Async/await implementation for high concurrency
- Pydantic v2 validation
- Proper error handling and logging
- Database transaction safety
- Session-based authentication with cookie management
- Role-based access control
- Input sanitization and validation
- Code uniqueness validation
- Comprehensive API documentation
- Server-side session control for better security
- Instant logout capability across all devices
- Better compliance with audit trails and regulations

## Best Practices

- Always use unique codes for salesmen to prevent conflicts
- Regularly review salesman assignments and commissions
- Maintain accurate contact information for all salesmen
- Use proper role-based access control for different operations
- Monitor API usage and access patterns
- Implement proper error handling in client applications
- Follow RESTful API design principles
- Use HTTPS in production environments
- Regular backup of salesman data
- Audit logs for all modifications