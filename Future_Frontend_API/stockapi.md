# Stock API Documentation

This document provides comprehensive documentation for all stock-related endpoints in the Regal POS Backend, including curl commands for testing and integration.

## Authentication

All stock endpoints require authentication with a valid JWT access token. Obtain a token by logging in:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Use the returned `access_token` in the Authorization header:

```bash
-H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## Stock Management Endpoints

### 1. View Stock

**Endpoint**: `GET /admin/ViewStock`

**Description**: View stock with search and branch filtering.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `search_string`: Search term to filter products
- `branches`: Branch to filter by
- `shelf`: Shelf to filter by
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/ViewStock?search_string=product&branches=MainBranch&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
[
  {
    "pro_id": "uuid-string",
    "pro_name": "Product Name",
    "quantity": 50,
    "branch": "MainBranch",
    "ven_name": "Vendor Name",
    "pro_price": 99.99,
    "pro_cost": 79.99,
    "pro_barcode": "1234567890123",
    "pro_dis": 0.0,
    "cat_id_fk": "Category Name",
    "limitedquan": false,
    "brand": "Brand Name",
    "pro_image": "image-path"
  }
]
```

### 2. Adjust Stock

**Endpoint**: `POST /admin/Adjuststock`

**Description**: Adjust stock levels for multiple products.

**Authentication**: Admin role required

**Request Body** (as JSON array):
```json
[
  {
    "pro_name": "Product Name",
    "quantity": 10,
    "stock_id": "uuid-string",
    "status": "IN",
    "frombranch": "MainBranch",
    "tobranch": "SecondaryBranch"
  }
]
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/Adjuststock \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d '[{"pro_name":"Product Name","quantity":10,"stock_id":"uuid-string","status":"IN","frombranch":"MainBranch","tobranch":"SecondaryBranch"}]'
```

**Response**:
```json
"JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL0xlbmd0aCA2MAo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjcyIDcyMCBUZAooU3RvY2sgQWRqdXN0bWVudCBSZXBvcnQpIFRqCkVUCmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDUKdHJhaWxlcgo8PAovU2l6ZSA1Ci9Sb290IDEgMCBSCj4+CgklJUVPRg=="
```

### 3. Save Stock In

**Endpoint**: `POST /admin/SaveStockIn`

**Description**: Save stock in transactions for multiple products.

**Authentication**: Admin role required

**Request Body** (as JSON array):
```json
[
  {
    "ven_name": "Vendor Name",
    "pro_name": "Product Name",
    "pro_price": 99.99,
    "pro_cost": 79.99,
    "quantity": 50,
    "totalCost": 3999.5,
    "pro_barcode": "1234567890123",
    "cat_name": "Category Name",
    "brand": "Brand Name",
    "pro_id": "uuid-string"
  }
]
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/SaveStockIn \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d '[{"ven_name":"Vendor Name","pro_name":"Product Name","pro_price":99.99,"pro_cost":79.99,"quantity":50,"totalCost":3999.5,"pro_barcode":"1234567890123","cat_name":"Category Name","brand":"Brand Name","pro_id":"uuid-string"}]'
```

**Response**:
```json
{
  "message": "Stock in transactions saved successfully",
  "results": [
    {
      "pro_name": "Product Name",
      "new_stock_level": 50,
      "status": "success"
    }
  ]
}
```

### 4. Search Stock

**Endpoint**: `GET /admin/searchstock`

**Description**: Search stock by branch.

**Authentication**: Employee role or higher required

**Query Parameters** (optional):
- `branches`: Branch to filter by

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/searchstock?branches=MainBranch" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
[
  {
    "stock_id": "uuid-string",
    "pro_name": "Product Name",
    "quantity": 50,
    "branch": "MainBranch"
  }
]
```

### 5. Stock Report

**Endpoint**: `POST /admin/StockReport`

**Description**: Generate stock report in PDF format.

**Authentication**: Admin role required

**Request Body** (as form data):
- `cat_name`: Category name to filter by
- `pro_name`: Product name to filter by
- `ven_name`: Vendor name to filter by
- `timezone`: Timezone for the report
- `branches`: Branch to filter by
- `shelf`: Shelf to filter by

**Example**:
```bash
curl -X POST http://localhost:8000/admin/StockReport \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d "cat_name=Electronics&pro_name=Phone&ven_name=Supplier&timezone=UTC&branches=MainBranch&shelf=A1"
```

**Response**:
```json
"JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL0xlbmd0aCA0NAo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjcyIDcyMCBUZAooU3RvY2sgUmVwb3J0KSBUagoKRVQKZW5kc3RyZWFtCmVuZG9iagp4cmVmCjAgNQp0cmFpbGVyCjw8Ci9TaXplIDUKL1Jvb3QgMSAwIFIKPj4KJSVFT0Y="
```

### 6. Daily Inventory Report

**Endpoint**: `POST /admin/Dailyinventoryreport`

**Description**: Generate daily inventory report in PDF format.

**Authentication**: Admin role required

**Example**:
```bash
curl -X POST http://localhost:8000/admin/Dailyinventoryreport \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
"JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL0xlbmd0aCA2MQo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjcyIDcyMCBUZAooRGFpbHkgSW52ZW50b3J5IFJlcG9ydCkgVGoKRVQKZW5kc3RyZWFtCmVuZG9iagp4cmVmCjAgNQp0cmFpbGVyCjw8Ci9TaXplIDUKL1Jvb3QgMSAwIFIKPj4KJSVFT0Y="
```

### 7. Get Stock Detail

**Endpoint**: `POST /admin/GetStockDetail`

**Description**: Get stock details for a specific product.

**Authentication**: Admin role required

**Query Parameters**:
- `pro_name`: Product name to search for

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/GetStockDetail?pro_name=ProductName" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "quantity": 50
}
```

## CRUD Operations Summary

### Create Operations
- `POST /admin/SaveStockIn` - Create stock in transactions

### Read Operations
- `GET /admin/ViewStock` - View stock with filtering
- `GET /admin/searchstock` - Search stock by branch
- `POST /admin/GetStockDetail` - Get specific stock details

### Update Operations
- `POST /admin/Adjuststock` - Adjust stock levels

### Report Operations
- `POST /admin/StockReport` - Generate stock report
- `POST /admin/Dailyinventoryreport` - Generate daily inventory report

## Frontend-Compatible Endpoints

The following capitalized endpoints are provided for JavaScript frontend compatibility:

- `GET /admin/ViewStock` - View stock with search and branch filtering
- `POST /admin/Adjuststock` - Adjust stock levels
- `POST /admin/SaveStockIn` - Save stock in transactions
- `GET /admin/searchstock` - Search stock by branch
- `POST /admin/StockReport` - Generate stock report
- `POST /admin/Dailyinventoryreport` - Generate daily inventory report
- `POST /admin/GetStockDetail` - Get stock detail by product name

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
- Stock data is protected by role-based access control
- Audit logs are maintained for all stock-related actions
- Only admins can modify stock levels and generate reports
- Foreign key constraints prevent deletion of products with stock history

## Production Ready Features

- Async/await implementation for high concurrency
- Pydantic v2 validation
- Proper error handling and logging
- Database transaction safety
- JWT token-based authentication
- Role-based access control
- Input sanitization and validation
- Comprehensive API documentation