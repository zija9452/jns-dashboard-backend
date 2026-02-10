# Walk-in Refund API Documentation

This document provides comprehensive documentation for all walk-in invoice refund-related endpoints in the Regal POS Backend with session-based authentication, including curl commands for testing and integration.

## Authentication

All walk-in refund endpoints require session-based authentication. Obtain a session by logging in:

```bash
curl -X POST http://localhost:8000/auth/session-login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

The login response will include a session cookie that will be automatically sent with subsequent requests when using the `-b` flag with curl or proper cookie handling in applications.

## Walk-in Refund Management Endpoints

### 1. Create Walk-in Invoice Refund

**Endpoint**: `POST /walkin-refund/refunds/walkin-invoice`

**Description**: Create a refund for a walk-in invoice. When a refund is processed, the refunded products are added back to inventory.

**Authentication**: Admin role required (admin and cashier can access)

**Request Body**:
```json
{
  "invoice_id": "string",
  "refunded_items": [
    {
      "product_name": "string",
      "quantity_returned": 0
    }
  ],
  "amount": 0.0,
  "reason": "string",
  "customer_id": "string"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/walkin-refund/refunds/walkin-invoice \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "invoice_id": "uuid-string",
    "refunded_items": [
      {
        "product_name": "T-Shirt",
        "quantity_returned": 1
      }
    ],
    "amount": 24.0,
    "reason": "Defective product",
    "customer_id": "uuid-string"
  }'
```

**Response**: Base64 encoded PDF receipt

### 2. Get Walk-in Invoice Refunds

**Endpoint**: `GET /walkin-refund/refunds/walkin-invoice`

**Description**: Get list of walk-in invoice refunds with optional filtering.

**Authentication**: Admin role required (admin and cashier can access)

**Query Parameters** (optional):
- `limit`: Maximum number of records to return (default 100, max 200)
- `skip`: Number of records to skip (for pagination)
- `customer_id`: Filter by customer ID
- `invoice_id`: Filter by invoice ID
- `date`: Filter by date (YYYY-MM-DD)

**Example**:
```bash
curl -X GET "http://localhost:8000/walkin-refund/refunds/walkin-invoice?limit=10&skip=0" \
  -b cookies.txt
```

**Response**:
```json
[
  {
    "refund_id": "uuid-string",
    "refund_no": "WRF-001",
    "invoice_id": "uuid-string",
    "customer_id": "uuid-string",
    "refunded_items": [
      {
        "product_name": "T-Shirt",
        "quantity_returned": 1
      }
    ],
    "refund_amount": 24.0,
    "refund_reason": "Defective product",
    "processed_by": "uuid-string",
    "created_at": "2026-02-07T10:00:00.000000",
    "updated_at": "2026-02-07T10:00:00.000000"
  }
]
```

### 3. Get Specific Walk-in Invoice Refund

**Endpoint**: `GET /walkin-refund/refunds/walkin-invoice/{refund_id}`

**Description**: Get specific walk-in invoice refund by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{refund_id}`: UUID of the refund

**Example**:
```bash
curl -X GET http://localhost:8000/walkin-refund/refunds/walkin-invoice/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "refund_id": "uuid-string",
  "refund_no": "WRF-001",
  "invoice_id": "uuid-string",
  "customer_id": "uuid-string",
  "refunded_items": [
    {
      "product_name": "T-Shirt",
      "quantity_returned": 1
    }
  ],
  "refund_amount": 24.0,
  "refund_reason": "Defective product",
  "processed_by": "uuid-string",
  "created_at": "2026-02-07T10:00:00.000000",
  "updated_at": "2026-02-07T10:00:00.000000"
}
```

### 4. Get Daily Walk-in Invoice Refunds

**Endpoint**: `GET /walkin-refund/refunds/walkin-invoice/daily/{date_str}`

**Description**: Get all walk-in invoice refunds processed on a specific date with totals.

**Authentication**: Admin role required

**Path Parameter**:
- `{date_str}`: Date in YYYY-MM-DD format

**Example**:
```bash
curl -X GET http://localhost:8000/walkin-refund/refunds/walkin-invoice/daily/2026-02-07 \
  -b cookies.txt
```

