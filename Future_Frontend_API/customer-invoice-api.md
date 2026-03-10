# Customer Invoice & Order API

## 🔐 Authentication & Authorization

### Login Required

Before using any of these endpoints, you **MUST** login first:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }' \
  -c cookies.txt
```

**Save the cookie!** All subsequent requests require the session cookie (`-b cookies.txt`).

---

### 🔑 Access Control

| Decorator | Allowed Roles | Used By |
|-----------|--------------|---------|
| `admin_cashier_employee_required_from_session()` | `admin`, `cashier`, `employee` | GET operations |
| `cashier_required_from_session()` | `admin`, `cashier` | POST operations |
| `admin_required_from_session()` | `admin` only | DELETE operations |

---

## API Endpoints

### Customer Management

---

### 1. POST /customerinvoice/Customers - Create Customer

**Access**: `cashier_required_from_session()` - **Admin, Cashier**

**Description**: Create a new customer.

**Endpoint**: `POST /customerinvoice/Customers`

**Request Body**:
```json
{
  "cus_name": "John Doe",
  "cus_phone": "03001234567",
  "cus_cnic": "4210112345678",
  "cus_address": "123 Main Street",
  "cus_sal_id_fk": "uuid-string",
  "branch": "European Sports Light House"
}
```

**Request Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `cus_name` | string | ✅ Yes | Customer name |
| `cus_phone` | string | ✅ Yes | Phone number |
| `cus_cnic` | string | ✅ Yes | CNIC number |
| `cus_address` | string | ✅ Yes | Address |
| `cus_sal_id_fk` | string | ❌ No | Salesman ID |
| `branch` | string | ❌ No | Branch name |

**Example**:
```bash
curl -X POST "http://localhost:8000/customerinvoice/Customers" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "cus_name": "John Doe",
    "cus_phone": "03001234567",
    "cus_cnic": "4210112345678",
    "cus_address": "123 Main Street",
    "branch": "European Sports Light House"
  }'
```

**Response** (200 OK):
```json
{
  "cus_id": "uuid-string",
  "cus_name": "John Doe",
  "cus_phone": "03001234567",
  "cus_cnic": "4210112345678",
  "cus_address": "123 Main Street",
  "cus_sal_id_fk": null,
  "branch": "European Sports Light House",
  "cus_balance": 0.00
}
```

---

### 2. GET /customers/viewcustomer - View Customers (Paginated)

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get paginated list of customers with search.

**Endpoint**: `GET /customers/viewcustomer?page=1&limit=8&search_string=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `limit` | int | 8 | Items per page |
| `search_string` | string | - | Search by name or phone |

**Example**:
```bash
curl -X GET "http://localhost:8000/customers/viewcustomer?page=1&limit=8&search_string=John" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "data": [
    {
      "cus_id": "uuid-string",
      "cus_name": "John Doe",
      "cus_phone": "03001234567",
      "cus_cnic": "4210112345678",
      "cus_address": "123 Main Street",
      "cus_balance": 1500.00,
      "cus_sal_id_fk": "uuid-string",
      "branch": "European Sports Light House"
    }
  ],
  "page": 1,
  "limit": 8,
  "total": 50,
  "total_pages": 7
}
```

---

### 3. PUT /customers/{id} - Update Customer

**Access**: `cashier_required_from_session()` - **Admin, Cashier**

**Description**: Update an existing customer.

**Endpoint**: `PUT /customers/{id}`

**Path Parameter**: `id` - UUID of the customer

**Request Body**:
```json
{
  "name": "John Doe Updated",
  "contacts": "{\"phone\": \"03001234567\", \"email\": \"\", \"address\": \"456 New Street\"}",
  "billing_addr": "{\"street\": \"456 New Street\", \"city\": \"\", \"country\": \"\"}",
  "shipping_addr": "{\"street\": \"456 New Street\", \"city\": \"\", \"country\": \"\"}",
  "cnic": "4210112345678",
  "sal_id_fk": "uuid-string",
  "branch": "European Sports Light House"
}
```

**Example**:
```bash
curl -X PUT "http://localhost:8000/customers/uuid-string" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "John Doe Updated",
    "contacts": "{\"phone\": \"03001234567\", \"address\": \"456 New Street\"}",
    "cnic": "4210112345678"
  }'
```

**Response** (200 OK):
```json
{
  "cus_id": "uuid-string",
  "cus_name": "John Doe Updated",
  "cus_phone": "03001234567",
  "cus_cnic": "4210112345678",
  "cus_address": "456 New Street",
  "cus_sal_id_fk": "uuid-string",
  "branch": "European Sports Light House"
}
```

