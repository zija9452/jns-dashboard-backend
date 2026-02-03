# Customer Invoice API Documentation

## Overview
This document outlines the Customer Invoice API endpoints that are compatible with the JavaScript frontend code provided. These endpoints handle customer invoice creation, retrieval, updates, and deletion.

**API Purpose**: Manages customer invoices with support for multiple products, categories, and real-world POS functionality.
**Key Features**: Create, read, update, delete customer invoices with detailed product information and PDF receipts.

## Base URL
All endpoints are prefixed with `/customer-invoice/` (handled via the customer-invoice router).

## Authentication
All endpoints require admin authentication via RBAC (Role-Based Access Control). Use the following header:
```
Authorization: Bearer YOUR_ACCESS_TOKEN_HERE
```

## Endpoints

### 1. Create Customer Orders (Save Customer Invoice)
**POST** `/customer-invoice/SaveCustomerOrders`

Creates a new customer invoice with multiple items.

#### Request Body (JSON Array):
```json
[
  {
    "pro_name": "string",
    "total_price": "number",
    "pro_cost": "number",
    "pro_quantity": "number",
    "pro_discount": "number",
    "or_pro_id_fk": "string",
    "or_cus_id_fk": "string",
    "amountpaid": "number",
    "totalamount": "number",
    "balance": "number",
    "unit_price": "number",
    "salesman": "string",
    "payment_mod": "string",
    "cat_name": "string",
    "totaldiscount": "number",
    "discount": "number",
    "grand": "number",
    "symbol": "string",
    "totaldiscounts": "number",
    "remarks": "string",
    "cricktshirt_Neckstyle": "string",
    "cricktshirt_sleeve": "string",
    "cricktshirt_bottom": "string",
    "cricktshirt_fabric": "string",
    "cricktrouser_style": "string",
    "cricktrouser_style2": "string",
    "cricktrouser_bottom": "string",
    "cricktrouser_pocket": "string",
    "cricktrouser_fabric": "string",
    "foottshirt_neckstyle": "string",
    "foottshirt_sleeves": "string",
    "football_fabric": "string",
    "footshorts_style": "string",
    "footshorts_pocket": "string",
    "footballshort_fabric": "string",
    "trackjack_style": "string",
    "trackjack_waist": "string",
    "trackjack_pocket": "string",
    "trackjack_bottom": "string",
    "trackjack_fabric": "string",
    "tracktrous_style": "string",
    "tracktrous_bottom": "string",
    "tracktrous_pocket": "string",
    "tracktrous_fabric": "string",
    "teamname": "string",
    "imgfile": "string",
    "imgfile2": "string",
    "imgfile3": "string"
  }
]
```

#### Response
Returns a base64-encoded PDF report of the created invoice.

#### Example Request:
```bash
curl -X POST http://localhost:8000/customer-invoice/SaveCustomerOrders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d '[{
    "pro_name": "Test Product",
    "total_price": 100,
    "pro_cost": 50,
    "pro_quantity": 2,
    "pro_discount": 0,
    "or_pro_id_fk": "0",
    "or_cus_id_fk": "customer-uuid",
    "amountpaid": 100,
    "totalamount": 100,
    "balance": 0,
    "unit_price": 50,
    "salesman": "0",
    "payment_mod": "cash",
    "cat_name": "Test Category",
    "totaldiscount": 0,
    "discount": 0,
    "grand": 100,
    "symbol": "Rs",
    "totaldiscounts": 0,
    "remarks": "Test order",
    "cricktshirt_Neckstyle": "0",
    "cricktshirt_sleeve": "0",
    "cricktshirt_bottom": "0",
    "cricktshirt_fabric": "0",
    "cricktrouser_style": "0",
    "cricktrouser_style2": "0",
    "cricktrouser_bottom": "0",
    "cricktrouser_pocket": "0",
    "cricktrouser_fabric": "0",
    "foottshirt_neckstyle": "0",
    "foottshirt_sleeves": "0",
    "football_fabric": "0",
    "footshorts_style": "0",
    "footshorts_pocket": "0",
    "footballshort_fabric": "0",
    "trackjack_style": "0",
    "trackjack_waist": "0",
    "trackjack_pocket": "0",
    "trackjack_bottom": "0",
    "trackjack_fabric": "0",
    "tracktrous_style": "0",
    "tracktrous_bottom": "0",
    "tracktrous_pocket": "0",
    "tracktrous_fabric": "0",
    "teamname": "Test Team",
    "imgfile": null,
    "imgfile2": null,
    "imgfile3": null
  }]'
```

### 2. Get Customer Details
**POST** `/customer-invoice/GetCustomerDetails`

Retrieves customer details by name.

#### Query Parameter:
- `cus_name`: Customer name (string)

#### Response:
```json
{
  "cus_id": "string",
  "cus_name": "string",
  "cus_phone": "string",
  "cus_address": "string",
  "cus_cnic": "string",
  "cus_balance": "number"
}
```

#### Example Request:
```bash
curl -X POST "http://localhost:8000/customer-invoice/GetCustomerDetails?cus_name=Test%20Customer" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 3. Get Salesman Details
**POST** `/customer-invoice/Getsalesmandetail`

Retrieves salesman details by name.

#### Query Parameter:
- `sal_name`: Salesman name (string)

#### Response:
```json
{
  "sal_id": "string",
  "sal_name": "string",
  "sal_phone": "string",
  "sal_address": "string",
  "branch": "string"
}
```

#### Example Request:
```bash
curl -X POST "http://localhost:8000/customer-invoice/Getsalesmandetail?sal_name=Jane%20Smith" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 4. View Customer Invoices
**GET** `/customer-invoice/ViewCustomerInvoices`

