# Walk-in Refund API

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
| `cashier_required_from_session()` | `admin`, `cashier` | POST, PUT operations |

---

## API Endpoints

### Refund CRUD Operations

---

### 1. POST /walkinrefund/refunds/walkin-invoice - Create Refund

**Access**: `cashier_required_from_session()` - **Admin, Cashier**

**Description**: Create a refund for a walk-in invoice. Restores inventory quantities.

**Endpoint**: `POST /walkinrefund/refunds/walkin-invoice`

**Request Body**:
```json
{
  "invoice_id": "uuid-string",
  "refund_amount": 189.98,
  "refund_method": "cash",
  "reason": "Product defective",
  "refund_date": "2026-03-10",
  "items": [
    {
      "product_id": "uuid-string",
      "quantity": 2,
      "unit_price": 99.99,
      "discount": 5.00
    }
  ]
}
```

**Request Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `invoice_id` | string | ✅ Yes | Original invoice UUID |
| `refund_amount` | number | ✅ Yes | Total refund amount |
| `refund_method` | string | ✅ Yes | cash, easypaisa, bank |
| `reason` | string | ✅ Yes | Reason for refund |
| `refund_date` | string | ❌ No | Refund date (YYYY-MM-DD) |
| `items` | array | ✅ Yes | Items being returned |

**Example**:
```bash
curl -X POST "http://localhost:8000/walkinrefund/refunds/walkin-invoice" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "invoice_id": "uuid-string",
    "refund_amount": 189.98,
    "refund_method": "cash",
    "reason": "Product defective",
    "items": [
      {
        "product_id": "uuid-string",
        "quantity": 2,
        "unit_price": 99.99,
        "discount": 5.00
      }
    ]
  }'
```

**Response** (200 OK):
```json
{
  "refund_id": "uuid-string",
  "invoice_no": "WIV-001",
  "refund_amount": 189.98,
  "refund_method": "cash",
  "status": "completed",
  "message": "Refund processed successfully. Inventory restored."
}
```

**Important**: 
- Creates refund record
- **Restores inventory** quantities
- Updates original invoice payment status if partial refund

---

### 2. GET /walkinrefund/refunds/walkin-invoice - Get Refunds

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get walk-in invoice refunds with optional date filter.

**Endpoint**: `GET /walkinrefund/refunds/walkin-invoice?date=&page=1&limit=8`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `date` | string | today | Filter by date (YYYY-MM-DD) |
| `page` | int | 1 | Page number |
| `limit` | int | 8 | Items per page |

**Example**:
```bash
curl -X GET "http://localhost:8000/walkinrefund/refunds/walkin-invoice?date=2026-03-10&page=1&limit=8" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "refunds": [
    {
      "refund_id": "uuid-string",
      "invoice_id": "uuid-string",
      "invoice_no": "WIV-001",
      "refund_amount": 189.98,
      "refund_method": "cash",
      "reason": "Product defective",
      "refund_date": "2026-03-10",
      "created_by": "uuid-string",
      "created_at": "2026-03-10T15:00:00"
    }
  ],
  "total": 5,
  "page": 1,
  "limit": 8,
  "total_pages": 1
}
```

---

### 3. GET /walkinrefund/refunds/walkin-invoice/{refund_id} - Get Refund Details

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get specific refund details by ID.

**Endpoint**: `GET /walkinrefund/refunds/walkin-invoice/{refund_id}`

**Path Parameter**: `refund_id` - UUID of the refund

**Example**:
```bash
curl -X GET "http://localhost:8000/walkinrefund/refunds/walkin-invoice/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "refund_id": "uuid-string",
  "invoice_id": "uuid-string",
  "invoice_no": "WIV-001",
  "refund_amount": 189.98,
  "refund_method": "cash",
  "reason": "Product defective",
  "refund_date": "2026-03-10",
  "items": [
    {
      "product_id": "uuid-string",
      "product_name": "Nike Air Max",
      "quantity": 2,
      "unit_price": 99.99,
      "discount": 5.00
    }
  ],
  "created_by": "uuid-string",
  "created_at": "2026-03-10T15:00:00",
  "updated_at": "2026-03-10T15:00:00"
}
```

---

### 4. GET /walkinrefund/refunds/walkin-invoice/daily/{date_str} - Daily Refunds

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get all refunds for a specific date.

**Endpoint**: `GET /walkinrefund/refunds/walkin-invoice/daily/{date_str}`

**Path Parameter**: `date_str` - Date in YYYY-MM-DD format

**Example**:
```bash
curl -X GET "http://localhost:8000/walkinrefund/refunds/walkin-invoice/daily/2026-03-10" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "date": "2026-03-10",
  "total_refunds": 3,
  "total_refund_amount": 569.94,
  "refunds": [
    {
      "refund_id": "uuid-string",
      "invoice_no": "WIV-001",
      "refund_amount": 189.98,
      "refund_method": "cash",
      "reason": "Product defective"
    }
  ]
}
```

