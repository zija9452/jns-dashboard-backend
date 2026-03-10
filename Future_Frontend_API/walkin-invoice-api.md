# Walk-in Invoice API

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

### Walk-in Invoice CRUD Operations

---

### 1. POST /walkininvoice/walkin-invoices - Create Walk-in Invoice

**Access**: `cashier_required_from_session()` - **Admin, Cashier**

**Description**: Create a new walk-in invoice with immediate payment. Returns PDF receipt.

**Endpoint**: `POST /walkininvoice/walkin-invoices`

**Request Body**:
```json
{
  "items": [
    {
      "pro_name": "Nike Air Max",
      "pro_quantity": 2,
      "unit_price": 99.99,
      "discount": 5.00,
      "cat_name": "Shoes",
      "name": "Nike Air Max"
    }
  ],
  "customer_id": "uuid-string",
  "salesman_id": "uuid-string",
  "payment_method": "cash",
  "payment_date": "2026-03-10",
  "manual_discount": 0
}
```

**Request Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `items` | array | ✅ Yes | Array of items with pro_name, pro_quantity, unit_price, discount |
| `customer_id` | string | ✅ Yes | Customer UUID |
| `salesman_id` | string | ❌ No | Salesman UUID |
| `payment_method` | string | ✅ Yes | cash, easypaisa, bank, etc. |
| `payment_date` | string | ❌ No | Payment date (YYYY-MM-DD) |
| `manual_discount` | number | ❌ No | Additional manual discount |

**Example**:
```bash
curl -X POST "http://localhost:8000/walkininvoice/walkin-invoices" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "items": [
      {
        "pro_name": "Nike Air Max",
        "pro_quantity": 2,
        "unit_price": 99.99,
        "discount": 5.00,
        "cat_name": "Shoes"
      }
    ],
    "customer_id": "uuid-string",
    "payment_method": "cash"
  }'
```

**Response** (200 OK):
```json
{
  "invoice_id": "uuid-string",
  "invoice_no": "WIV-001",
  "total_amount": 189.98,
  "pdf": "base64-encoded-pdf-string"
}
```

**Note**: Response includes base64-encoded PDF receipt for printing.

---

### 2. GET /walkininvoice/walkin-invoices - Get Walk-in Invoices

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get list of walk-in invoices with pagination and filters.

**Endpoint**: `GET /walkininvoice/walkin-invoices?skip=0&limit=8&customer_id=&date=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `skip` | int | 0 | Records to skip |
| `limit` | int | 100 | Items per page |
| `customer_id` | string | - | Filter by customer ID |
| `date` | string | - | Filter by date (YYYY-MM-DD) |

**Example**:
```bash
curl -X GET "http://localhost:8000/walkininvoice/walkin-invoices?skip=0&limit=8" \
  -b cookies.txt