Retrieves customer invoices with optional filtering.

#### Query Parameters:
- `customer_id`: Optional customer ID to filter by (string)
- `skip`: Number of records to skip for pagination (integer, default: 0)
- `limit`: Maximum number of records to return (integer, default: 100)

#### Response:
Array of invoice objects with detailed information.

#### Example Request:
```bash
curl -X GET "http://localhost:8000/customer-invoice/ViewCustomerInvoices?customer_id=uuid-string&skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 5. Get Specific Customer Invoice
**GET** `/customer-invoice/GetCustomerInvoice/{invoice_id}`

Retrieves a specific customer invoice by ID.

#### Path Parameter:
- `invoice_id`: UUID of the invoice (string)

#### Response:
Detailed invoice object with all fields.

#### Example Request:
```bash
curl -X GET http://localhost:8000/customer-invoice/GetCustomerInvoice/123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 6. Update Customer Invoice
**PUT** `/customer-invoice/UpdateCustomerInvoice/{invoice_id}`

Updates a specific customer invoice by ID.

#### Path Parameter:
- `invoice_id`: UUID of the invoice to update (string)

#### Query Parameters:
- `e_name`: New invoice name/number (optional)
- `e_amount`: New amount (optional)
- `note`: New notes (optional)

#### Response:
Updated invoice object with all fields.

#### Example Request:
```bash
curl -X PUT "http://localhost:8000/customer-invoice/UpdateCustomerInvoice/uuid-string?e_name=INV-NEW-001&e_amount=500.00&note=Updated invoice" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 7. Delete Customer Invoice
**POST** `/customer-invoice/DeleteCustomerInvoice/{invoice_id}`

Deletes a specific customer invoice by ID.

#### Path Parameter:
- `invoice_id`: UUID of the invoice to delete (string)

#### Response:
```json
{
  "success": true,
  "message": "Invoice deleted successfully"
}
```

#### Example Request:
```bash
curl -X POST http://localhost:8000/customer-invoice/DeleteCustomerInvoice/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 8. Get Customer Invoice Balance
**POST** `/customer-invoice/GetCustomerInvoiceBalance`

Retrieves the balance for a customer's unpaid invoices.

#### Request Body (Form Data):
- `customer_id`: Optional customer ID to filter by (string)

#### Response:
```json
{
  "cus_balance": "number"
}
```

#### Example Request:
```bash
curl -X POST http://localhost:8000/customer-invoice/GetCustomerInvoiceBalance \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d "customer_id=uuid-string"
```

### 9. Generate Customer Invoice Report
**POST** `/customer-invoice/CustomerInvoicereport`

Generates a PDF report of customer invoices.

#### Request Body (Form Data):
- `cat_name`: Optional category name filter (string)
- `pro_name`: Optional product name filter (string)
- `ven_name`: Optional vendor name filter (string)
- `branches`: Optional branch filter (string)
- `shelf`: Optional shelf filter (string)
- `timezone`: Timezone information (string)

#### Response
Returns a base64-encoded PDF report.

#### Example Request:
```bash
curl -X POST http://localhost:8000/customer-invoice/CustomerInvoicereport \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d "cat_name=Electronics&branches=Main Branch"
```

### 10. Update Customer Orders
**PUT** `/customer-invoice/UpdateCustomerOrders/{invoice_id}`

Updates customer orders (invoice update) by ID.

#### Path Parameter:
- `invoice_id`: UUID of the invoice to update (string)

#### Request Body (JSON):
Same structure as SaveCustomerOrders orderItems

#### Response
Returns a base64-encoded PDF report of the updated invoice.

#### Example Request:
```bash
curl -X PUT http://localhost:8000/customer-invoice/UpdateCustomerOrders/uuid-string \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d '[{"pro_name": "Updated Product", "total_price": 150, "pro_quantity": 3}]'
```

### 11. Delete Customer Orders
**POST** `/customer-invoice/DeleteCustomerOrders/{invoice_id}`

Deletes customer orders (invoice deletion) by ID.

#### Path Parameter:
- `invoice_id`: UUID of the invoice to delete (string)

#### Response:
```json
{
  "success": true,
  "message": "Customer order deleted successfully"
}
```

#### Example Request:
```bash
curl -X POST http://localhost:8000/customer-invoice/DeleteCustomerOrders/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## Error Handling
All endpoints return appropriate HTTP status codes:
- `200`: Success
- `400`: Bad Request (invalid input)
- `404`: Not Found
- `401`: Unauthorized
- `403`: Forbidden (insufficient permissions)
- `500`: Internal Server Error

## Additional Features

### Invoice Number Generation
The system automatically generates unique invoice numbers in the format: `CUSTINV-YYYYMMDD-XXX` (e.g., `CUSTINV-20260203-001`).

### Payment Methods
Supported payment methods include:
- `cash`
- `credit`
- `online`
- `card`

### Invoice Statuses
- `draft`
- `issued`
- `paid`
- `cancelled`

## Security
- All endpoints require admin authentication
- Input validation is performed on all requests
- SQL injection protection through parameterized queries
- Proper error handling without exposing sensitive information

## Notes
- The `items` and `totals` fields are stored as JSON strings in the database
- Images are stored as base64-encoded strings within the items data
- The system supports multiple product categories with specific attributes for each