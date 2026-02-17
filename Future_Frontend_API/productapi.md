# Product API Documentation - Session-Based Authentication

This document provides comprehensive documentation for all product-related endpoints in the Regal POS Backend with session-based authentication, including curl commands for testing and integration.

## Authentication

All product endpoints require session-based authentication. Obtain a session by logging in:

```bash
curl -X POST http://localhost:8000/auth/session-login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

The login response will include a session cookie that will be automatically sent with subsequent requests when using the `-b` flag with curl or proper cookie handling in applications.

## Product Management Endpoints

### 1. Get All Products

**Endpoint**: `GET /products/`

**Description**: Get list of products with pagination. Admins and cashiers can view products.

**Authentication**: Admin or cashier role required

**Query Parameters** (optional):
- `skip`: Number of records to skip (for pagination) - default 0
- `limit`: Maximum number of records to return (default 100) - default 100

**Example**:
```bash
curl -X GET "http://localhost:8000/products/?skip=0&limit=10" \
  -b cookies.txt
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

**Authentication**: Admin or cashier role required

**Parameters**:
- `{id}`: UUID of the product

**Example**:
```bash
curl -X GET http://localhost:8000/products/uuid-string \
  -b cookies.txt
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

**Description**: Create a new product. Requires employee role.

**Authentication**: Employee role required

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
  -b cookies.txt \
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

**Description**: Update a specific product by ID. Requires employee role.

**Authentication**: Employee role required

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
  -b cookies.txt \
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
  -b cookies.txt
```

**Response**:
```json
{
  "message": "Product deleted successfully"
}
```

## Frontend-Compatible Product Endpoints

### 6. Get Product Details (Frontend Compatible)

**Endpoint**: `GET /products/get-products/{id}`

**Description**: Retrieve specific product details by ID in frontend-compatible format.

**Authentication**: Admin, cashier, or employee role required

**Parameters**:
- `{id}`: UUID of the product

**Example**:
```bash
curl -X GET http://localhost:8000/products/get-products/uuid-string \
  -b cookies.txt
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

**Endpoint**: `GET /products/view-product`

**Description**: View products with search and branch filtering in frontend-compatible format.

**Authentication**: Admin, cashier, or employee role required

**Query Parameters** (optional):
- `search_string`: Search term to filter products
- `branches`: Branch to filter by
- `skip`: Number of records to skip (for pagination) - default 0
- `limit`: Maximum number of records to return (default 100) - default 100

**Example**:
```bash
curl -X GET "http://localhost:8000/products/view-product?search_string=product&branches=Main%20Branch&limit=10" \
  -b cookies.txt
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

**Endpoint**: `GET /products/get-max-pro-id`

**Description**: Get the maximum product ID for barcode calculation.

**Authentication**: Employee role required

**Example**:
```bash
curl -X GET http://localhost:8000/products/get-max-pro-id \
  -b cookies.txt
```

**Response**:
```
1003
```

### 9. Delete Product (Frontend Compatible)

**Endpoint**: `POST /products/delete-product/{id}`

**Description**: Delete a product by ID (frontend-compatible endpoint).

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the product to delete

**Example**:
```bash
curl -X POST http://localhost:8000/products/delete-product/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "success": true,
  "message": "Product deleted successfully"
}
```

### 10. Delete Product Image

**Endpoint**: `POST /products/delete-product-image/{id}`

**Description**: Delete product image by product ID.

**Authentication**: Employee role required

**Parameters**:
- `{id}`: UUID of the product whose image to delete

**Example**:
```bash
curl -X POST http://localhost:8000/products/delete-product-image/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "success": true,
  "message": "Product image deleted successfully"
}
```

### 11. Create Brand

**Endpoint**: `POST /products/brand`

**Description**: Add a new brand.

**Authentication**: Employee role required

**Query Parameters**:
- `brand`: Brand name to add

**Example**:
```bash
curl -X POST "http://localhost:8000/products/brand?brand=NewBrand" \
  -b cookies.txt
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

**Endpoint**: `POST /products/delete-brand`

**Description**: Delete a brand.

**Authentication**: Employee role required

**Query Parameters**:
- `brand`: Brand name to delete

**Example**:
```bash
curl -X POST "http://localhost:8000/products/delete-brand?brand=OldBrand" \
  -b cookies.txt
```

**Response**:
```json
{
  "success": true,
  "message": "Brand 'OldBrand' deleted successfully"
}
```

### 13. Get Stock Detail

**Endpoint**: `POST /products/get-stock-detail`

**Description**: Get stock details for a specific product.

**Authentication**: Employee role required

**Query Parameters**:
- `pro_name`: Product name to search for

**Example**:
```bash
curl -X POST "http://localhost:8000/products/get-stock-detail?pro_name=ProductName" \
  -b cookies.txt
```

**Response**:
```json
{
  "quantity": 50
}
```

---

## Category Management Endpoints

### 14. Create Category

**Endpoint**: `POST /category/`

**Description**: Add a new category with name and branch.

**Authentication**: Employee role required

**Request Body**:
```json
{
  "name": "European Sports",
  "branch": "Light House"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/category/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "European Sports",
    "branch": "Light House"
  }'
```

**Response**:
```json
{
  "id": "uuid-string",
  "name": "European Sports",
  "branch": "Light House",
  "created_at": "2026-02-17T10:00:00.000000"
}
```

### 15. Get All Categories

**Endpoint**: `GET /category/`

**Description**: Get all categories with optional branch filter.

**Authentication**: Employee role required

**Query Parameters**:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100)
- `branch`: Filter by branch name (optional)

**Example**:
```bash
curl -X GET "http://localhost:8000/category/?skip=0&limit=100&branch=Light%20House" \
  -b cookies.txt
