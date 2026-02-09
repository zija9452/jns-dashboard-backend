# Walk-in Invoice API Documentation

This document provides comprehensive documentation for all walk-in invoice-related endpoints in the Regal POS Backend, including curl commands for testing and integration.

## Authentication

All walk-in invoice endpoints require authentication with a valid JWT access token. Obtain a token by logging in:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Use the returned `access_token` in the Authorization header:

```bash
-H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## Walk-in Invoice Management Endpoints

### 1. Create Walk-in Invoice

**Endpoint**: `POST /walkin-invoice/walkin-invoices`

**Description**: Create a new walk-in invoice with immediate payment. All products selected and paid in full at time of purchase.

**Authentication**: Admin role required

**Request Body**:
```json
{
  "items": [
    {
      "pro_name": "string",
      "pro_quantity": 1,
      "unit_price": 0.0,
      "discount": 0.0,
      "cat_name": "string",
    }
  ],
  "customer_id": "string",
  "salesman_id": "string",
  "payment_method": "string",
  "notes": "string"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/walkin-invoice/walkin-invoices \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "pro_name": "T-Shirt",
        "pro_quantity": 2,
        "unit_price": 25.00,
        "discount": 2.00
      }
    ],
    "payment_method": "cash",
    "notes": "Walk-in customer purchase"
  }'
```

**Response**: Base64 encoded PDF receipt

### 2. Get Walk-in Invoices

**Endpoint**: `GET /walkin-invoice/walkin-invoices`

**Description**: Get list of walk-in invoices with optional filtering.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `limit`: Maximum number of records to return (default 100, max 200)
- `skip`: Number of records to skip (for pagination)
- `customer_id`: Filter by customer ID
- `status`: Filter by invoice status
- `date`: Filter by date (YYYY-MM-DD)

**Example**:
```bash
curl -X GET "http://localhost:8000/walkin-invoice/walkin-invoices?limit=10&skip=0" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
[
  {
    "invoice_id": "uuid-string",
    "invoice_no": "WIV-001",
    "customer_id": "uuid-string",
    "salesman_id": "uuid-string",
    "customer_name": "Walk-in Customer",
    "team_name": "",
    "quantity": 2,
    "total_amount": 48.0,
    "date": "2026-02-07",
    "status": "paid",
    "items": [],
    "created_at": "2026-02-07T10:00:00.000000",
    "updated_at": "2026-02-07T10:00:00.000000"
  }
]
```

### 3. Get Specific Walk-in Invoice

**Endpoint**: `GET /walkin-invoice/walkin-invoices/{invoice_id}`

**Description**: Get specific walk-in invoice by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{invoice_id}`: UUID of the invoice

**Example**:
```bash
curl -X GET http://localhost:8000/walkin-invoice/walkin-invoices/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "invoice_id": "uuid-string",
  "invoice_no": "WIV-001",
  "customer_id": "uuid-string",
  "salesman_id": "uuid-string",
  "items": [],
  "totals": {},
  "total_amount": 48.0,
  "amount_paid": 48.0,
  "balance_due": 0.0,
  "payment_status": "paid",
  "payments_history": [],
  "taxes": 0.0,
  "discounts": 0.0,
  "status": "issued",
  "payment_method": "cash",
  "notes": "Walk-in customer purchase",
  "created_by": "uuid-string",
  "created_at": "2026-02-07T10:00:00.000000",
  "updated_at": "2026-02-07T10:00:00.000000"
}
```

### 4. Update Walk-in Invoice

**Endpoint**: `PUT /walkin-invoice/walkin-invoices/{invoice_id}`

**Description**: Update existing walk-in invoice.

**Authentication**: Admin role required

**Path Parameter**:
- `{invoice_id}`: UUID of the invoice to update

**Request Body**:
```json
{
  "items": "string",
  "totals": "string",
  "total_amount": "decimal",
  "amount_paid": "decimal",
  "balance_due": "decimal",
  "payment_status": "string",
  "payments_history": "string",
  "taxes": "decimal",
  "discounts": "decimal",
  "status": "InvoiceStatus",
  "payment_method": "string",
  "notes": "string"
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/walkin-invoice/walkin-invoices/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "notes": "Updated walk-in invoice"
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Invoice updated successfully",
  "invoice_id": "uuid-string"
}
```

### 5. Delete Walk-in Invoice

**Endpoint**: `DELETE /walkin-invoice/walkin-invoices/{invoice_id}`

**Description**: Delete walk-in invoice by ID. This will restore the inventory quantities that were decreased when the invoice was created.

**Authentication**: Admin role required

**Path Parameter**:
- `{invoice_id}`: UUID of the invoice to delete

**Example**:
```bash
curl -X DELETE http://localhost:8000/walkin-invoice/walkin-invoices/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "success": true,
  "message": "Invoice deleted successfully and inventory restored"
}
```

### 6. Get Duplicate Invoice Receipt

**Endpoint**: `GET /walkin-invoice/walkin-invoices/{invoice_id}/receipt`

