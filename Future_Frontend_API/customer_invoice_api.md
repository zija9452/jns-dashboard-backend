# Customer Invoice API Documentation

## Overview
This document provides comprehensive documentation for all customer invoice endpoints in the Regal POS Backend, including curl commands for testing and integration.

## Authentication
All customer invoice endpoints require authentication with a valid JWT access token. Obtain a token by logging in:

```bash
curl -X POST http://localhost:8000/auth/traditional-login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Use the returned `access_token` in the Authorization header:

```bash
-H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

## Customer Invoice Endpoints

### 1. Get Customer Details (READ)
**URL**: `POST /customer-invoice/GetCustomerDetails` - Retrieves customer details by name

### 2. Get Salesman Details (READ)
**URL**: `POST /customer-invoice/Getsalesmandetail` - Retrieves salesman details by name

### 3. Save Customer Orders (CREATE)
**URL**: `POST /customer-invoice/SaveCustomerOrders` - Creates a new customer invoice with specified items and payment details

### 4. Get Customer Invoice Balance (READ)
**URL**: `POST /customer-invoice/GetCustomerInvoiceBalance` - Gets total balance across all customer invoices

### 5. Update Customer Invoice (UPDATE)
**URL**: `PUT /customer-invoice/UpdateCustomerInvoice/{invoice_id}` - Updates details of an existing customer invoice

### 6. Get Order by ID (READ)
**URL**: `GET /customer-invoice/Getorder/{id}` - Retrieves specific order details by its ID

### 7. View Customer Orders (READ)
**URL**: `GET /customer-invoice/Viewcustomerorder` - Lists all customer orders with optional filtering and pagination

### 8. Customer Order Report (READ)
**URL**: `GET /customer-invoice/customerorderreport` - Generates customer order report with optional filtering

### 9. Delete Customer Order (DELETE)
**URL**: `POST /customer-invoice/Deletecustomorder/{id}` - Deletes a customer order by its ID

### 10. Create Customer (CREATE)
**URL**: `POST /customer-invoice/Customers` - Creates a new customer in the system

### 11. Get Salesman Details (Alternative) (READ)
**URL**: `POST /customer-invoice/GetSalesmanDetails` - Alternative endpoint to retrieve salesman details by name

### 12. Get Customer Balance (READ)
**URL**: `POST /customer-invoice/customerbalance` - Gets customer balance by name

### 13. Get Customer Balance by ID (READ)
**URL**: `GET /customer-invoice/customer-balance/{customer_id}` - Gets detailed balance information for a specific customer

### 14. Get Customer Orders (READ)
**URL**: `GET /customer-invoice/customer-orders/{customer_id}` - Gets all orders for a specific customer

### 15. Get Order Details (READ)
**URL**: `GET /customer-invoice/order-details/{order_id}` - Gets detailed information for a specific order

### 16. Process Payment (UPDATE)
**URL**: `PUT /customer-invoice/process-payment/{order_id}` - Processes a payment for an existing order

### 17. Daily Collection Report (READ)
**URL**: `GET /customer-invoice/daily-collection-report/{date}` - Gets all payments collected on a specific date

### 18. Get Payment History (READ)
**URL**: `GET /customer-invoice/payment-history/{order_id}` - Gets payment history for a specific order

### 19. Get Customer Invoices by Date (READ)
**URL**: `GET /customer-invoice/customerinvoicesbydate` - Gets all customer invoices for a specific date
**Endpoint**: `POST /customer-invoice/GetCustomerDetails`

**Description**: Get customer details by name for JavaScript frontend compatibility.

**Authentication**: Admin role required

**Query Parameters**:
- `cus_name`: Customer name to search for

**Example**:
```bash
curl -X POST "http://localhost:8000/customer-invoice/GetCustomerDetails?cus_name=John%20Doe" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
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

### 2. Get Salesman Details (READ)
**Endpoint**: `POST /customer-invoice/Getsalesmandetail`

**Description**: Get salesman details by name for JavaScript frontend compatibility.

**Authentication**: Admin role required

**Query Parameters**:
- `sal_name`: Salesman name to search for

**Example**:
```bash
curl -X POST "http://localhost:8000/customer-invoice/Getsalesmandetail?sal_name=Jane" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
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

### 3. Save Customer Orders (CREATE)
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
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
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

### 4. Get Customer Invoice Balance (READ)
**Endpoint**: `POST /customer-invoice/GetCustomerInvoiceBalance`

**Description**: Get customer invoice balance with optional customer ID filtering.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `customer_id`: Filter by specific customer ID

**Example**:
```bash
curl -X POST "http://localhost:8000/customer-invoice/GetCustomerInvoiceBalance?customer_id=uuid-string" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
Customer invoice balance information.

### 5. Update Customer Invoice (UPDATE)
**Endpoint**: `PUT /customer-invoice/UpdateCustomerInvoice/{invoice_id}`

**Description**: Update customer invoice details by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{invoice_id}`: UUID of the invoice to update

**Query Parameters** (optional):
- `e_name`: New invoice name
- `e_amount`: New amount
- `note`: Notes

