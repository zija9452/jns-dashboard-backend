# Walk-in Refund API Documentation

This document provides comprehensive documentation for all walk-in invoice refund-related endpoints in the Regal POS Backend, including curl commands for testing and integration.

## Authentication

All walk-in refund endpoints require authentication with a valid JWT access token. Obtain a token by logging in:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Use the returned `access_token` in the Authorization header:

```bash
-H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## Walk-in Refund Management Endpoints

### 1. Create Walk-in Invoice Refund

**Endpoint**: `POST /walkin-refund/refunds/walkin-invoice`

**Description**: Create a refund for a walk-in invoice. When a refund is processed, the refunded products are added back to inventory.

**Authentication**: Admin role required

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
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "Content-Type: application/json" \
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

**Authentication**: Admin role required

**Query Parameters** (optional):
- `limit`: Maximum number of records to return (default 100, max 200)
- `skip`: Number of records to skip (for pagination)
- `customer_id`: Filter by customer ID
- `invoice_id`: Filter by invoice ID
- `date`: Filter by date (YYYY-MM-DD)

**Example**:
```bash
curl -X GET "http://localhost:8000/walkin-refund/refunds/walkin-invoice?limit=10&skip=0" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
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
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
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
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
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

**Authentication**: Admin role required

**Path Parameter**:
- `{invoice_id}`: UUID of the invoice

**Example**:
```bash
curl -X GET http://localhost:8000/walkin-refund/refunds/walkin-invoice/invoice/uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
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

- All endpoints require appropriate role-based access control (admin required)
- Refund data is protected by role-based access control
- Inventory updates are synchronized with refunds (products returned to stock)
- Refund amounts are validated against original invoice amounts
- Unique refund numbers are generated with database-level locking
- Original invoice payment status is updated when refunds are processed

## Production Ready Features

- Async/await implementation for high concurrency
- Pydantic v2 validation
- Proper error handling and logging
- Database transaction safety
- JWT token-based authentication
- Role-based access control
- Input sanitization and validation
- Inventory management with automatic stock restoration on refunds
- PDF receipt generation for all refunds
- Concurrency-safe operations with advisory locks
- Payment status updates synchronized with refunds