# Product API Requirements Analysis

## Current State
The existing product API in the Regal POS Backend provides basic CRUD operations:
- GET /products/ - Get list of products
- POST /products/ - Create a new product
- GET /products/{id} - Get specific product
- PUT /products/{id} - Update a product
- DELETE /products/{id} - Delete a product

## Required Fields from JavaScript Code
The JavaScript frontend expects these fields for products:
- `pro_name` - Product name
- `pro_price` - Product price
- `pro_cost` - Product cost
- `pro_barcode` - Product barcode
- `pro_dis` - Product discount
- `cat_id_fk` - Category ID (foreign key)
- `limitedquan` - Limited quantity
- `branch` - Branch assignment
- `brand` - Brand name
- `pro_id` - Product ID
- `pro_image` - Product image

## Missing Endpoints Required by JavaScript Code

### 1. GET `/Admin/GetProducts/{id}`
- **Description**: Retrieve specific product details by ID
- **Response**: Product object with fields mapped to expected JavaScript properties
- **Required**: Currently missing

### 2. GET `/Admin/Viewproduct`
- **Description**: View products with search and branch filtering capabilities
- **Parameters**:
  - `searchString` (optional): Search term for product filtering
  - `branches` (optional): Branch filter
- **Response**: Paginated list of products matching criteria
- **Required**: Currently missing

### 3. GET `/Admin/GetMaxProId`
- **Description**: Get the maximum product ID for barcode calculation
- **Response**: Integer representing the highest product ID
- **Required**: Currently missing

### 4. POST `/Admin/Deleteproduct/{id}`
- **Description**: Delete a product by ID
- **Response**:
  - `success`: boolean indicating success
  - `message`: success/error message
- **Required**: Currently missing (existing DELETE endpoint returns different format)

### 5. POST `/Admin/DeleteProductImage/{id}`
- **Description**: Delete product image by product ID
- **Response**:
  - `success`: boolean indicating success
  - `message`: success/error message
- **Required**: Currently missing

### 6. POST `/Admin/brand`
- **Description**: Add a new brand
- **Request Body**: Object with brand information
- **Response**:
  - `success`: boolean indicating success
  - `ID`: ID of the created brand
  - `shelf`: name of the created brand
- **Required**: Currently missing

### 7. POST `/Admin/Deletebrand`
- **Description**: Delete a brand
- **Request Body**: Brand name to delete
- **Response**:
  - `success`: boolean indicating success
  - `message`: success/error message
- **Response**: Updated list of brands
- **Required**: Currently missing

### 8. POST `/Admin/GetStockDetail`
- **Description**: Get stock details for a specific product
- **Request Body**: Product name
- **Response**:
  - `quantity`: Available stock quantity
  - `error`: Error message if product not found
- **Required**: Currently missing

### 9. GET `/Admin/GetCustomerVendorByBranch`
- **Description**: Get categories and vendors by branch
- **Parameters**:
  - `branch`: Branch name to filter by
- **Response**:
  - `categories`: Array of category objects with `cat_id` and `cat_name`
- **Required**: Currently missing

## Field Mapping Requirements

The existing Product model fields need to be mapped to JavaScript expected fields:
- `name` → `pro_name`
- `unit_price` → `pro_price`
- `cost_price` → `pro_cost`
- `barcode` → `pro_barcode`
- `discount` → `pro_dis`
- `category` → `cat_id_fk` (need category lookup)
- `limited_qty` → `limitedquan`
- `branch` → `branch`
- `brand_action` → `brand`
- `id` → `pro_id`
- `attributes` (or new field) → `pro_image`

## Required Enhancements

### 1. Enhanced Product Model
- Add image field to store product images
- Add proper category relationship (currently using string field)
- Add brand field separate from brand_action

### 2. Category Management
- Create Category model and endpoints
- Implement category lookup functionality
- Link products to categories via foreign key

### 3. Brand Management
- Create Brand model and endpoints
- Implement brand lookup functionality
- Separate brand from product attributes

### 4. Image Management
- Add product image upload/delete functionality
- Store image paths in product model

### 5. Advanced Search & Filtering
- Implement search functionality for products
- Add branch-based filtering
- Add pagination support for large datasets

## Security Considerations
- All endpoints should require appropriate authentication (admin/cashier/employee)
- Proper validation of all input parameters
- Sanitize and validate all user inputs
- Prevent unauthorized access to product management features

## Implementation Priority
1. **High Priority**: GET `/Admin/GetProducts/{id}`, GET `/Admin/Viewproduct`
2. **Medium Priority**: GET `/Admin/GetMaxProId`, POST `/Admin/Deleteproduct/{id}`
3. **Low Priority**: Brand management, image management, category management