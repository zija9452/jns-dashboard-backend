# API Contracts: Regal POS Backend

**Date**: 2026-01-28
**Feature**: Regal POS Backend Clone

## Authentication Endpoints

### POST /auth/login
Authenticate user and return JWT tokens

**Request**:
```json
{
  "username": "string",
  "password": "string"
}
```

**Response (200)**:
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "username": "string",
    "email": "string",
    "full_name": "string",
    "role": "admin|cashier|employee",
    "is_active": true
  }
}
```

### POST /auth/refresh
Refresh access token using refresh token

**Request**:
```json
{
  "refresh_token": "string"
}
```

**Response (200)**:
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "token_type": "bearer",
  "expires_in": 900
}
```

### POST /auth/logout
Revoke refresh token and logout user

**Request**:
```json
{
  "refresh_token": "string"
}
```

**Response (200)**:
```json
{
  "message": "Successfully logged out"
}
```

## Product Management Endpoints

### GET /products
List products with pagination

**Query Parameters**:
- `limit`: integer (default: 50, max: 200)
- `offset`: integer (default: 0)
- `category`: string (optional filter)
- `search`: string (optional search term)

**Response (200)**:
```json
{
  "items": [
    {
      "id": "uuid",
      "sku": "string",
      "name": "string",
      "desc": "string",
      "unit_price": "decimal",
      "cost_price": "decimal",
      "tax_rate": "decimal",
      "stock_level": 0,
      "barcode": "string",
      "category": "string",
      "brand_action": "string"
    }
  ],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

### POST /products
Create a new product

**Request**:
```json
{
  "sku": "string",
  "name": "string",
  "desc": "string",
  "unit_price": "decimal",
  "cost_price": "decimal",
  "tax_rate": "decimal",
  "vendor_id": "uuid",
  "stock_level": 0,
  "attributes": {},
  "barcode": "string",
  "discount": "decimal",
  "category": "string",
  "branch": "string",
  "limited_qty": false,
  "brand_action": "string"
}
```

**Response (201)**:
```json
{
  "id": "uuid",
  "sku": "string",
  "name": "string",
  "desc": "string",
  "unit_price": "decimal",
  "cost_price": "decimal",
  "tax_rate": "decimal",
  "vendor_id": "uuid",
  "stock_level": 0,
  "attributes": {},
  "barcode": "string",
  "discount": "decimal",
  "category": "string",
  "branch": "string",
  "limited_qty": false,
  "brand_action": "string",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## Customer Management Endpoints

### GET /customers
List customers with pagination

**Query Parameters**:
- `limit`: integer (default: 50, max: 200)
- `offset`: integer (default: 0)
- `search`: string (optional search term)

**Response (200)**:
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "string",
      "contacts": {},
      "billing_addr": {},
      "shipping_addr": {},
      "credit_limit": "decimal"
    }
  ],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

## Invoice Management Endpoints

### GET /invoices
List invoices with pagination

**Query Parameters**:
- `limit`: integer (default: 50, max: 200)
- `offset`: integer (default: 0)
- `status`: string (optional filter: draft, issued, paid, cancelled)
- `customer_id`: uuid (optional filter)

**Response (200)**:
```json
{
  "items": [
    {
      "id": "uuid",
      "invoice_no": "string",
      "customer_id": "uuid",
      "items": [],
      "totals": {},
      "taxes": "decimal",
      "discounts": "decimal",
      "status": "draft|issued|paid|cancelled",
      "payments": []
    }
  ],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

### POST /invoices
Create a new invoice

**Request**:
```json
{
  "customer_id": "uuid",
  "items": [
    {
      "product_id": "uuid",
      "quantity": 0,
      "unit_price": "decimal",
      "total": "decimal"
    }
  ],
  "discounts": "decimal",
  "status": "draft"
}
```

**Response (201)**:
```json
{
  "id": "uuid",
  "invoice_no": "string",
  "customer_id": "uuid",
  "items": [],
  "totals": {},
  "taxes": "decimal",
  "discounts": "decimal",
  "status": "draft",
  "payments": [],
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## Stock Management Endpoints

### GET /stock
List stock entries with pagination

**Query Parameters**:
- `limit`: integer (default: 50, max: 200)
- `offset`: integer (default: 0)
- `product_id`: uuid (optional filter)
- `location`: string (optional filter)

**Response (200)**:
```json
{
  "items": [
    {
      "id": "uuid",
      "product_id": "uuid",
      "qty": 0,
      "type": "IN|OUT|ADJUST",
      "location": "string",
      "batch": "string",
      "expiry": "date",
      "ref": "string"
    }
  ],
  "total": 0,
  "limit": 50,
  "offset": 0
}
```

## Role-Based Access Control

All endpoints require appropriate authentication and authorization:

- **Admin**: Full access to all endpoints
- **Cashier**: Access to POS-related endpoints (invoices, quick sell, payments)
- **Employee**: Access to most endpoints but limited administrative functions

Unauthorized requests return a 401 or 403 status code with an error message.