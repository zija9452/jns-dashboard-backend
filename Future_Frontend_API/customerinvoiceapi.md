# Customer Invoice API Documentation

## Overview
This document outlines the Customer Invoice API endpoints that are in the actual customer_invoice.py file. These endpoints handle customer invoice creation, retrieval, updates, and deletion.

**API Purpose**: Manages customer invoices with support for multiple products, categories, and real-world POS functionality.
**Key Features**: Create, read, update, delete customer invoices with detailed product information and PDF receipts.

## Base URL
All endpoints are prefixed with `/customer-invoice/` (handled via the customer-invoice router).

## Authentication
All endpoints require admin authentication via RBAC (Role-Based Access Control). To obtain an access token, use the login endpoint:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Use the returned `access_token` in the Authorization header:
```
Authorization: Bearer ACCESS_TOKEN_FROM_LOGIN
```

## Endpoints

### 1. Get Customer Details
**POST** `/customer-invoice/GetCustomerDetails`

Retrieves customer details by name.

#### Query Parameter:
- `cus_name`: Customer name (string, optional)

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
curl -X POST "http://localhost:8000/customer-invoice/GetCustomerDetails?cus_name=John%20Doe" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 2. Get Salesman Details
**POST** `/customer-invoice/Getsalesmandetail`

Retrieves salesman details by name.

#### Query Parameter:
- `sal_name`: Salesman name (string, optional)

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

### 3. Save Customer Orders
**POST** `/customer-invoice/SaveCustomerOrders`

Saves customer orders (customer invoice creation).

#### Request Body:
- `orderItems`: List of order items (array of objects)
- `timezone`: Timezone information (string, optional)
- `Date`: Date information (string, optional)

#### Response:
Base64-encoded PDF report.

#### Example Request:
```bash
curl -X POST http://localhost:8000/customer-invoice/SaveCustomerOrders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -d '{
    "orderItems": [
      {
        "pro_name": "Test Product",
        "pro_quantity": 2,
        "unit_price": 10.0,
        "total_price": 20.0,
        "discount": 0.0,
        "cat_name": "Test Category",
        "or_cus_id_fk": "customer-id-uuid",
        "payment_mod": "cash",
        "cricktshirt_Neckstyle": "Style A",
        "cricktshirt_sleeve": "Full Sleeve",
        "imgfile": "base64image...",
        "remarks": "Test order"
      }
    ],
    "timezone": "UTC",
    "Date": "2026-02-04"
  }'
```

### 4. Get Customer Invoice Balance
**POST** `/customer-invoice/GetCustomerInvoiceBalance`

Get customer invoice balance.

#### Query Parameter:
- `customer_id`: Customer ID (string, optional)

#### Response:
```json
{
  "cus_balance": "number"
}
```

#### Example Request:
```bash
curl -X POST "http://localhost:8000/customer-invoice/GetCustomerInvoiceBalance?customer_id=customer-uuid" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 5. Update Customer Invoice
**PUT** `/customer-invoice/UpdateCustomerInvoice/{invoice_id}`

Update a customer invoice by ID.

#### Path Parameter:
- `invoice_id`: Invoice ID (string)

#### Query Parameters:
- `e_name`: New invoice name (string, optional)
- `e_amount`: New amount (float, optional)
- `note`: Note (string, optional)

#### Response:
Updated invoice details.

#### Example Request:
```bash
curl -X PUT "http://localhost:8000/customer-invoice/UpdateCustomerInvoice/invoice-uuid?e_name=INV-UPDATED-001&e_amount=150.0&note=Updated invoice" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 6. Get Order Details
**GET** `/customer-invoice/Getorder/{id}`

Retrieve specific order details by ID (customer invoice).

#### Path Parameter:
- `id`: Order ID (string)

#### Response:
Order details.

#### Example Request:
```bash
curl -X GET "http://localhost:8000/customer-invoice/Getorder/order-uuid" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 7. View Customer Orders
**GET** `/customer-invoice/Viewcustomerorder`

View customer orders (customer invoices) with optional search and status filtering.

#### Query Parameters (optional):
- `searchString`: Search string
- `status`: Status filter
- `skip`: Skip count (default: 0)
- `limit`: Limit count (default: 100)

#### Response:
List of customer orders.

#### Example Request:
```bash
curl -X GET "http://localhost:8000/customer-invoice/Viewcustomerorder?searchString=test&status=issued&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 8. Customer Order Report
**GET** `/customer-invoice/customerorderreport`

Generate customer order report in PDF format.

#### Query Parameters (optional):
- `orderid`: Specific order ID
- `timezone`: Timezone
- `printoption`: Print option

#### Response:
Base64-encoded PDF report.

