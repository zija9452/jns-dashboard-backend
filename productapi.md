# Product API Documentation

This document provides comprehensive documentation for all product-related endpoints in the Regal POS Backend, including curl commands for testing and integration.

## Authentication

All product endpoints require authentication with a valid JWT access token. Obtain a token by logging in:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Use the returned `access_token` in the Authorization header:

```bash
-H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## Product Management Endpoints

### 1. Get Maximum Product ID

**Endpoint**: `GET /admin/GetMaxProId`

**Description**: Get the maximum product ID for barcode calculation.

**Authentication**: Admin role required

**Example**:
```bash
curl -X GET http://localhost:8000/admin/GetMaxProId \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
1005
```

### 2. Get Product Details

**Endpoint**: `GET /admin/GetProducts/{id}`

**Description**: Retrieve specific product details by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the product

**Example**:
```bash
curl -X GET http://localhost:8000/admin/GetProducts/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "pro_id": "uuid-string",
  "pro_name": "Product Name",
  "pro_price": 100.0,
  "pro_cost": 80.0,
  "pro_barcode": "",
  "pro_dis": 0.0,
  "cat_id_fk": "",
  "limitedquan": false,
  "branch": "",
  "brand": "",
  "pro_image": ""
}
```

### 3. View Products

**Endpoint**: `GET /admin/Viewproduct`

**Description**: View products with search and branch filtering.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `search_string`: Search term to filter products
- `branches`: Branch to filter by
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/Viewproduct?search_string=laptop&branches=Main%20Branch&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
[
  {
    "pro_id": "uuid-string",
    "pro_name": "Laptop",
    "pro_price": 1000.0,
    "pro_cost": 800.0,
    "pro_barcode": "",
    "pro_dis": 0.0,
    "cat_id_fk": "electronics",
    "limitedquan": false,
    "branch": "",
    "brand": "",
    "pro_image": ""
  }
]
```

### 4. Delete Product

**Endpoint**: `POST /admin/Deleteproduct/{id}`

**Description**: Delete a product by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the product to delete

**Example**:
```bash
curl -X POST http://localhost:8000/admin/Deleteproduct/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "success": true,
  "message": "Product deleted successfully"
}
```

### 5. Delete Product Image

**Endpoint**: `POST /admin/DeleteProductImage/{id}`

**Description**: Delete product image by product ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the product whose image to delete

**Example**:
```bash
curl -X POST http://localhost:8000/admin/DeleteProductImage/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "success": true,
  "message": "Product image deleted successfully"
}
```

### 6. Add Brand

**Endpoint**: `POST /admin/brand`

**Description**: Add a new brand.

**Authentication**: Admin role required

**Request Body** (as query parameter):
- `brand`: Brand name to add

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/brand?brand=NewBrand" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "success": true,
  "ID": 1,
  "shelf": "NewBrand"
}
```

### 7. Delete Brand

**Endpoint**: `POST /admin/Deletebrand`

**Description**: Delete a brand.

**Authentication**: Admin role required

**Request Body** (as query parameter):
- `brand`: Brand name to delete

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/Deletebrand?brand=OldBrand" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "success": true,
  "message": "Brand 'OldBrand' deleted successfully"
}
```

### 8. Get Stock Detail

**Endpoint**: `POST /admin/GetStockDetail`

**Description**: Get stock details for a specific product.

**Authentication**: Admin role required

**Request Body** (as query parameter):
- `pro_name`: Product name to get stock for

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
Or if not found:
```json
{
  "error": "Product not found"
}
```

### 9. Get Categories by Branch

**Endpoint**: `GET /admin/GetCustomerVendorByBranch`

**Description**: Get categories by branch.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `branch`: Branch to filter categories by

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/GetCustomerVendorByBranch?branch=Main%20Branch" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "categories": [
    {
      "cat_id": "1",
      "cat_name": "Electronics"
    },
    {
      "cat_id": "2",
      "cat_name": "Clothing"
    },
    {
      "cat_id": "3",
      "cat_name": "Home & Garden"
    },
    {
      "cat_id": "4",
      "cat_name": "Books"
    },
    {
      "cat_id": "5",
      "cat_name": "Sports"
    }
  ]
}
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

- All endpoints require admin role authentication
- Product data is protected by role-based access control
- Audit logs are maintained for all product-related actions

## Production Ready Features

- Async/await implementation for high concurrency
- Pydantic v2 validation
- Proper error handling and logging
- Database transaction safety
- JWT token-based authentication
- Role-based access control
- Input sanitization and validation