---

### 4. DELETE /customers/{id} - Delete Customer

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Delete a customer by ID.

**Endpoint**: `DELETE /customers/{id}`

**Path Parameter**: `id` - UUID of the customer

**Example**:
```bash
curl -X DELETE "http://localhost:8000/customers/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "message": "Customer deleted successfully"
}
```

---

### 5. GET /customerinvoice/customerbalance/{customer_id} - Get Customer Balance

**Access**: `cashier_required_from_session()` - **Admin, Cashier**

**Description**: Get total balance for a customer from unpaid invoices.

**Endpoint**: `GET /customerinvoice/customerbalance/{customer_id}`

**Path Parameter**: `customer_id` - UUID of the customer

**Example**:
```bash
curl -X GET "http://localhost:8000/customerinvoice/customerbalance/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "customer_id": "uuid-string",
  "total_balance": 1500.00
}
```

---

### 6. GET /admin/getcustomervendorbybranch - Get Salesmen

**Access**: `employee_required_from_session()` - **Any authenticated user**

**Description**: Get list of salesmen for dropdown (used in customer form).

**Endpoint**: `GET /admin/getcustomervendorbybranch`

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/getcustomervendorbybranch" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "salesmans": [
    {
      "sal_id": "uuid-string",
      "sal_name": "Salesman John"
    }
  ],
  "customers": [],
  "vendors": []
}
```

---

### Customer Invoice / Order Management

---

### 7. GET /customerinvoice/viewcustomerorder - View Customer Orders

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get paginated list of customer orders (invoices) with search and status filter.

**Endpoint**: `GET /customerinvoice/viewcustomerorder?skip=0&limit=8&searchString=&order_status=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | int | 0 | Records to skip |
| `limit` | int | 8 | Items per page |
| `searchString` | string | - | Search by invoice_no, customer_name, team_name |
| `order_status` | string | - | Filter by status (PENDING, DELIVERED, COMPLETED, CANCEL) |

**Example**:
```bash
curl -X GET "http://localhost:8000/customerinvoice/viewcustomerorder?skip=0&limit=8&searchString=CIN-0007" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "data": [
    {
      "orderid": "uuid-string",
      "invoice_no": "CIN-0007",
      "status": "PENDING",
      "customer": "John Doe",
      "teamname": "Team A",
      "quantity": 5,
      "total_amount": 5000.00,
      "date": "2026-03-10T10:00:00"
    }
  ],
  "page": 1,
  "limit": 8,
  "total": 50,
  "total_pages": 7,
  "has_more": true
}
```

**Important**: Search works across **all records** (not just current page) in:
- `invoice_no` (e.g., "CIN-0007")
- `customer_name`
- `team_name`
- `items` (JSON field)

---

### 8. POST /customerinvoice/SaveCustomerOrders - Create Invoice

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Create a new customer invoice/order.

**Endpoint**: `POST /customerinvoice/SaveCustomerOrders`

**Request Body**:
```json
{
  "customer_id": "uuid-string",
  "customer_name": "John Doe",
  "team_name": "Team A",
  "salesman_id": "uuid-string",
  "items": "[{\"product_id\": \"uuid\", \"product_name\": \"Product A\", \"quantity\": 2, \"unit_price\": 1000}]",
  "totals": "{\"subtotal\": 2000, \"tax\": 0, \"total\": 2000}",
  "total_amount": 2000.00,
  "payment_method": "cash",
  "status": "PENDING",
  "notes": "Deliver by Friday"
}
```

**Request Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `customer_id` | string | ✅ Yes | Customer UUID |
| `customer_name` | string | ✅ Yes | Customer name |
| `team_name` | string | ❌ No | Team name |
| `salesman_id` | string | ❌ No | Salesman UUID |
| `items` | string | ✅ Yes | JSON array of items |
| `totals` | string | ✅ Yes | JSON totals object |
| `total_amount` | number | ✅ Yes | Total amount |
| `payment_method` | string | ❌ No | Payment method |
| `status` | string | ❌ No | Order status |
| `notes` | string | ❌ No | Additional notes |