```

**Response** (200 OK):
```json
[
  {
    "invoice_id": "uuid-string",
    "invoice_no": "WIV-001",
    "customer_id": "uuid-string",
    "customer_name": "Walk-in Customer",
    "team_name": "",
    "quantity": 2,
    "total_amount": 189.98,
    "date": "2026-03-10",
    "status": "paid",
    "payment_method": "cash",
    "created_at": "2026-03-10T10:00:00"
  }
]
```

---

### 3. GET /walkininvoice/walkin-invoices/{invoice_id} - Get Invoice Details

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get specific walk-in invoice by ID.

**Endpoint**: `GET /walkininvoice/walkin-invoices/{invoice_id}`

**Path Parameter**: `invoice_id` - UUID of the invoice

**Example**:
```bash
curl -X GET "http://localhost:8000/walkininvoice/walkin-invoices/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "invoice_id": "uuid-string",
  "invoice_no": "WIV-001",
  "customer_id": "uuid-string",
  "salesman_id": "uuid-string",
  "items": "[{\"pro_name\": \"Nike Air Max\", \"pro_quantity\": 2, ...}]",
  "totals": "{\"subtotal\": 199.98, \"discount\": 10.00, \"total\": 189.98}",
  "total_amount": 189.98,
  "amount_paid": 189.98,
  "balance_due": 0.00,
  "payment_status": "paid",
  "payment_method": "cash",
  "status": "issued",
  "created_at": "2026-03-10T10:00:00"
}
```

---

### 4. PUT /walkininvoice/walkin-invoices/{invoice_id} - Update Invoice

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Update an existing walk-in invoice.

**Endpoint**: `PUT /walkininvoice/walkin-invoices/{invoice_id}`

**Path Parameter**: `invoice_id` - UUID of the invoice

**Request Body** (all fields optional):
```json
{
  "items": "updated items JSON",
  "totals": "updated totals JSON",
  "total_amount": 199.98,
  "amount_paid": 199.98,
  "payment_status": "paid",
  "status": "issued",
  "payment_method": "cash",
  "notes": "Updated notes"
}
```

**Example**:
```bash
curl -X PUT "http://localhost:8000/walkininvoice/walkin-invoices/uuid-string" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "notes": "Updated walk-in invoice"
  }'
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Invoice updated successfully"
}
```

---

### 5. DELETE /walkininvoice/walkin-invoices/{invoice_id} - Delete Invoice

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Delete a walk-in invoice by ID. Restores inventory quantities.

**Endpoint**: `DELETE /walkininvoice/walkin-invoices/{invoice_id}`

**Path Parameter**: `invoice_id` - UUID of the invoice

**Example**:
```bash
curl -X DELETE "http://localhost:8000/walkininvoice/walkin-invoices/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Invoice deleted successfully and inventory restored"
}
```

**Important**: Deleting an invoice restores the product stock levels that were reduced when the invoice was created.

---

### 6. GET /walkininvoice/walkin-invoices/{invoice_id}/receipt - Get Receipt

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get duplicate invoice receipt for an existing walk-in invoice.

**Endpoint**: `GET /walkininvoice/walkin-invoices/{invoice_id}/receipt`

**Path Parameter**: `invoice_id` - UUID of the invoice

**Example**:
```bash
curl -X GET "http://localhost:8000/walkininvoice/walkin-invoices/uuid-string/receipt" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "invoice_no": "WIV-001",
  "pdf": "base64-encoded-pdf-string"
}
```

**Note**: Returns base64-encoded PDF receipt for printing.

---

### 7. GET /walkininvoice/products-for-sales - Get Products for Sales

**Access**: `employee_required_from_session()` - **Employee, Cashier, Admin**

**Description**: Get products for salesman to select from during sales. Supports search filtering.

**Endpoint**: `GET /walkininvoice/products-for-sales?search_term=&barcode=&limit=50`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search_term` | string | - | Search by product name |
| `barcode` | string | - | Filter by barcode |
| `limit` | int | 50 | Max products to return |

**Example**:
```bash
curl -X GET "http://localhost:8000/walkininvoice/products-for-sales?search_term=Nike&limit=10" \
  -b cookies.txt
```

**Response** (200 OK):
```json
[
  {
    "id": "uuid-string",
    "sku": "SKU-123456",
    "name": "Nike Air Max",
    "unit_price": 99.99,
    "cost_price": 79.99,
    "stock_level": 50,
    "barcode": "1234567890123",
    "discount": 10.0,
    "category": "Shoes",
    "attributes": "product-image-url"
  }
]
```

---

### 8. GET /walkininvoice/daily-invoice-report/{date_str} - Daily Report

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Get daily invoice report showing all invoices and totals for a specific date.

**Endpoint**: `GET /walkininvoice/daily-invoice-report/{date_str}`

**Path Parameter**: `date_str` - Date in YYYY-MM-DD format

**Example**:
```bash
curl -X GET "http://localhost:8000/walkininvoice/daily-invoice-report/2026-03-10" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "date": "2026-03-10",
  "total_invoices": 15,
  "total_amount": 2850.00,
  "total_paid": 2850.00,
  "total_discount": 150.00,
  "invoices": [
    {
      "invoice_id": "uuid-string",
      "invoice_no": "WIV-001",
      "customer_id": "uuid-string",
      "total_amount": 189.98,
      "payment_method": "cash",
      "payment_status": "paid",
      "created_at": "2026-03-10T10:00:00",
      "products": [
        {
          "Product": "Nike Air Max",
          "Price": 99.99,
          "Quantity": 2,
          "Discount": 5.00,
          "Total": 189.98
        }
      ]
    }
  ]
}
```

---

## Daily Cash Management Endpoints

---

### 9. POST /walkininvoice/opening - Save Opening Balance

**Access**: `cashier_required_from_session()` - **Admin, Cashier**

**Description**: Save opening balance for the day (cash only).

**Endpoint**: `POST /walkininvoice/opening`

**Request Body**:
```json
{
  "date": "2026-03-10",
  "amount": 50000.00,
  "notes": "Opening balance for the day"
}
```

**Request Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `date` | string | ✅ Yes | Date (YYYY-MM-DD) |
| `amount` | number | ✅ Yes | Opening cash amount |
| `notes` | string | ❌ No | Additional notes |

**Example**:
```bash
curl -X POST "http://localhost:8000/walkininvoice/opening" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "date": "2026-03-10",
    "amount": 50000.00
  }'
```

**Response** (200 OK):
```json
{
  "message": "Opening balance saved successfully",
  "date": "2026-03-10",
  "amount": 50000.00
}
```

