# Customer Invoice API Documentation

## Overview
This document provides comprehensive documentation for all customer invoice endpoints in the Regal POS Backend with session-based authentication, including curl commands for testing and integration.

### Authentication

All product endpoints require session-based authentication. Obtain a session by logging in:

```bash
curl -X POST http://localhost:8000/auth/session-login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

The login response will include a session cookie that will be automatically sent with subsequent requests when using the `-b` flag with curl or proper cookie handling in applications.

## Customer Invoice Endpoints

### 1. Get Customer Details
**Endpoint**: `POST /customer-invoice/GetCustomerDetails`

**Description**: Get customer details by name for JavaScript frontend compatibility.

**Authentication**: Cashier role required (admin and cashier can access)

**Request Body**:
```json
{
  "cus_name": "string (required)"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/customer-invoice/GetCustomerDetails" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "cus_name": "John Doe"
  }'
```

**Response**:
```json
{
  "cus_id": "uuid-string",
  "cus_name": "John Doe",
  "cus_phone": "1234567890",
  "cus_address": "{\"street\": \"123 Main St\", \"city\": \"\", \"country\": \"\"}",
  "cus_cnic": "",
  "cus_balance": 0.0
}
```

### 2. Get Salesman Details
**Endpoint**: `POST /customer-invoice/Getsalesmandetail`

**Description**: Get salesman details by name for JavaScript frontend compatibility.

**Authentication**: Cashier role required (admin and cashier can access)

**Request Body**:
```json
{
  "sal_name": "string (required)"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/customer-invoice/Getsalesmandetail" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "sal_name": "Jane"
  }'
```

**Response**:
```json
{
  "sal_id": "uuid-string",
  "sal_name": "Jane Doe",
  "sal_phone": "",
  "sal_address": "",
  "branch": ""
}
```

### 3. Save Customer Orders
**Endpoint**: `POST /customer-invoice/SaveCustomerOrders`

**Description**: Save customer orders (customer invoice creation) with all parameters in request body for security.

**Authentication**: Admin role required

**Request Body**:
```json
{
  "items": [
    {
      "pro_name": "string",
      "pro_quantity": integer,
      "unit_price": float,
      "discount": float,
      "cat_name": "string"
    }
  ],
  "customer_id": "uuid-string",
  "customer_name": "string",
  "team_name": "string",
  "payment_method": "string",
  "initial_paid_amount": float,
  "remarks": "string",
  "salesman_id": "uuid-string",
  "timezone": "string",
  "date": "string"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/customer-invoice/SaveCustomerOrders" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "items": [
      {
        "pro_name": "T-Shirt",
        "pro_quantity": 2,
        "unit_price": 10.0,
        "discount": 0.0,
        "cat_name": "Clothing"
      },
      {
        "pro_name": "Pants",
        "pro_quantity": 1,
        "unit_price": 15.0,
        "discount": 0.0,
        "cat_name": "Clothing"
      }
    ],
    "customer_id": "uuid-string",
    "customer_name": "John Doe",
    "team_name": "Sales Team",
    "payment_method": "cash",
    "initial_paid_amount": 10.0,
    "remarks": "Test order with multiple items",
    "salesman_id": "uuid-string",
    "timezone": "UTC",
    "date": "2026-02-06"
  }'
```

**Response**:
Base64 encoded PDF report of the customer invoice.

### 4. View Customer Orders
**Endpoint**: `GET /customer-invoice/Viewcustomerorder`

**Description**: View customer orders with optional filtering and pagination.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `searchString`: Search term for filtering orders
- `status`: Filter by status (issued, paid, partial, cancelled)
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/Viewcustomerorder?limit=10" \
  -b cookies.txt
```

**Response**:
Array of customer orders with details.

### 5. Get Order Details
**Endpoint**: `GET /customer-invoice/order-details/{order_id}`

**Description**: Get detailed information for a specific order by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{order_id}`: UUID of the order

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/order-details/uuid-string" \
  -b cookies.txt
```

**Response**:
Detailed order information including items, totals, payments, etc.

### 6. Process Payment
**Endpoint**: `PUT /customer-invoice/process-payment/{order_id}`

**Description**: Process payment for an existing customer order.

**Authentication**: Admin role required

**Path Parameter**:
- `{order_id}`: UUID of the order to process payment for

**Query Parameters**:
- `amount`: Payment amount to process
- `payment_method`: Method of payment (cash, card, etc.)
- `description`: Description of the payment

**Example**:
```bash
curl -X PUT "http://localhost:8000/customer-invoice/process-payment/uuid-string" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "amount": 15,
    "payment_method": "cash",
    "description": "Additional payment"
  }'
```

**Response**:
Updated payment information including new balance and payment history.

### 7. Get Customer Balance (by Name)
**Endpoint**: `POST /customer-invoice/customerbalance`

**Description**: Get customer balance by name.

**Authentication**: Cashier role required (admin and cashier can access)

**Request Body**:
```json
{
  "cus_name": "string (required)"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/customer-invoice/customerbalance" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "cus_name": "John Doe"
  }'
```

**Response**:
```json
{
  "cus_id": "uuid-string",
  "cus_balance": 0.0
}
```

### 8. Get Customer Balance (by ID)
**Endpoint**: `GET /customer-invoice/customer-balance/{customer_id}`

**Description**: Get detailed customer balance information by customer ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{customer_id}`: UUID of the customer

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/customer-balance/uuid-string" \
  -b cookies.txt
```

**Response**:
Detailed customer balance information including total balance, orders, and status.

### 9. Get Customer Orders
**Endpoint**: `GET /customer-invoice/customer-orders/{customer_id}`