**Example**:
```bash
curl -X POST "http://localhost:8000/customerinvoice/SaveCustomerOrders" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "customer_id": "uuid-string",
    "customer_name": "John Doe",
    "items": "[{\"product_id\": \"uuid\", \"product_name\": \"Product A\", \"quantity\": 2, \"unit_price\": 1000}]",
    "totals": "{\"subtotal\": 2000, \"tax\": 0, \"total\": 2000}",
    "total_amount": 2000.00,
    "status": "PENDING"
  }'
```

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "invoice_no": "CIN-0008",
  "customer_id": "uuid-string",
  "customer_name": "John Doe",
  "total_amount": 2000.00,
  "status": "PENDING",
  "created_at": "2026-03-10T10:00:00"
}
```

---

### 9. PUT /customerinvoice/update-status/{order_id} - Update Order Status

**Access**: `cashier_required_from_session()` - **Admin, Cashier**

**Description**: Update the status of a customer order.

**Endpoint**: `PUT /customerinvoice/update-status/{order_id}`

**Path Parameter**: `order_id` - UUID of the order

**Request Body**:
```json
{
  "status": "COMPLETED"
}
```

**Available Statuses**:
- `PENDING` - Order pending
- `DELIVERED` - Order delivered
- `COMPLETED` - Order completed
- `CANCEL` - Order cancelled

**Example**:
```bash
curl -X PUT "http://localhost:8000/customerinvoice/update-status/uuid-string" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "status": "COMPLETED"
  }'
```

**Response** (200 OK):
```json
{
  "orderid": "uuid-string",
  "invoice_no": "CIN-0007",
  "status": "COMPLETED",
  "message": "Order status updated successfully"
}
```

---

### 10. DELETE /customerinvoice/{id} - Delete Order

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Delete a customer order by ID.

**Endpoint**: `DELETE /customerinvoice/{id}`

**Path Parameter**: `id` - UUID of the order

**Example**:
```bash
curl -X DELETE "http://localhost:8000/customerinvoice/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "message": "Order deleted successfully"
}
```

---

### 11. GET /api/customers/report - Customer Report

**Access**: `employee_required_from_session()` - **Any authenticated user**

**Description**: Get customer details report (used by ReportModal).

**Endpoint**: `GET /customers/report`

**Example**:
```bash
curl -X GET "http://localhost:8000/customers/report" \
  -b cookies.txt
```

**Response**: Returns customer report data (format depends on implementation).

---

## Frontend API Routes

The frontend uses Next.js API routes as proxies:

| Frontend Route | Backend Endpoint |
|----------------|------------------|
| `POST /api/customerinvoice/Customers` | `POST /customerinvoice/Customers` |
| `GET /api/customers/viewcustomer` | `GET /customers/viewcustomer` |
| `PUT /api/customers/{id}` | `PUT /customers/{id}` |
| `DELETE /api/customers/{id}` | `DELETE /customers/{id}` |
| `GET /api/customerinvoice/customerbalance/{id}` | `GET /customerinvoice/customerbalance/{id}` |
| `GET /api/admin/getcustomervendorbybranch` | `GET /admin/getcustomervendorbybranch` |
| `GET /api/customerinvoice/viewcustomerorder` | `GET /customerinvoice/viewcustomerorder` |
| `POST /api/customerinvoice/SaveCustomerOrders` | `POST /customerinvoice/SaveCustomerOrders` |
| `PUT /api/customerinvoice/update-status/{id}` | `PUT /customerinvoice/update-status/{id}` |
| `DELETE /api/customerinvoice/{id}` | `DELETE /customerinvoice/{id}` |

---

## Error Codes

| HTTP Status | Meaning | Common Causes |
|-------------|---------|---------------|
| 200 | OK | Success |
| 400 | Bad Request | Invalid input, missing required fields |
| 401 | Unauthorized | Not logged in, invalid session |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Customer/Order not found |
| 500 | Server Error | Database error, server issue |

---

## Testing Checklist

### Login First
- [ ] Login with admin credentials
- [ ] Save cookies (`-c cookies.txt`)

### Test Customer APIs
- [ ] Create new customer
- [ ] Fetch customers (paginated)
- [ ] Search customers by name
- [ ] Update customer details
- [ ] Delete customer (admin only)
- [ ] Get customer balance

### Test Customer Order APIs
- [ ] Fetch orders (paginated)
- [ ] Search orders by invoice number (CIN-0007)
- [ ] Filter orders by status
- [ ] Create new invoice/order
- [ ] Update order status
- [ ] Delete order (admin only)

### Test Salesman API
- [ ] Fetch salesmen for dropdown

---

## Related Documentation

- [Authentication](authentication_api.md) - Login and session management
- [User Management](administrative_api.md) - User CRUD operations
- [Product API](productapi.md) - Product management
- [Stock API](stockapi.md) - Stock management