---

### 5. GET /walkinrefund/refunds/walkin-invoice/invoice/{invoice_id} - Invoice Refunds

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get all refunds for a specific invoice.

**Endpoint**: `GET /walkinrefund/refunds/walkin-invoice/invoice/{invoice_id}`

**Path Parameter**: `invoice_id` - UUID of the invoice

**Example**:
```bash
curl -X GET "http://localhost:8000/walkinrefund/refunds/walkin-invoice/invoice/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "invoice_id": "uuid-string",
  "invoice_no": "WIV-001",
  "total_refunds": 2,
  "total_refund_amount": 189.98,
  "refunds": [
    {
      "refund_id": "uuid-string",
      "refund_amount": 99.99,
      "refund_method": "cash",
      "reason": "Wrong size",
      "refund_date": "2026-03-10"
    },
    {
      "refund_id": "uuid-string-2",
      "refund_amount": 89.99,
      "refund_method": "cash",
      "reason": "Product defective",
      "refund_date": "2026-03-11"
    }
  ]
}
```

---

### 6. PUT /walkinrefund/refunds/walkin-invoice/{refund_id} - Update Refund

**Access**: `cashier_required_from_session()` - **Admin, Cashier**

**Description**: Update refund details including date and amount.

**Endpoint**: `PUT /walkinrefund/refunds/walkin-invoice/{refund_id}`

**Path Parameter**: `refund_id` - UUID of the refund

**Request Body** (all fields optional):
```json
{
  "refund_amount": 199.98,
  "refund_method": "easypaisa",
  "reason": "Updated reason",
  "refund_date": "2026-03-11"
}
```

**Example**:
```bash
curl -X PUT "http://localhost:8000/walkinrefund/refunds/walkin-invoice/uuid-string" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "refund_amount": 199.98,
    "reason": "Updated reason"
  }'
```

**Response** (200 OK):
```json
{
  "refund_id": "uuid-string",
  "message": "Refund updated successfully"
}
```

---

### 7. DELETE /walkinrefund/refunds/walkin-invoice/{refund_id} - Delete Refund

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Delete a refund. Reverses inventory restoration.

**Endpoint**: `DELETE /walkinrefund/refunds/walkin-invoice/{refund_id}`

**Path Parameter**: `refund_id` - UUID of the refund

**Example**:
```bash
curl -X DELETE "http://localhost:8000/walkinrefund/refunds/walkin-invoice/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "message": "Refund deleted successfully. Inventory adjustment reversed."
}
```

**Important**: 
- Deletes refund record
- **Reverses inventory restoration** (decreases stock back)
- Only admins can delete refunds

---

## Frontend API Routes

| Frontend Route | Backend Endpoint |
|----------------|------------------|
| `POST /api/refunds/walkin-invoice` | `POST /walkinrefund/refunds/walkin-invoice` |
| `GET /api/refunds/walkin-invoice` | `GET /walkinrefund/refunds/walkin-invoice` |
| `PUT /api/refunds/walkin-invoice/{id}` | `PUT /walkinrefund/refunds/walkin-invoice/{id}` |
| `GET /api/refunds/walkin-invoice/{id}` | `GET /walkinrefund/refunds/walkin-invoice/{id}` |

**Example** - Frontend create refund:
```typescript
const createRefund = async (refundData: any) => {
  const response = await fetch('/api/refunds/walkin-invoice', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(refundData),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to create refund');
  }

  return response.json();
};
```

---

## Error Codes

| HTTP Status | Meaning | Common Causes |
|-------------|---------|---------------|
| 200 | OK | Success |
| 400 | Bad Request | Invalid input, invalid invoice ID |
| 401 | Unauthorized | Not logged in, invalid session |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Invoice not found, refund not found |
| 500 | Server Error | Database error, server issue |

---

## Testing Checklist

### Login First
- [ ] Login with admin credentials
- [ ] Save cookies (`-c cookies.txt`)

### Test Create Refund
- [ ] Create refund for walk-in invoice
- [ ] Verify inventory restored
- [ ] Try create without items (should fail)
- [ ] Try create for non-existent invoice (should 404)

### Test Get Refunds
- [ ] Get refunds for today
- [ ] Get refunds by date
- [ ] Get refund by ID
- [ ] Get refunds for specific invoice
- [ ] Get daily refunds

### Test Update Refund
- [ ] Update refund amount
- [ ] Update refund reason
- [ ] Try update as non-admin/cashier (should fail)

### Test Delete Refund
- [ ] Delete refund (admin only)
- [ ] Verify inventory adjustment reversed
- [ ] Try delete as non-admin (should fail)

---

## Related Documentation

- [Walk-in Invoice API](walkin-invoice-api.md) - Walk-in invoice management
- [Authentication](authentication_api.md) - Login and session management