#### Example Request:
```bash
curl -X GET "http://localhost:8000/customer-invoice/customerorderreport?orderid=order-uuid&printoption=Yes" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 9. Delete Customer Order
**POST** `/customer-invoice/Deletecustomorder/{id}`

Delete a customer invoice by ID (mapped to work with customer invoices).

#### Path Parameter:
- `id`: Invoice ID (string)

#### Response:
```json
{
  "success": true,
  "message": "Customer invoice deleted successfully"
}
```

#### Example Request:
```bash
curl -X POST "http://localhost:8000/customer-invoice/Deletecustomorder/invoice-uuid" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 10. Create Customer
**POST** `/customer-invoice/Customers`

Create a new customer from the modal.

#### Query Parameters:
- `cus_name`: Customer name (string, required)
- `cus_phone`: Customer phone (string, required)
- `cus_address`: Customer address (string, required)
- `cus_cnic`: Customer CNIC (string, required)
- `cus_sal_id_fk`: Salesman ID (string, optional)

#### Response:
Created customer details.

#### Example Request:
```bash
curl -X POST "http://localhost:8000/customer-invoice/Customers?cus_name=Test%20Customer&cus_phone=1234567890&cus_address=123%20Test%20Street&cus_cnic=1234567890123&cus_sal_id_fk=salesman-uuid" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 11. Get Salesman Details (Alternative)
**POST** `/customer-invoice/GetSalesmanDetails`

Get salesman details by name.

#### Query Parameter:
- `sal_name`: Salesman name (string, optional)

#### Response:
Salesman details.

#### Example Request:
```bash
curl -X POST "http://localhost:8000/customer-invoice/GetSalesmanDetails?sal_name=Test%20Salesman" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 12. Get Customer Balance
**POST** `/customer-invoice/customerbalance`

Get customer balance by name.

#### Query Parameter:
- `cus_name`: Customer name (string, optional)

#### Response:
```json
{
  "cus_id": "string",
  "cus_balance": "number"
}
```
OR
```json
{
  "error": "Customer not found"
}
```

#### Example Request:
```bash
curl -X POST "http://localhost:8000/customer-invoice/customerbalance?cus_name=Test%20Customer" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 13. Get Customer Invoices by Date
**GET** `/customer-invoice/customerinvoicesbydate`

Retrieves all customer invoices for a specific date with total amounts and detailed product information.

#### Query Parameter:
- `date`: Date in YYYY-MM-DD format (string, required)

#### Response:
```json
{
  "date": "string",
  "total_invoices": "number",
  "total_amount": "number",
  "invoices": [
    {
      "invoice_id": "string",
      "invoice_no": "string",
      "customer_id": "string",
      "total_amount": "number",
      "created_at": "string",
      "products": [
        {
          "Orderid": "string",
          "Product": "string",
          "Price": "number",
          "Amount Paid": "number",
          "Quantity": "number",
          "Discount": "number",
          "Total Discount": "number",
          "Cost": "number",
          "Time": "string",
          "Date": "string"
        }
      ]
    }
  ]
}
```

#### Example Request:
```bash
curl -X GET "http://localhost:8000/customer-invoice/customerinvoicesbydate?date=2026-02-04" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

#### Real World Usage Notes:
- **Current System**: The system uses date-based sequential invoice numbers (e.g., "CUSTINV-20260204-001") which include the date for organization.
- **Recommended Real-World Format**: For practical billing, use simple prefix-based sequential numbering like "CIN-0001", "CIN-0002", etc. This keeps the brand prefix but removes date complexity.
- **Benefits of Simple Format**:
  - Easy for customers to remember and reference
  - Clean, professional appearance on bills
  - Consistent branding with "CIN" prefix
  - Simple sequential numbering without date clutter
- **Implementation Change Needed**: To implement CIN-0001 format, the SaveCustomerOrders function in customer_invoice.py needs modification to use global sequential numbering instead of date-based numbering.
- **Internal UUID Identifiers**: The internal invoice_id uses UUIDs for security, uniqueness, and to prevent enumeration attacks - these are used for system operations only.
- **Best Practice**: Show the simple, readable invoice_no (like "CIN-0001") to users/customers on bills, while using the UUID invoice_id for internal operations, API calls, and database queries.
- **Format Recommendation**: Simple prefix-based sequential numbering (CIN-0001, CIN-0002) is ideal for billing as it's memorable, professional, and maintains brand identity.

## Error Handling
All endpoints return appropriate HTTP status codes:
- `200`: Success
- `400`: Bad Request (invalid input)
- `404`: Not Found
- `401`: Unauthorized
- `403`: Forbidden (insufficient permissions)
- `500`: Internal Server Error