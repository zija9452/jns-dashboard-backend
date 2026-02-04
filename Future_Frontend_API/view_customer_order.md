# View Customer Order API Documentation

## Overview
This document outlines the Customer Order API endpoints that are compatible with the JavaScript frontend code provided. These endpoints handle customer order creation, retrieval, updates, deletion and reporting.

**API Purpose**: Manages customer orders with support for status updates, searching, filtering, and PDF reporting.
**Key Features**: Create, read, update, delete customer orders with detailed status tracking and PDF reports.

## Base URL
All endpoints are prefixed with `/admin/` (handled via the admin router).

## Authentication
All endpoints require admin authentication via RBAC (Role-Based Access Control). Use the following header:
```
Authorization: Bearer YOUR_ACCESS_TOKEN_HERE
```

## Endpoints

### 1. Get Customer Order by ID
**GET** `/admin/Getorder/{id}`

Retrieves specific customer order details by ID.

#### Path Parameter:
- `id`: Customer order ID (string)

#### Response:
```json
{
  "orderid": "string",
  "status": "string"
}
```

#### Example Request:
```bash
curl -X GET http://localhost:8000/admin/Getorder/order-uuid-string \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 2. View Customer Orders
**GET** `/admin/Viewcustomerorder`

Retrieves customer orders with optional search and filtering capabilities.

#### Query Parameters (optional):
- `searchString`: Search term to filter customer orders by name, order ID, etc.
- `status`: Filter by order status (e.g., pending, completed, cancelled)
- `skip`: Number of records to skip for pagination (default: 0)
- `limit`: Maximum number of records to return (default: 100)

#### Response:
Returns HTML table content for dynamic loading in the frontend.

#### Example Request:
```bash
curl -X GET "http://localhost:8000/admin/Viewcustomerorder?searchString=test&status=pending&limit=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 3. Generate Customer Order Report
**GET** `/admin/customerorderreport`

Generates a PDF report for a specific customer order.

#### Query Parameters:
- `orderid`: Order ID to generate report for (string, required)
- `timezone`: Client timezone information (string)
- `printoption`: Print option flag (string)

#### Response:
Returns a base64-encoded PDF report.

#### Example Request:
```bash
curl -X GET "http://localhost:8000/admin/customerorderreport?orderid=order-uuid-string&timezone=UTC&printoption=No" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

### 4. Delete Customer Order
**POST** `/admin/Deletecustomorder/{id}`

Deletes a specific customer order by ID.

#### Path Parameter:
- `id`: Customer order ID to delete (string)

#### Response:
```json
{
  "success": true,
  "message": "Order deleted successfully"
}
```

#### Example Request:
```bash
curl -X POST http://localhost:8000/admin/Deletecustomorder/order-uuid-string \
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

### Order Status Tracking
Supported order statuses include:
- `pending`
- `processing`
- `completed`
- `cancelled`
- `delivered`

### Search Capabilities
The Viewcustomerorder endpoint supports:
- Full-text search across order fields
- Status-based filtering
- Pagination for large datasets

## Security
- All endpoints require admin authentication
- Input validation is performed on all requests
- SQL injection protection through parameterized queries
- Proper error handling without exposing sensitive information

## Notes
- Customer orders are separate from customer invoices
- The system maintains order history for audit purposes
- PDF reports include timezone-aware timestamps