**Response**:
```json
{
  "date": "2026-02-07",
  "total_refunds": 1,
  "total_refund_amount": 24.0,
  "refunds": [
    {
      "refund_id": "uuid-string",
      "refund_no": "WRF-001",
      "invoice_id": "uuid-string",
      "customer_id": "uuid-string",
      "refunded_items": [
        {
          "product_name": "T-Shirt",
          "quantity_returned": 1
        }
      ],
      "refund_amount": 24.0,
      "refund_reason": "Defective product",
      "processed_by": "uuid-string",
      "created_at": "2026-02-07T10:00:00.000000"
    }
  ]
}
```

### 5. Get Refunds for Specific Walk-in Invoice

**Endpoint**: `GET /walkin-refund/refunds/walkin-invoice/invoice/{invoice_id}`

**Description**: Get all refunds for a specific walk-in invoice.

**Authentication**: Admin role required (admin and cashier can access)

**Path Parameter**:
- `{invoice_id}`: UUID of the invoice

**Example**:
```bash
curl -X GET http://localhost:8000/walkin-refund/refunds/walkin-invoice/invoice/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "invoice_id": "uuid-string",
  "refunds": [
    {
      "refund_id": "uuid-string",
      "refund_no": "WRF-001",
      "refunded_items": [
        {
          "product_name": "T-Shirt",
          "quantity_returned": 1
        }
      ],
      "refund_amount": 24.0,
      "refund_reason": "Defective product",
      "processed_by": "uuid-string",
      "created_at": "2026-02-07T10:00:00.000000"
    }
  ],
  "total_refund_amount": 24.0,
  "refund_count": 1
}
```

### 6. Update Walk-in Invoice Refund

**Endpoint**: `PUT /walkin-refund/refunds/walkin-invoice/{refund_id}`

**Description**: Update a specific walk-in invoice refund. Allows updating refund details including date and amount.

**Authentication**: Admin role required (admin and cashier can access)

**Path Parameter**:
- `{refund_id}`: UUID of the refund to update

**Request Body**:
```json
{
  "items": "string (optional) - JSON string for refunded items",
  "amount": "decimal (optional) - Updated refund amount",
  "reason": "string (optional) - Updated reason for refund",
  "created_at": "datetime (optional) - Updated date of refund"
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/walkin-refund/refunds/walkin-invoice/uuid-string \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "reason": "Updated reason: Customer returned damaged product",
    "created_at": "2026-02-08T11:20:41.289250"
  }'
```

**Response**:
```json
{
  "success": true,
  "message": "Refund updated successfully",
  "refund_id": "string"
}
```

### 7. Delete Walk-in Invoice Refund

**Endpoint**: `DELETE /walkin-refund/refunds/walkin-invoice/{refund_id}`

**Description**: Delete a specific walk-in invoice refund. Also restores the inventory quantities that were refunded.

**Authentication**: Admin role required (admin and cashier can access)

**Path Parameter**:
- `{refund_id}`: UUID of the refund to delete

**Example**:
```bash
curl -X DELETE http://localhost:8000/walkin-refund/refunds/walkin-invoice/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "success": true,
  "message": "Refund deleted successfully",
  "refund_id": "string"
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
- `409 Conflict`: Refund amount exceeds amount paid

## Security Notes

- All endpoints require appropriate role-based access control using session cookies
- Refund data is protected by role-based access control
- Inventory updates are synchronized with refunds (products returned to stock)
- Refund amounts are validated against original invoice amounts
- Unique refund numbers are generated with database-level locking
- Original invoice payment status is updated when refunds are processed
- Both admin and cashier roles have access to refund operations for walk-in invoices
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
- Role-based access control (both admin and cashier roles can access refund endpoints)
- Input sanitization and validation
- Complete CRUD operations for refunds (Create, Read, Update, Delete)
- Inventory management with automatic stock restoration on refunds
- PDF receipt generation for all refunds
- Concurrency-safe operations with advisory locks
- Payment status updates synchronized with refunds
- Date and amount modification capabilities for refunds
- Full audit trail for all refund operations
- Server-side session control for better security
- Instant logout capability across all devices
- Better compliance with audit trails and regulations