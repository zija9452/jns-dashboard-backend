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

### 1. Get All Products

**Endpoint**: `GET /products/`

**Description**: Get list of products with pagination. Cashiers, employees, and admins can view products.

**Authentication**: Cashier role or higher required

**Query Parameters** (optional):
- `skip`: Number of records to skip (for pagination) - default 0
- `limit`: Maximum number of records to return (default 100) - default 100

**Example**:
```bash
curl -X GET "http://localhost:8000/products/?skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
[
  {
    "id": "uuid-string",
    "sku": "PRODUCT-SKU",
    "name": "Product Name",
    "desc": "Product Description",
    "unit_price": "99.99",
    "cost_price": "79.99",
    "tax_rate": "0.00",
    "vendor_id": "uuid-string",
    "stock_level": 50,
    "attributes": "JSON string for extensibility",
    "barcode": "1234567890123",
    "discount": "0.00",
    "category": "Category Name",
    "branch": "Branch Name",
    "limited_qty": false,
    "brand_action": "Brand Name",
    "created_at": "2026-01-30T10:31:18.150552",
    "updated_at": "2026-01-30T10:31:18.150552"
  }
]
```

### 2. Get Product by ID

**Endpoint**: `GET /products/{id}`

**Description**: Get a specific product by ID.

**Authentication**: Cashier role or higher required

**Parameters**:
- `{id}`: UUID of the product

**Example**:
```bash
curl -X GET http://localhost:8000/products/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "id": "uuid-string",
  "sku": "PRODUCT-SKU",
  "name": "Product Name",
  "desc": "Product Description",
  "unit_price": "99.99",
  "cost_price": "79.99",
  "tax_rate": "0.00",
  "vendor_id": "uuid-string",
  "stock_level": 50,
  "attributes": "JSON string for extensibility",
  "barcode": "1234567890123",
  "discount": "0.00",
  "category": "Category Name",
  "branch": "Branch Name",
  "limited_qty": false,
  "brand_action": "Brand Name",
  "created_at": "2026-01-30T10:31:18.150552",
  "updated_at": "2026-01-30T10:31:18.150552"
}
```

### 3. Create Product

**Endpoint**: `POST /products/`

**Description**: Create a new product. Requires admin or employee role.

**Authentication**: Employee role or higher required

**Request Body**:
```json
{
  "sku": "NEW-PRODUCT-SKU",
  "name": "New Product Name",
  "desc": "New Product Description",
  "unit_price": 99.99,
  "cost_price": 79.99,
  "tax_rate": 0.00,
  "vendor_id": "uuid-string",
  "stock_level": 50,
  "attributes": "JSON string for extensibility",
  "barcode": "1234567890123",
  "discount": 0.00,
  "category": "Category Name",
  "branch": "Branch Name",
  "limited_qty": false,
  "brand_action": "Brand Name"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/products/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d '{
    "sku": "NEW-PRODUCT-SKU",
    "name": "New Product Name",
    "desc": "New Product Description",
    "unit_price": 99.99,
    "cost_price": 79.99,
    "stock_level": 50,
    "category": "Category Name",
    "barcode": "1234567890123"
  }'
```

**Response**:
```json
{
  "id": "uuid-string",
  "sku": "NEW-PRODUCT-SKU",
  "name": "New Product Name",
  "desc": "New Product Description",
  "unit_price": "99.99",
  "cost_price": "79.99",
  "tax_rate": "0.00",
  "vendor_id": "uuid-string",
  "stock_level": 50,
  "attributes": "JSON string for extensibility",
  "barcode": "1234567890123",
  "discount": "0.00",
  "category": "Category Name",
  "branch": "Branch Name",
  "limited_qty": false,
  "brand_action": "Brand Name",
  "created_at": "2026-01-30T10:31:18.150552",
  "updated_at": "2026-01-30T10:31:18.150552"
}
```

### 4. Update Product

**Endpoint**: `PUT /products/{id}`

**Description**: Update a specific product by ID. Requires admin or employee role.

**Authentication**: Employee role or higher required

**Parameters**:
- `{id}`: UUID of the product to update

**Request Body** (all fields optional):
```json
{
  "name": "Updated Product Name",
  "desc": "Updated Product Description",
  "unit_price": 109.99,
  "cost_price": 89.99,
  "tax_rate": 0.00,
  "vendor_id": "uuid-string",
  "stock_level": 60,
  "attributes": "Updated JSON string for extensibility",
  "barcode": "1234567890123",
  "discount": 0.00,
  "category": "Updated Category Name",
  "branch": "Updated Branch Name",
  "limited_qty": true,
  "brand_action": "Updated Brand Name"
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/products/uuid-string \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d '{
    "name": "Updated Product Name",
    "unit_price": 109.99,
    "stock_level": 60
  }'
```

**Response**:
```json
{
  "id": "uuid-string",
  "sku": "EXISTING-PRODUCT-SKU",
  "name": "Updated Product Name",
  "desc": "Existing Product Description",
  "unit_price": "109.99",
  "cost_price": "79.99",
  "tax_rate": "0.00",
  "vendor_id": "uuid-string",
  "stock_level": 60,
  "attributes": "JSON string for extensibility",
  "barcode": "1234567890123",
  "discount": "0.00",
  "category": "Category Name",
  "branch": "Branch Name",
  "limited_qty": false,
  "brand_action": "Brand Name",
  "created_at": "2026-01-30T10:31:18.150552",
  "updated_at": "2026-01-30T10:32:18.150552"
}
```

### 5. Delete Product

**Endpoint**: `DELETE /products/{id}`