---

### 10. POST /walkininvoice/closing - Save Closing Balance

**Access**: `cashier_required_from_session()` - **Admin, Cashier**

**Description**: Save closing balance for the day.

**Endpoint**: `POST /walkininvoice/closing`

**Request Body**:
```json
{
  "date": "2026-03-10",
  "amount": 75000.00,
  "notes": "Closing balance for the day"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/walkininvoice/closing" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "date": "2026-03-10",
    "amount": 75000.00
  }'
```

**Response** (200 OK):
```json
{
  "message": "Closing balance saved successfully",
  "date": "2026-03-10",
  "amount": 75000.00
}
```

---

### 11. GET /walkininvoice/daily-cash/{date_str} - Get Daily Cash Record

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get daily cash record including opening, sales, expenses, and closing.

**Endpoint**: `GET /walkininvoice/daily-cash/{date_str}`

**Path Parameter**: `date_str` - Date in YYYY-MM-DD format

**Example**:
```bash
curl -X GET "http://localhost:8000/walkininvoice/daily-cash/2026-03-10" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "found": true,
  "date": "2026-03-10",
  "cash_opening": 50000.00,
  "total_sales": 100000.00,
  "total_expenses": 25000.00,
  "cash_closing": 125000.00,
  "total_closing": 125000.00,
  "expected_cash": 125000.00,
  "difference": 0.00,
  "opening_notes": "Opening balance",
  "closing_notes": "Closing balance"
}
```

---

### 12. GET /walkininvoice/today - Today's Sales Report

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get today's sales report with opening, sales, expenses, and cash in hand.

**Endpoint**: `GET /walkininvoice/today?date=2026-03-10`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date` | string | today | Date (YYYY-MM-DD) |

**Example**:
```bash
curl -X GET "http://localhost:8000/walkininvoice/today?date=2026-03-10" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "date": "2026-03-10",
  "opening": 50000.00,
  "sales": 100000.00,
  "expenses": 25000.00,
  "cash_in_hand": 125000.00,
  "has_opening": true,
  "has_closing": false
}
```

---

## Frontend API Routes

The frontend uses Next.js API routes as proxies:

| Frontend Route | Backend Endpoint |
|----------------|------------------|
| `POST /api/walkin-invoices` | `POST /walkininvoice/walkin-invoices` |
| `GET /api/walkin-invoices` | `GET /walkininvoice/walkin-invoices` |
| `GET /api/walkin-invoices/daily-cash/{date}` | `GET /walkininvoice/daily-cash/{date}` |
| `POST /api/walkin-invoices/opening` | `POST /walkininvoice/opening` |
| `POST /api/walkin-invoices/closing` | `POST /walkininvoice/closing` |
| `GET /api/walkin-invoices/today` | `GET /walkininvoice/today` |

**Example** - Frontend fetch for creating invoice:
```typescript
const createWalkinInvoice = async (invoiceData: any) => {
  const response = await fetch('/api/walkin-invoices', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(invoiceData),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to create invoice');
  }

  return response.json();
};
```

---

## Error Codes

| HTTP Status | Meaning | Common Causes |
|-------------|---------|---------------|
| 200 | OK | Success |
| 400 | Bad Request | Invalid input, missing required fields |
| 401 | Unauthorized | Not logged in, invalid session |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Invoice not found, daily cash not found |
| 500 | Server Error | Database error, server issue |

---

## Testing Checklist

### Login First
- [ ] Login with admin credentials
- [ ] Save cookies (`-c cookies.txt`)

### Test Create Invoice
- [ ] Create walk-in invoice with items
- [ ] Verify PDF receipt in response
- [ ] Verify stock levels reduced
- [ ] Try create without items (should fail)

### Test Get Invoices
- [ ] Fetch invoices with pagination
- [ ] Fetch invoice by ID
- [ ] Get duplicate receipt
- [ ] Fetch invoices by date

### Test Update/Delete
- [ ] Update invoice (admin only)
- [ ] Delete invoice (admin only)
- [ ] Verify stock restored after delete

### Test Daily Cash
- [ ] Save opening balance
- [ ] Get daily cash record
- [ ] Get today's sales report
- [ ] Save closing balance

### Test Products for Sales
- [ ] Fetch products with search
- [ ] Fetch products by barcode
- [ ] Verify only in-stock products returned

---

## Related Documentation

- [Authentication](authentication_api.md) - Login and session management
- [Customer Invoice API](customer-invoice-api.md) - Customer invoice management
- [Walkin Refund API](walkin-refund-api.md) - Refund operations
- [Sales View API](salesview_api.md) - Sales reports and analytics
