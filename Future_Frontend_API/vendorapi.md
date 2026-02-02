# Vendor API Documentation

This document provides comprehensive documentation for all vendor-related endpoints in the Regal POS Backend, including curl commands for testing and integration.

## Authentication

All vendor endpoints require authentication with a valid JWT access token. Obtain a token by logging in:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Use the returned `access_token` in the Authorization header:

```bash
-H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## Vendor Management Endpoints

### 1. Get Vendor Details

**Endpoint**: `GET /admin/GetVendor/{id}`

**Description**: Retrieve specific vendor details by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the vendor

**Example**:
```bash
curl -X GET http://localhost:8000/admin/GetVendor/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "ven_id": "uuid-string",
  "ven_name": "Vendor Name",
  "ven_phone": "1234567890",
  "ven_address": "123 Main St",
  "branch": ""
}
```

### 2. View Vendors

**Endpoint**: `GET /admin/Viewvendor`

**Description**: View vendors with search and branch filtering.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `search_string`: Search term to filter vendors
- `branches`: Branch to filter by
- `searchphone`: Phone number to search by
- `searchaddress`: Address to search by
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/Viewvendor?search_string=vendor&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
[
  {
    "ven_id": "uuid-string",
    "ven_name": "Vendor Name",
    "ven_phone": "1234567890",
    "ven_address": "123 Main St",
    "branch": ""
  }
]
```

### 3. Delete Vendor

**Endpoint**: `POST /admin/Deletevendor/{id}`

**Description**: Delete a vendor by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the vendor to delete

**Example**:
```bash
curl -X POST http://localhost:8000/admin/Deletevendor/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "success": true,
  "message": "Vendor deleted successfully"
}
```

### 4. Get Vendor Balance

**Endpoint**: `POST /admin/Getvendorbalance`

**Description**: Get vendor balance by branch.

**Authentication**: Admin role required

**Request Body** (as form data):
- `branches`: Branch to get balance for (optional)

**Example**:
```bash
curl -X POST http://localhost:8000/admin/Getvendorbalance \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d "branches=MainBranch"
```

**Response**:
```json
{
  "cus_balance": 5000.0
}
```

### 5. Vendor View Report

**Endpoint**: `POST /admin/Vendorviewreport`

**Description**: Generate vendor view report in PDF format.

**Authentication**: Admin role required

**Example**:
```bash
curl -X POST http://localhost:8000/admin/Vendorviewreport \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
"JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL0xlbmd0aCA0NAo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjcyIDcyMCBUZAooVmVuZG9yIFJlcG9ydCkgVGoKRVQKZW5kc3RyZWFtCmVuZG9iagp4cmVmCjAgNQp0cmFpbGVyCjw8Ci9TaXplIDUKL1Jvb3QgMSAwIFIKPj4KJSVFT0Y="
```

### 6. Get Customer/Vendor by Branch

**Endpoint**: `GET /admin/GetCustomerVendorByBranch`

**Description**: Get salesmen by branch for vendor form.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `branch`: Branch to filter by

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/GetCustomerVendorByBranch?branch=MainBranch" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "salesmans": [
    {
      "sal_id": "1",
      "sal_name": "John Smith"
    },
    {
      "sal_id": "2",
      "sal_name": "Jane Doe"
    }
  ]
}
```

## Standard Endpoints (via vendors router)

### 7. Get All Vendors

**Endpoint**: `GET /vendors/`

**Description**: Get list of vendors with pagination.

**Authentication**: Employee role or higher required

**Query Parameters**:
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/vendors/?limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 8. Create Vendor

**Endpoint**: `POST /vendors/`

**Description**: Create a new vendor.

**Authentication**: Admin role required

**Request Body** (as JSON):
```json
{
  "name": "Vendor Name",
  "contacts": "{\"phone\":\"1234567890\",\"email\":\"vendor@example.com\",\"address\":\"123 Main St\"}",
  "terms": "Payment terms"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/vendors/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d '{"name":"New Vendor","contacts":"{\"phone\":\"1234567890\",\"email\":\"vendor@example.com\",\"address\":\"123 Main St\"}","terms":"Net 30"}'
```

### 9. Get Vendor by ID

**Endpoint**: `GET /vendors/{vendor_id}`

**Description**: Get a specific vendor by ID.

**Authentication**: Employee role or higher required

**Example**:
```bash
curl -X GET http://localhost:8000/vendors/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 10. Update Vendor

**Endpoint**: `PUT /vendors/{vendor_id}`

**Description**: Update a specific vendor by ID.

**Authentication**: Admin role required

**Example**:
```bash
curl -X PUT http://localhost:8000/vendors/uuid-string \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d '{"name":"Updated Vendor Name","terms":"Updated terms"}'
```

### 11. Delete Vendor (Standard)

**Endpoint**: `DELETE /vendors/{vendor_id}`

**Description**: Delete a specific vendor by ID.

**Authentication**: Admin role required

**Example**:
```bash
curl -X DELETE http://localhost:8000/vendors/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## Frontend-Compatible Endpoints

The following capitalized endpoints are provided for JavaScript frontend compatibility:

- `GET /admin/GetVendor/{id}` - Same as `/admin/getvendor/{id}`
- `GET /admin/Viewvendor` - Same as `/admin/viewvendor`
- `POST /admin/Deletevendor/{id}` - Same as `/admin/deletevendor/{id}`
- `POST /admin/Getvendorbalance` - Same as `/admin/getvendorbalance`
- `POST /admin/Vendorviewreport` - Same as `/admin/vendorviewreport`
- `GET /admin/GetCustomerVendorByBranch` - Same as `/admin/getcustomervendorbybranch`

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

- All endpoints require appropriate role authentication
- Vendor data is protected by role-based access control
- Audit logs are maintained for all vendor-related actions
- Foreign key constraints prevent deletion of vendors with related transactions

## Production Ready Features

- Async/await implementation for high concurrency
- Pydantic v2 validation
- Proper error handling and logging
- Database transaction safety
- JWT token-based authentication
- Role-based access control
- Input sanitization and validation