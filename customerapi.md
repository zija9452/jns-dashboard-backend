# Customer API Documentation

This document provides comprehensive documentation for all customer-related endpoints in the Regal POS Backend, including curl commands for testing and integration.

## Authentication

All customer endpoints require authentication with a valid JWT access token. Obtain a token by logging in:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Use the returned `access_token` in the Authorization header:

```bash
-H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## Customer Management Endpoints

### 1. Get Customer Details

**Endpoint**: `GET /admin/GetCustomer/{id}`

**Description**: Retrieve specific customer details by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the customer

**Example**:
```bash
curl -X GET http://localhost:8000/admin/GetCustomer/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "cus_id": "uuid-string",
  "cus_name": "Customer Name",
  "cus_phone": "1234567890",
  "cus_cnic": "",
  "cus_address": "123 Main St",
  "cus_sal_id_fk": "1",
  "branch": ""
}
```

### 2. View Customers

**Endpoint**: `GET /admin/Viewcustomer`

**Description**: View customers with search and branch filtering.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `search_string`: Search term to filter customers
- `branches`: Branch to filter by
- `searchphone`: Phone number to search by
- `searchaddress`: Address to search by
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/Viewcustomer?search_string=john&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
[
  {
    "cus_id": "uuid-string",
    "cus_name": "John Doe",
    "cus_phone": "1234567890",
    "cus_cnic": "",
    "cus_address": "123 Main St",
    "cus_sal_id_fk": "1",
    "branch": "",
    "cus_balance": 1000.0
  }
]
```

### 3. Delete Customer

**Endpoint**: `POST /admin/Deletecustomer/{id}`

**Description**: Delete a customer by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the customer to delete

**Example**:
```bash
curl -X POST http://localhost:8000/admin/Deletecustomer/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "success": true,
  "message": "Customer deleted successfully"
}
```

### 4. Get Customer Balance

**Endpoint**: `POST /admin/Getcustomerbalance`

**Description**: Get customer balance by branch.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `branches`: Branch to get balance for

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/Getcustomerbalance?branches=MainBranch" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "cus_balance": 5000.0
}
```

### 5. Customer View Report

**Endpoint**: `POST /admin/Customerviewreport`

**Description**: Generate customer view report in PDF format.

**Authentication**: Admin role required

**Request Body** (as JSON):
- `timezone`: Client's timezone

**Example**:
```bash
curl -X POST http://localhost:8000/admin/Customerviewreport \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d '{"timezone":"UTC"}'
```

**Response**:
```json
"JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL0xlbmd0aCA0NAo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjcyIDcyMCBUZAooQ3VzdG9tZXIgUmVwb3J0KSBUagpFVAplbmRzdHJlYW0KZW5kb2JqCnhyZWYKMCA1CnRyYWlsZXIKPDwKL1NpemUgNQovUm9vdCAxIDAgUgo+PgolJUVPRg=="
```

### 6. Get Customer/Vendor by Branch

**Endpoint**: `GET /admin/GetCustomerVendorByBranch`

**Description**: Get salesmen by branch for customer form.

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

## Standard Endpoints (via customers router)

### 7. Get All Customers

**Endpoint**: `GET /customers/`

**Description**: Get list of customers with pagination.

**Authentication**: Cashier role or higher required

**Query Parameters**:
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/customers/?limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 8. Create Customer

**Endpoint**: `POST /customers/`

**Description**: Create a new customer.

**Authentication**: Admin role required

**Request Body**:
```json
{
  "name": "Customer Name",
  "contacts": "{\"phone\":\"1234567890\",\"email\":\"customer@example.com\"}",
  "billing_addr": "{\"street\":\"123 Main St\",\"city\":\"City\",\"country\":\"Country\"}",
  "shipping_addr": "{\"street\":\"123 Main St\",\"city\":\"City\",\"country\":\"Country\"}",
  "credit_limit": 1000.0
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/customers/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d '{"name":"New Customer","contacts":"{\"phone\":\"1234567890\",\"email\":\"customer@example.com\"}","billing_addr":"{\"street\":\"123 Main St\",\"city\":\"City\",\"country\":\"Country\"}","credit_limit":1000.0}'
```

### 9. Get Customer by ID

**Endpoint**: `GET /customers/{customer_id}`

**Description**: Get a specific customer by ID.

**Authentication**: Cashier role or higher required

**Example**:
```bash
curl -X GET http://localhost:8000/customers/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 10. Update Customer

**Endpoint**: `PUT /customers/{customer_id}`

**Description**: Update a specific customer by ID.

**Authentication**: Employee role or higher required

**Example**:
```bash
curl -X PUT http://localhost:8000/customers/uuid-string \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d '{"name":"Updated Customer Name","credit_limit":2000.0}'
```

### 11. Delete Customer (Standard)

**Endpoint**: `DELETE /customers/{customer_id}`

**Description**: Delete a specific customer by ID.

**Authentication**: Admin role required

**Example**:
```bash
curl -X DELETE http://localhost:8000/customers/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

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
- Customer data is protected by role-based access control
- Audit logs are maintained for all customer-related actions
- Data validation and sanitization applied

## Production Ready Features

- Async/await implementation for high concurrency
- Pydantic v2 validation
- Proper error handling and logging
- Database transaction safety
- JWT token-based authentication
- Role-based access control
- Input sanitization and validation