```

**Response**:
```json
[
  {
    "id": "uuid-string",
    "name": "European Sports",
    "branch": "Light House",
    "created_at": "2026-02-17T10:00:00.000000"
  },
  {
    "id": "uuid-string-2",
    "name": "Casual Wear",
    "branch": "Light House",
    "created_at": "2026-02-17T11:00:00.000000"
  }
]
```

### 16. Get Category by ID

**Endpoint**: `GET /category/{id}`

**Description**: Get a specific category by ID.

**Authentication**: Employee role required

**Parameters**:
- `{id}`: UUID of the category

**Example**:
```bash
curl -X GET http://localhost:8000/category/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "id": "uuid-string",
  "name": "European Sports",
  "branch": "Light House",
  "created_at": "2026-02-17T10:00:00.000000"
}
```

### 17. Update Category

**Endpoint**: `PUT /category/{id}`

**Description**: Update a specific category by ID.

**Authentication**: Employee role required

**Parameters**:
- `{id}`: UUID of the category to update

**Request Body** (all fields optional):
```json
{
  "name": "Updated Category Name",
  "branch": "Updated Branch"
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/category/uuid-string \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "Updated Category Name"
  }'
```

**Response**:
```json
{
  "id": "uuid-string",
  "name": "Updated Category Name",
  "branch": "Light House",
  "created_at": "2026-02-17T10:00:00.000000"
}
```

### 18. Delete Category

**Endpoint**: `DELETE /category/{id}`

**Description**: Delete a category by ID.

**Authentication**: Employee role required

**Parameters**:
- `{id}`: UUID of the category to delete

**Example**:
```bash
curl -X DELETE http://localhost:8000/category/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "message": "Category deleted successfully"
}
```

---

## Brand Management Endpoints

### 19. Create Brand

**Endpoint**: `POST /brand/`

**Description**: Add a new brand with name only.

**Authentication**: Employee role required

**Request Body**:
```json
{
  "name": "Nike"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/brand/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "Nike"
  }'
```

**Response**:
```json
{
  "id": "uuid-string",
  "name": "Nike",
  "created_at": "2026-02-17T10:00:00.000000"
}
```

### 20. Get All Brands

**Endpoint**: `GET /brand/`

**Description**: Get all brands.

**Authentication**: Employee role required

**Query Parameters**:
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum number of records to return (default: 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/brand/?skip=0&limit=100" \
  -b cookies.txt
```

**Response**:
```json
[
  {
    "id": "uuid-string",
    "name": "Nike",
    "created_at": "2026-02-17T10:00:00.000000"
  },
  {
    "id": "uuid-string-2",
    "name": "Adidas",
    "created_at": "2026-02-17T11:00:00.000000"
  }
]
```

### 21. Get Brand by ID

**Endpoint**: `GET /brand/{id}`

**Description**: Get a specific brand by ID.

**Authentication**: Employee role required

**Parameters**:
- `{id}`: UUID of the brand

**Example**:
```bash
curl -X GET http://localhost:8000/brand/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "id": "uuid-string",
  "name": "Nike",
  "created_at": "2026-02-17T10:00:00.000000"
}
```

### 22. Update Brand

**Endpoint**: `PUT /brand/{id}`

**Description**: Update a specific brand by ID.

**Authentication**: Employee role required

**Parameters**:
- `{id}`: UUID of the brand to update

**Request Body** (all fields optional):
```json
{
  "name": "Updated Brand Name"
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/brand/uuid-string \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "Updated Brand Name"
  }'
```

**Response**:
```json
{
  "id": "uuid-string",
  "name": "Updated Brand Name",
  "created_at": "2026-02-17T10:00:00.000000"
}
```

### 23. Delete Brand

**Endpoint**: `DELETE /brand/{id}`

**Description**: Delete a brand by ID.

**Authentication**: Employee role required

**Parameters**:
- `{id}`: UUID of the brand to delete

**Example**:
```bash
curl -X DELETE http://localhost:8000/brand/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "message": "Brand deleted successfully"
}
```

## CRUD Operations Summary

### Create Operations
- `POST /products/` - Create a new product
- `POST /category/` - Create a new category
- `POST /brand/` - Create a new brand

### Read Operations
- `GET /products/` - Get all products
- `GET /products/{id}` - Get specific product
- `GET /products/get-products/{id}` - Get product in frontend format
- `GET /products/view-product` - Get products in frontend format
- `GET /products/get-max-pro-id` - Get maximum product ID
- `GET /category/` - Get all categories
- `GET /category/{id}` - Get specific category
- `GET /brand/` - Get all brands
- `GET /brand/{id}` - Get specific brand

### Update Operations
- `PUT /products/{id}` - Update a product
- `PUT /category/{id}` - Update a category
- `PUT /brand/{id}` - Update a brand

### Delete Operations
- `DELETE /products/{id}` - Delete a product (admin only)
- `POST /products/delete-product/{id}` - Delete a product (frontend compatible, admin only)
- `POST /products/delete-product-image/{id}` - Delete product image
- `DELETE /category/{id}` - Delete a category
- `DELETE /brand/{id}` - Delete a brand

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

- All endpoints require role-based authentication using session cookies
- Product data is protected by role-based access control
- Audit logs are maintained for all product-related actions
- Only admins can delete products for security reasons
- Image management is available to employees and above

## Session-Based Authentication Benefits

- Server-side session control for better security
- Instant logout capability across all devices
- Full control over active sessions
- Better compliance with audit trails and regulations
- Protection against JWT token theft from client-side storage

## Production Ready Features

- Async/await implementation for high concurrency
- Pydantic v2 validation
- Proper error handling and logging
- Database transaction safety
- Session-based authentication with cookie management
- Role-based access control
- Input sanitization and validation
- Flexible attributes field for extensibility
- Comprehensive API documentation