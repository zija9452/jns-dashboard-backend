# Stock API Documentation

This document provides comprehensive documentation for all stock-related endpoints in the Regal POS Backend with session-based authentication, including curl commands for testing and integration.

## Authentication

All stock endpoints require session-based authentication. Obtain a session by logging in:

```bash
curl -X POST http://localhost:8000/auth/session-login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

The login response will include a session cookie that will be automatically sent with subsequent requests when using the `-b` flag with curl or proper cookie handling in applications.

## Stock Management Endpoints

### 1. View Stock

**Endpoint**: `GET /admin/ViewStock`

**Description**: View stock with search and branch filtering.

**Authentication**: Admin role required

**Purpose**: Displays all stock items with filtering options. This is for viewing existing inventory only, no modifications made.

**When to use**: When you want to see current stock levels and product details.

**Query Parameters** (optional):
- `search_string`: Search term to filter products
- `branches`: Branch to filter by
- `shelf`: Shelf to filter by
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/ViewStock?search_string=product&branches=MainBranch&limit=10" \
  -b cookies.txt
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

**Purpose**: Modifies existing stock quantities up or down. This is for changing existing inventory levels.

**When to use**: When you need to manually adjust stock quantities (increase/decrease) for existing products.

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
  -b cookies.txt \
  -d '[{"pro_name":"Product Name","quantity":10,"stock_id":"uuid-string","status":"IN","frombranch":"MainBranch","tobranch":"SecondaryBranch"}]'
```

**Response**:
```json
"JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL0xlbmd0aCA2MAo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjcyIDcyMCBUZAooU3RvY2sgQWRqdXN0bWVudCBSZXBvcnQpIFRqCkVUCmVuZHN0cmVhbQplbmRvYmoKeHJlZgowIDUKdHJhaWxlcgo8PAovU2l6ZSA1Ci9Sb290IDEgMCBSCj4+CgklJUVPRg=="
```

### 8. Save Stock In

**Endpoint**: `POST /admin/SaveStockIn`

**Description**: Save stock in transactions for multiple products.

**Authentication**: Admin role required

**Purpose**: Adds new products to inventory or increases existing stock quantities. This is for updating inventory only, no barcode printing.

**When to use**: When you want to add new stock/inventory without generating barcodes for printing.

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
    "pro_id": "uuid-string",
    "ven_id": "uuid-string"
  }
]
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/SaveStockIn \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '[{"ven_name":"Vendor Name","pro_name":"Product Name","pro_price":99.99,"pro_cost":79.99,"quantity":50,"totalCost":3999.5,"pro_barcode":"1234567890123","cat_name":"Category Name","brand":"Brand Name","pro_id":"uuid-string","ven_id":"uuid-string"}]'
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

### 9. Search Stock

**Endpoint**: `GET /admin/searchstock`

**Description**: Search stock by branch.

**Authentication**: Employee role or higher required

**Purpose**: Finds specific products in stock based on branch/location. This is for searching existing inventory only.

**When to use**: When you need to locate products in specific branches or locations.

**Query Parameters** (optional):
- `branches`: Branch to filter by
- `search_string`: Search term to filter products

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/searchstock?branches=MainBranch&search_string=product" \
  -b cookies.txt
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

### 10. Stock Report

**Endpoint**: `POST /admin/StockReport`

**Description**: Generate stock report in PDF format.

**Authentication**: Admin role required

**Purpose**: Creates a comprehensive stock report in PDF format. This is for reporting only, no inventory changes.

**When to use**: When you need to generate a PDF report of current stock levels and inventory.

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
  -b cookies.txt \
  -d "cat_name=Electronics&pro_name=Phone&ven_name=Supplier&timezone=UTC&branches=MainBranch&shelf=A1"
```

**Response**:
```json
"JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL0xlbmd0aCA0NAo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjcyIDcyMCBUZAooU3RvY2sgUmVwb3J0KSBUagoKRVQKZW5kc3RyZWFtCmVuZG9iagp4cmVmCjAgNQp0cmFpbGVyCjw8Ci9TaXplIDUKL1Jvb3QgMSAwIFIKPj4KJSVFT0Y="
```

### 11. Stock Report Excel

**Endpoint**: `POST /admin/StockReportexcel`

**Description**: Generate stock report in Excel format.

**Authentication**: Admin role required

**Purpose**: Creates a comprehensive stock report in Excel format. This is for reporting only, no inventory changes.

**When to use**: When you need to generate an Excel spreadsheet report of current stock levels and inventory.

**Request Body** (as form data):
- `cat_name`: Category name to filter by
- `pro_name`: Product name to filter by
- `ven_name`: Vendor name to filter by
- `timezone`: Timezone for the report
- `branches`: Branch to filter by
- `shelf`: Shelf to filter by

**Example**:
```bash
curl -X POST http://localhost:8000/admin/StockReportexcel \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -b cookies.txt \
  -d "cat_name=Electronics&pro_name=Phone&ven_name=Supplier&timezone=UTC&branches=MainBranch&shelf=A1"