**Description**: Get all orders for a specific customer.

**Authentication**: Admin role required

**Path Parameter**:
- `{customer_id}`: UUID of the customer

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/customer-orders/uuid-string" \
  -b cookies.txt
```

**Response**:
List of all orders for the specified customer.

### 10. Get Payment History
**Endpoint**: `GET /customer-invoice/payment-history/{order_id}`

**Description**: Get payment history for a specific order.

**Authentication**: Admin role required

**Path Parameter**:
- `{order_id}`: UUID of the order

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/payment-history/uuid-string" \
  -b cookies.txt
```

**Response**:
Array of payment records for the order.

### 11. Get Customer Invoices by Date
**Endpoint**: `GET /customer-invoice/customerinvoicesbydate`

**Description**: Get all customer invoices for a specific date.

**Authentication**: Admin role required

**Query Parameters**:
- `date`: Date in YYYY-MM-DD format

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/customerinvoicesbydate?date=2026-02-06" \
  -b cookies.txt
```

**Response**:
All customer invoices created on the specified date with totals and details.

### 12. Get Daily Collection Report
**Endpoint**: `GET /customer-invoice/daily-collection-report/{date}`

**Description**: Get all payments collected on a specific date.

**Authentication**: Admin role required

**Path Parameter**:
- `{date}`: Date in YYYY-MM-DD format

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/daily-collection-report/2026-02-06" \
  -b cookies.txt
```

**Response**:
All payments collected on the specified date with totals and details.

### 13. Create Customer
**Endpoint**: `POST /customer-invoice/Customers`

**Description**: Create a new customer for JavaScript frontend compatibility.

**Authentication**: Cashier role required (admin and cashier can access)

**Request Body**:
```json
{
  "cus_name": "string (required)",
  "cus_phone": "string (required)",
  "cus_address": "string (required)",
  "cus_cnic": "string (required)",
  "cus_sal_id_fk": "string (optional)"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/customer-invoice/Customers" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "cus_name": "Jane Smith",
    "cus_phone": "0987654321",
    "cus_address": "456 Elm St",
    "cus_cnic": "0987654321098",
    "cus_sal_id_fk": "uuid-string"
  }'
```

**Response**:
Created customer information.

### 14. Get Customer Invoice Balance
**Endpoint**: `POST /customer-invoice/GetCustomerInvoiceBalance`

**Description**: Get customer invoice balance with optional customer ID filtering.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `customer_id`: Filter by specific customer ID

**Example**:
```bash
curl -X POST "http://localhost:8000/customer-invoice/GetCustomerInvoiceBalance" \
  -b cookies.txt
```

**Response**:
Customer invoice balance information.

### 15. Get Order by ID
**Endpoint**: `GET /customer-invoice/Getorder/{id}`

**Description**: Get specific order details by ID for JavaScript frontend compatibility.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the order

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/Getorder/uuid-string" \
  -b cookies.txt
```

**Response**:
Detailed order information.

### 16. Update Customer Invoice
**Endpoint**: `PUT /customer-invoice/UpdateCustomerInvoice/{invoice_id}`

**Description**: Update customer invoice details.

**Authentication**: Admin role required

**Path Parameter**:
- `{invoice_id}`: UUID of the invoice to update

**Query Parameters** (optional):
- `e_name`: New invoice name
- `e_amount`: New amount
- `note`: Notes

**Example**:
```bash
curl -X PUT "http://localhost:8000/customer-invoice/UpdateCustomerInvoice/uuid-string" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "e_name": "Updated Invoice",
    "e_amount": 50.0,
    "note": "Updated note"
  }'
```

**Response**:
Updated invoice information.

### 17. Delete Customer Order
**Endpoint**: `DELETE /customer-invoice/Deletecustomorder/{id}`

**Description**: Delete customer order by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the order to delete

**Example**:
```bash
curl -X DELETE "http://localhost:8000/customer-invoice/Deletecustomorder/uuid-string" \
  -b cookies.txt
```

**Response**:
Deletion confirmation.

### 18. Get Salesman Details (Alternative)
**Endpoint**: `POST /customer-invoice/GetSalesmanDetails`

**Description**: Alternative endpoint to get salesman details by name.

**Authentication**: Cashier role required (admin and cashier can access)

**Request Body**:
```json
{
  "sal_name": "string (optional)"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/customer-invoice/GetSalesmanDetails" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "sal_name": "Jane"
  }'
```

**Response**:
Salesman details.

### 19. Customer Invoice Health Check
**Endpoint**: `GET /health/customer-invoice`

**Description**: Health check for customer invoice functionality.

**Authentication**: Not required

**Example**:
```bash
curl -X GET "http://localhost:8000/health/customer-invoice"
```

**Response**:
```json
{
  "status": "healthy",
  "service": "customer-invoice"
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
    "timestamp": "2026-02-06T08:00:00.000000"
  }
}
```

Common error types:
- `400 Bad Request`: Invalid input parameters or format
- `401 Unauthorized`: Missing or invalid authentication token
- `403 Forbidden`: Insufficient permissions for the requested action
- `404 Not Found`: Requested resource not found
- `422 Validation Error`: Request validation failed
- `500 Internal Server Error`: Unexpected server error

## Security Notes
- All endpoints require appropriate role-based access control using session cookies
- Customer invoice data is protected by role-based access control
- Audit logs are maintained for all customer invoice-related actions
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
- Concurrency-safe invoice number generation
- Payment validation and tracking
- Server-side session control for better security
- Instant logout capability across all devices
- Better compliance with audit trails and regulations