**Example**:
```bash
curl -X PUT "http://localhost:8000/customer-invoice/UpdateCustomerInvoice/uuid-string?e_name=Updated%20Invoice&e_amount=50.0&note=Updated%20note" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
Updated invoice information.

### 6. Get Order by ID (READ)
**Endpoint**: `GET /customer-invoice/Getorder/{id}`

**Description**: Get specific order details by ID for JavaScript frontend compatibility.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the order

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/Getorder/uuid-string" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
Detailed order information.

### 7. View Customer Orders (READ)
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
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
Array of customer orders with details including:
- Order ID
- Status
- Customer name
- Team name
- Quantity
- Total amount
- Date
- Detailed fields

### 8. Customer Order Report (READ)
**Endpoint**: `GET /customer-invoice/customerorderreport`

**Description**: Generate customer order report with optional filtering.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `orderid`: Specific order ID to report on
- `timezone`: Timezone for the report
- `printoption`: Print options

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/customerorderreport?orderid=uuid-string" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
Customer order report in PDF format.

### 9. Delete Customer Order (DELETE)
**Endpoint**: `POST /customer-invoice/Deletecustomorder/{id}`

**Description**: Delete customer order by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the order to delete

**Example**:
```bash
curl -X POST "http://localhost:8000/customer-invoice/Deletecustomorder/uuid-string" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
Deletion confirmation.

### 10. Create Customer (CREATE)
**Endpoint**: `POST /customer-invoice/Customers`

**Description**: Create a new customer for JavaScript frontend compatibility.

**Authentication**: Admin role required

**Query Parameters**:
- `cus_name`: Customer name (required)
- `cus_phone`: Customer phone (required)
- `cus_address`: Customer address (required)
- `cus_cnic`: Customer CNIC (required)
- `cus_sal_id_fk`: Salesman ID (optional)

**Example**:
```bash
curl -X POST "http://localhost:8000/customer-invoice/Customers?cus_name=Jane%20Smith&cus_phone=0987654321&cus_address=456%20Elm%20St&cus_cnic=0987654321098&cus_sal_id_fk=uuid-string" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
Created customer information.

### 11. Get Salesman Details (Alternative) (READ)
**Endpoint**: `POST /customer-invoice/GetSalesmanDetails`

**Description**: Alternative endpoint to get salesman details by name.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `sal_name`: Salesman name to search for

**Example**:
```bash
curl -X POST "http://localhost:8000/customer-invoice/GetSalesmanDetails?sal_name=Jane" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
Salesman details.

### 12. Get Customer Balance (READ)
**Endpoint**: `POST /customer-invoice/customerbalance`

**Description**: Get customer balance by name.

**Authentication**: Admin role required

**Query Parameters**:
- `cus_name`: Customer name to get balance for

**Example**:
```bash
curl -X POST "http://localhost:8000/customer-invoice/customerbalance?cus_name=John%20Doe" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
```json
{
  "cus_id": "uuid-string",
  "cus_balance": 0.0
}
```

### 13. Get Customer Balance by ID (READ)
**Endpoint**: `GET /customer-invoice/customer-balance/{customer_id}`

**Description**: Get detailed customer balance information by customer ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{customer_id}`: UUID of the customer

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/customer-balance/uuid-string" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
Detailed customer balance information including total balance, orders, and status.

### 14. Get Customer Orders (READ)
**Endpoint**: `GET /customer-invoice/customer-orders/{customer_id}`

**Description**: Get all orders for a specific customer.

**Authentication**: Admin role required

**Path Parameter**:
- `{customer_id}`: UUID of the customer

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/customer-orders/uuid-string" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
List of all orders for the specified customer.

### 15. Get Order Details (READ)
**Endpoint**: `GET /customer-invoice/order-details/{order_id}`

**Description**: Get detailed information for a specific order by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{order_id}`: UUID of the order

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/order-details/uuid-string" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
Detailed order information including items, totals, payments, etc.

### 16. Process Payment (UPDATE)
**Endpoint**: `PUT /customer-invoice/process-payment/{order_id}`

**Description**: Process payment for an existing customer order.

**Authentication**: Admin role required

**Path Parameter**:
- `{order_id}`: UUID of the order to process payment for

**Request Body**:
```json
{
  "amount": float,
  "payment_method": "string",
  "description": "string",
  "payment_date": "string"
}
```

**Example**:
```bash
curl -X PUT "http://localhost:8000/customer-invoice/process-payment/uuid-string" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d '{
    "amount": 15.0,
    "payment_method": "cash",
    "description": "Partial payment",
    "payment_date": "2026-02-06T10:30:00"
  }'
```

**Response**:
Updated payment information including new balance and payment history.

### 17. Daily Collection Report (READ)
**Endpoint**: `GET /customer-invoice/daily-collection-report/{date}`

**Description**: Get all payments collected on a specific date.

**Authentication**: Admin role required

**Path Parameter**:
- `{date}`: Date in YYYY-MM-DD format

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/daily-collection-report/2026-02-06" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
All payments collected on the specified date with totals and details.

### 18. Get Payment History (READ)
**Endpoint**: `GET /customer-invoice/payment-history/{order_id}`

**Description**: Get payment history for a specific order.

**Authentication**: Admin role required

**Path Parameter**:
- `{order_id}`: UUID of the order

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/payment-history/uuid-string" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
Array of payment records for the order.

### 19. Get Customer Invoices by Date (READ)
**Endpoint**: `GET /customer-invoice/customerinvoicesbydate`

**Description**: Get all customer invoices for a specific date.

**Authentication**: Admin role required

**Query Parameters**:
- `date`: Date in YYYY-MM-DD format

**Example**:
```bash
curl -X GET "http://localhost:8000/customer-invoice/customerinvoicesbydate?date=2026-02-06" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response**:
All customer invoices created on the specified date with totals and details.

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
- All endpoints require appropriate role-based access control
- Customer invoice data is protected by role-based access control
- Audit logs are maintained for all customer invoice-related actions
- Payment information is secured with proper validation

## Production Ready Features
- Async/await implementation for high concurrency
- Pydantic v2 validation
- Proper error handling and logging
- Database transaction safety
- JWT token-based authentication
- Role-based access control
- Input sanitization and validation
- Concurrency-safe invoice number generation
- Payment validation and tracking