```

**Response**:
Base64-encoded Excel file content.

### 12. Daily Inventory Report

**Endpoint**: `POST /admin/Dailyinventoryreport`

**Description**: Generate daily inventory report in PDF format.

**Authentication**: Admin role required

**Purpose**: Creates a daily inventory summary report in PDF format. This is for reporting only, no inventory changes.

**When to use**: When you need to generate a daily summary report of inventory.

**Example**:
```bash
curl -X POST http://localhost:8000/admin/Dailyinventoryreport \
  -b cookies.txt
```

**Response**:
```json
"JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL0xlbmd0aCA2MQo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjcyIDcyMCBUZAooRGFpbHkgSW52ZW50b3J5IFJlcG9ydCkgVGoKRVQKZW5kc3RyZWFtCmVuZG9iagp4cmVmCjAgNQp0cmFpbGVyCjw8Ci9TaXplIDUKL1Jvb3QgMSAwIFIKPj4KJSVFT0Y="
```

### 13. Print Barcodes (ZPL)

**Endpoint**: `POST /admin/PrintBarcodes`

**Description**: Generate ZPL commands for printing barcodes for a product using Zebra printers.

**Authentication**: Admin role required

**Purpose**: Generates ZPL commands for barcode printing ONLY. This does NOT add or modify any stock data.

**When to use**: When you want to print barcodes for an existing product without changing inventory. Call this endpoint when you want to generate ZPL commands to send to a Zebra printer for physical barcode labels.

**Query Parameters**:
- `pro_name`: Product name to print barcodes for
- `quantity`: Number of barcodes to print (based on quantity)
- `barcode`: Specific barcode to use (optional, will use product's barcode if not provided)

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/PrintBarcodes?pro_name=Laptop&quantity=5&barcode=LAPTOP123" \
  -b cookies.txt
```

**Response**:
```json
{
  "zpl_commands": "^XA^FO50,50^BY2,3,100^BCN,100,Y,N,N,A^FDLAPTOP123^FS^FO50,150^A0N,25,25^FDLaptop^FS^XZ",
  "product": "Laptop",
  "quantity": 5,
  "barcode": "LAPTOP123",
  "message": "Generated ZPL for 5 barcode(s) of Laptop"
}
```

### 14. Save Stock In With Barcode Printing

**Endpoint**: `POST /admin/SaveStockInWithBarcodes`

**Description**: Save stock in transactions and optionally generate ZPL commands for barcode printing.

**Authentication**: Admin role required

**Purpose**: Combines both inventory update and barcode printing. Updates stock data in database AND generates ZPL commands for printing barcodes.

**When to use**: When you want to add new stock/inventory AND simultaneously generate barcodes for printing. Use with `print_barcodes=true` parameter to generate ZPL commands, or `print_barcodes=false` to just update inventory like the basic SaveStockIn endpoint.

**Query Parameters** (optional):
- `print_barcodes`: Whether to generate ZPL commands for barcode printing (default: false)

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
    "pro_id": "uuid-string",
    "ven_id": "uuid-string"
  }
]
```

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/SaveStockInWithBarcodes?print_barcodes=true" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '[{"ven_name":"Vendor Name","pro_name":"Product Name","pro_price":99.99,"pro_cost":79.99,"quantity":50,"totalCost":3999.5,"pro_barcode":"1234567890123","cat_name":"Category Name","brand":"Brand Name","pro_id":"uuid-string","ven_id":"uuid-string"}]'
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
  ],
  "zpl_commands": [
    {
      "product": "Product Name",
      "zpl_commands": "^XA^FO50,50^BY2,3,100^BCN,100,Y,N,N,A^FD1234567890123^FS^FO50,150^A0N,25,25^FDProduct Name^FS^XZ"
    }
  ],
  "print_requested": true
}
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
  -b cookies.txt \
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
  -b cookies.txt
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
  -b cookies.txt \
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
  -b cookies.txt
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
  -b cookies.txt
```

**Response**:
```json
{
  "quantity": 50
}
```

## CRUD Operations Summary