**Description**: Delete a specific product by ID. Requires admin role.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the product to delete

**Example**:
```bash
curl -X DELETE http://localhost:8000/products/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "message": "Product deleted successfully"
}
```

## Frontend-Compatible Product Endpoints

### 6. Get Product Details (Frontend Compatible)

**Endpoint**: `GET /admin/GetProducts/{id}`

**Description**: Retrieve specific product details by ID in frontend-compatible format.

**Authentication**: Employee role or higher required

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
  "pro_price": 99.99,
  "pro_cost": 79.99,
  "pro_barcode": "1234567890123",
  "pro_dis": 0.0,
  "cat_id_fk": "Category Name",
  "limitedquan": false,
  "branch": "Branch Name",
  "brand": "Brand Name",
  "pro_image": "image-path-or-json-data"
}
```

### 7. View Products (Frontend Compatible)

**Endpoint**: `GET /admin/Viewproduct`

**Description**: View products with search and branch filtering in frontend-compatible format.

**Authentication**: Employee role or higher required

**Query Parameters** (optional):
- `search_string`: Search term to filter products
- `branches`: Branch to filter by
- `skip`: Number of records to skip (for pagination) - default 0
- `limit`: Maximum number of records to return (default 100) - default 100

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/Viewproduct?search_string=product&branches=Main%20Branch&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
[
  {
    "pro_id": "uuid-string",
    "pro_name": "Product Name",
    "pro_price": 99.99,
    "pro_cost": 79.99,
    "pro_barcode": "1234567890123",
    "pro_dis": 0.0,
    "cat_id_fk": "Category Name",
    "limitedquan": false,
    "branch": "Branch Name",
    "brand": "Brand Name",
    "pro_image": "image-path-or-json-data"
  }
]
```

### 8. Get Maximum Product ID

**Endpoint**: `GET /admin/GetMaxProId`

**Description**: Get the maximum product ID for barcode calculation.

**Authentication**: Employee role or higher required

**Example**:
```bash
curl -X GET http://localhost:8000/admin/GetMaxProId \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```
1003
```

### 9. Delete Product (Frontend Compatible)

**Endpoint**: `POST /admin/Deleteproduct/{id}`

**Description**: Delete a product by ID (frontend-compatible endpoint).

**Authentication**: Admin role required

**Parameters**:
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

### 10. Delete Product Image

**Endpoint**: `POST /admin/DeleteProductImage/{id}`

**Description**: Delete product image by product ID.

**Authentication**: Employee role or higher required

**Parameters**:
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

### 11. Create Brand

**Endpoint**: `POST /admin/brand`

**Description**: Add a new brand.

**Authentication**: Employee role or higher required

**Query Parameters**:
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

### 12. Delete Brand

**Endpoint**: `POST /admin/Deletebrand`

**Description**: Delete a brand.

**Authentication**: Employee role or higher required

**Query Parameters**:
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

### 13. Get Stock Detail

**Endpoint**: `POST /admin/GetStockDetail`

**Description**: Get stock details for a specific product.

**Authentication**: Employee role or higher required

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
- `POST /products/` - Create a new product
- `POST /admin/brand` - Create a new brand

### Read Operations
- `GET /products/` - Get all products
- `GET /products/{id}` - Get specific product
- `GET /admin/GetProducts/{id}` - Get product in frontend format
- `GET /admin/Viewproduct` - Get products in frontend format
- `GET /admin/GetMaxProId` - Get maximum product ID

### Update Operations
- `PUT /products/{id}` - Update a product

### Delete Operations
- `DELETE /products/{id}` - Delete a product (admin only)
- `POST /admin/Deleteproduct/{id}` - Delete a product (frontend compatible, admin only)
- `POST /admin/DeleteProductImage/{id}` - Delete product image
- `POST /admin/Deletebrand` - Delete a brand

## Database Schema

The Product model includes the following fields:
- `id`: UUID (Primary Key)
- `sku`: String (Unique, max 50 chars) - Product identifier
- `name`: String (max 100 chars) - Product name
- `desc`: String (Optional) - Product description
- `unit_price`: Decimal (10,2) - Selling price
- `cost_price`: Decimal (10,2) - Cost price
- `tax_rate`: Decimal (5,2) - Tax rate
- `vendor_id`: UUID (Foreign Key) - Associated vendor
- `stock_level`: Integer - Available quantity
- `attributes`: String (Optional) - JSON field for extensibility (used for image paths)
- `barcode`: String (Optional, Unique, max 50 chars) - Barcode
- `discount`: Decimal (5,2) - Discount percentage
- `category`: String (Optional, max 50 chars) - Product category
- `branch`: String (Optional, max 50 chars) - Branch location
- `limited_qty`: Boolean - Limited quantity flag
- `brand_action`: String (Optional, max 100 chars) - Brand information
- `created_at`: DateTime - Creation timestamp
- `updated_at`: DateTime - Update timestamp

## Image Storage

Product images are stored in the `attributes` field as JSON strings, allowing for flexible storage of image paths and other extensible product information.

## Barcode Support

The schema includes a dedicated `barcode` field that supports UPC, EAN, and other barcode formats up to 50 characters.

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

- All endpoints require role-based authentication
- Product data is protected by role-based access control
- Audit logs are maintained for all product-related actions
- Only admins can delete products for security reasons
- Image management is available to employees and above

## Production Ready Features

- Async/await implementation for high concurrency
- Pydantic v2 validation
- Proper error handling and logging
- Database transaction safety
- JWT token-based authentication
- Role-based access control
- Input sanitization and validation
- Flexible attributes field for extensibility
- Comprehensive API documentation