**Description**: Get duplicate invoice/receipt for an existing walk-in invoice.

**Authentication**: Admin role required

**Path Parameter**:
- `{invoice_id}`: UUID of the invoice

**Example**:
```bash
curl -X GET http://localhost:8000/walkin-invoice/walkin-invoices/uuid-string/receipt \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**: Base64 encoded PDF receipt

### 7. Get Walk-in Invoices by Date

**Endpoint**: `GET /walkin-invoice/walkin-invoices/date/{date_str}`

**Description**: Get all walk-in invoices for a specific date.

**Authentication**: Admin role required

**Path Parameter**:
- `{date_str}`: Date in YYYY-MM-DD format

**Example**:
```bash
curl -X GET http://localhost:8000/walkin-invoice/walkin-invoices/date/2026-02-07 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "date": "2026-02-07",
  "total_invoices": 1,
  "total_amount": 48.0,
  "invoices": [
    {
      "invoice_id": "uuid-string",
      "invoice_no": "WIV-001",
      "customer_id": "uuid-string",
      "total_amount": 48.0,
      "created_at": "2026-02-07T10:00:00.000000",
      "products": [
        {
          "Orderid": "uuid-string",
          "Product": "T-Shirt",
          "Price": 25.0,
          "Amount Paid": 48.0,
          "Quantity": 2,
          "Discount": 2.0,
          "Total Discount": 2.0,
          "Cost": 50.0,
          "Time": "10:00:00",
          "Date": "2026-02-07"
        }
      ]
    }
  ]
}
```

### 8. Get Products for Sales

**Endpoint**: `GET /walkin-invoice/products-for-sales`

**Description**: Get products for salesman to select from during sales. Allows filtering by name, barcode, etc.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `search_term`: Search term to filter products
- `barcode`: Filter by specific barcode
- `limit`: Maximum number of records to return (default 50, max 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/walkin-invoice/products-for-sales?search_term=T-Shirt&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "id": "uuid-string",
  "sku": "string",
  "name": "string",
  "desc": "string",
  "unit_price": 0.0,
  "cost_price": 0.0,
  "tax_rate": 0.0,
  "stock_level": 0,
  "barcode": "string",
  "discount": 0.0,
  "category": "string",
  "attributes": "string"
}
```

### 9. Get Invoice by Order ID

**Endpoint**: `GET /walkin-invoice/invoices-by-order-id/{order_id}`

**Description**: Get specific invoice by order ID (invoice ID).

**Authentication**: Admin role required

**Path Parameter**:
- `{order_id}`: UUID of the order/invoice

**Example**:
```bash
curl -X GET http://localhost:8000/walkin-invoice/invoices-by-order-id/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**: Same as endpoint #3

### 10. Get Daily Invoice Report

**Endpoint**: `GET /walkin-invoice/daily-invoice-report/{date_str}`

**Description**: Get daily invoice report showing all invoices and totals for a specific date.

**Authentication**: Admin role required

**Path Parameter**:
- `{date_str}`: Date in YYYY-MM-DD format

**Example**:
```bash
curl -X GET http://localhost:8000/walkin-invoice/daily-invoice-report/2026-02-07 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "date": "2026-02-07",
  "total_invoices": 1,
  "total_amount": 48.0,
  "total_paid": 48.0,
  "total_discount": 2.0,
  "invoices": [
    {
      "invoice_id": "uuid-string",
      "invoice_no": "WIV-001",
      "customer_id": "uuid-string",
      "salesman_id": "uuid-string",
      "total_amount": 48.0,
      "amount_paid": 48.0,
      "payment_method": "cash",
      "payment_status": "paid",
      "created_at": "2026-02-07T10:00:00.000000",
      "products": [
        {
          "Orderid": "uuid-string",
          "Product": "T-Shirt",
          "Price": 25.0,
          "Amount Paid": 48.0,
          "Quantity": 2,
          "Discount": 2.0,
          "Total Discount": 2.0,
          "Cost": 50.0,
          "Time": "10:00:00",
          "Date": "2026-02-07"
        }
      ]
    }
  ]
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
    "timestamp": "2026-02-07T10:00:00.000000"
  }
}
```

Common error types:
- `400 Bad Request`: Invalid input parameters or format
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: Insufficient permissions for the requested action
- `404 Not Found`: Requested resource not found
- `422 Unprocessable Entity`: Validation error in request body

## Security Notes

- All endpoints require appropriate role-based access control (admin required)
- Invoice data is protected by role-based access control
- Inventory updates are synchronized with sales and refunds
- Payment methods and amounts are validated
- Unique invoice numbers are generated with database-level locking

## Production Ready Features

- Async/await implementation for high concurrency
- Pydantic v2 validation
- Proper error handling and logging
- Database transaction safety
- JWT token-based authentication
- Role-based access control
- Input sanitization and validation
- Inventory management with automatic stock updates
- PDF receipt generation for all transactions
- Concurrency-safe operations with advisory locks