### Create Operations
- `POST /admin/SaveStockIn` - Create stock in transactions (stock data only)
- `POST /admin/SaveStockInWithBarcodes` - Create stock in transactions with optional barcode printing
- `POST /admin/Adjuststock` - Create stock adjustments

### Read Operations
- `GET /admin/ViewStock` - View stock with filtering
- `GET /admin/searchstock` - Search stock by branch
- `POST /admin/GetStockDetail` - Get specific stock details

### Update Operations
- `POST /admin/Adjuststock` - Adjust stock levels

### Report Operations
- `POST /admin/StockReport` - Generate stock report (PDF)
- `POST /admin/StockReportexcel` - Generate stock report (Excel)
- `POST /admin/Dailyinventoryreport` - Generate daily inventory report

### Print Operations
- `POST /admin/PrintBarcodes` - Generate ZPL commands for barcode printing

## Frontend-Compatible Endpoints

The following capitalized endpoints are provided for JavaScript frontend compatibility:

- `GET /admin/ViewStock` - View stock with search and branch filtering
- `POST /admin/Adjuststock` - Adjust stock levels
- `POST /admin/SaveStockIn` - Save stock in transactions
- `GET /admin/searchstock` - Search stock by branch
- `POST /admin/StockReport` - Generate stock report (PDF)
- `POST /admin/StockReportexcel` - Generate stock report (Excel)
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

- All endpoints require appropriate role-based access control using session cookies
- Stock data is protected by role-based access control
- Audit logs are maintained for all stock-related actions
- Only admins can modify stock levels and generate reports
- Foreign key constraints prevent deletion of products with stock history
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
- Comprehensive API documentation
- Server-side session control for better security
- Instant logout capability across all devices
- Better compliance with audit trails and regulations

## CRUD Commands for Stock Operations

### Stock In Operations

**Basic Stock In (Database Only)**:
```bash
curl -X POST http://localhost:8000/admin/SaveStockIn \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '[{
    "ven_name": "Vendor Name",
    "pro_name": "Product Name",
    "pro_price": 99.99,
    "pro_cost": 79.99,
    "quantity": 50,
    "totalCost": 3999.5,
    "pro_barcode": "1234567890123",
    "cat_name": "Category Name",
    "brand": "Brand Name",
    "pro_id": "uuid-string",
    "ven_id": "uuid-string"
  }]'
```

**Stock In with Barcode Printing**:
```bash
curl -X POST "http://localhost:8000/admin/SaveStockInWithBarcodes?print_barcodes=true" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '[{
    "ven_name": "Vendor Name",
    "pro_name": "Product Name",
    "pro_price": 99.99,
    "pro_cost": 79.99,
    "quantity": 50,
    "totalCost": 3999.5,
    "pro_barcode": "1234567890123",
    "cat_name": "Category Name",
    "brand": "Brand Name",
    "pro_id": "uuid-string",
    "ven_id": "uuid-string"
  }]'
```

### Barcode Printing Operations

**Generate ZPL for Specific Product**:
```bash
curl -X POST "http://localhost:8000/admin/PrintBarcodes?pro_name=Product Name&quantity=5&barcode=1234567890123" \
  -b cookies.txt
```

### Stock Adjustment Operations

**Adjust Stock Levels**:
```bash
curl -X POST http://localhost:8000/admin/Adjuststock \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '[{
    "pro_name": "Product Name",
    "quantity": 10,
    "stock_id": "uuid-string",
    "status": "IN",
    "frombranch": "MainBranch",
    "tobranch": "SecondaryBranch"
  }]'
```

### Stock Viewing Operations

**View All Stock**:
```bash
curl -X GET "http://localhost:8000/admin/ViewStock?search_string=product&branches=MainBranch&limit=100" \
  -b cookies.txt
```

**Search Stock by Branch**:
```bash
curl -X GET "http://localhost:8000/admin/searchstock?branches=MainBranch&search_string=product" \
  -b cookies.txt
```

### Report Generation Operations

**Generate Stock Report (PDF)**:
```bash
curl -X POST http://localhost:8000/admin/StockReport \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -b cookies.txt \
  -d "cat_name=Electronics&pro_name=Phone&ven_name=Supplier&timezone=UTC&branches=MainBranch&shelf=A1"
```

**Generate Stock Report (Excel)**:
```bash
curl -X POST http://localhost:8000/admin/StockReportexcel \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -b cookies.txt \
  -d "cat_name=Electronics&pro_name=Phone&ven_name=Supplier&timezone=UTC&branches=MainBranch&shelf=A1"
```

**Generate Daily Inventory Report**:
```bash
curl -X POST http://localhost:8000/admin/Dailyinventoryreport \
  -b cookies.txt
```