# Duplicate Bill API

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
| `admin_cashier_employee_required_from_session()` | `admin`, `cashier`, `employee` | Search invoices |
| `cashier_required_from_session()` | `admin`, `cashier` | Generate duplicate invoice |

---

## API Endpoints

---

### 1. GET /duplicatebill/search - Search Invoices

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Search for invoices from both walk-in (SIN-) and customer (CIN-) invoices. Returns last 24 hours data by default, or search results if query provided.

**Endpoint**: `GET /duplicatebill/search?search_query=&page=1&limit=8`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `search_query` | string | - | Search by invoice number, customer name, or team name |
| `page` | int | 1 | Page number for pagination |
| `limit` | int | 8 | Items per page (max 100) |

**Default Behavior**: If no search query, returns invoices from **last 24 hours**.

**Example** - Search by invoice number:
```bash
curl -X GET "http://localhost:8000/duplicatebill/search?search_query=CIN-0007&page=1&limit=8" \
  -b cookies.txt
```

**Example** - Get last 24 hours:
```bash
curl -X GET "http://localhost:8000/duplicatebill/search?page=1&limit=8" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "invoices": [
    {
      "id": "uuid-string",
      "invoice_no": "CIN-0007",
      "customer_name": "John Doe",
      "team_name": "Team A",
      "type": "customer",
      "total_amount": 5000.00,
      "amount_paid": 4000.00,
      "balance_due": 1000.00,
      "discount": 100.00,
      "payment_status": "partial",
      "payment_method": "cash",
      "payment_date": "2026-03-10T14:30:00",
      "created_at": "2026-03-05T10:00:00",
      "items": [
        {
          "product_name": "Nike Air Max",
          "quantity": 2,
          "unit_price": 2500.00,
          "discount": 50.00,
          "category": "Shoes"
        }
      ]
    }
  ],
  "total": 15,
  "page": 1,
  "limit": 8,
  "total_pages": 2,
  "search_query": "CIN-0007",
  "time_range": "search_results"
}
```

**Response Fields**:
- `invoices`: Array of invoices (paginated)
- `total`: Total number of matching invoices
- `page`: Current page number
- `limit`: Items per page
- `total_pages`: Total pages for pagination
- `search_query`: Search term used
- `time_range`: `search_results` or `last_24_hours`

**Search Fields**:
- Walk-in invoices: `invoice_no`, `customer_name`
- Customer invoices: `invoice_no`, `customer_name`, `team_name`

---

### 2. GET /duplicatebill/{invoice_id}/duplicate - Generate Duplicate Invoice

**Access**: `cashier_required_from_session()` - **Admin, Cashier**

**Description**: Generate duplicate invoice PDF with 7-day Redis cache.

**Endpoint**: `GET /duplicatebill/{invoice_id}/duplicate?invoice_type=`

**Path Parameter**: `invoice_id` - UUID of the invoice

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `invoice_type` | string | ✅ Yes | `walkin` or `customer` |

**Example** - Walk-in invoice:
```bash
curl -X GET "http://localhost:8000/duplicatebill/uuid-string/duplicate?invoice_type=walkin" \
  -b cookies.txt
```

**Example** - Customer invoice:
```bash
curl -X GET "http://localhost:8000/duplicatebill/uuid-string/duplicate?invoice_type=customer" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "pdf": "base64-encoded-pdf-string",
  "source": "cache",
  "bill_type": "DUPLICATE BILL"
}
```

**Response Fields**:
- `pdf`: Base64-encoded PDF string for printing
- `source`: `cache` (if from Redis) or `generated` (if newly created)
- `bill_type`: Always "DUPLICATE BILL"

**Caching**:
- PDFs are cached in Redis for **7 days** (604800 seconds)
- Cache key: `invoice:duplicate:{type}:{id}`
- Subsequent requests return cached PDF (faster response)

---

## Frontend API Routes

| Frontend Route | Backend Endpoint |
|----------------|------------------|
| `GET /api/duplicatebill/search` | `GET /duplicatebill/search` |
| `GET /api/duplicatebill/{id}/duplicate` | `GET /duplicatebill/{id}/duplicate` |

**Example** - Frontend search:
```typescript
const searchInvoices = async (query: string, page: number = 1) => {
  const params = new URLSearchParams({
    search_query: query,
    page: page.toString(),
    limit: '8'
  });

  const response = await fetch(`/api/duplicatebill/search?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to search invoices');
  }

  return response.json();
};
```

**Example** - Generate duplicate:
```typescript
const generateDuplicate = async (invoiceId: string, type: 'walkin' | 'customer') => {
  const response = await fetch(`/api/duplicatebill/${invoiceId}/duplicate?invoice_type=${type}`, {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to generate duplicate');
  }

  const data = await response.json();
  return data.pdf; // Base64 PDF
};
```

---

## Error Codes

| HTTP Status | Meaning | Common Causes |
|-------------|---------|---------------|
| 200 | OK | Success |
| 400 | Bad Request | Invalid invoice ID format, invalid invoice type |
| 401 | Unauthorized | Not logged in, invalid session |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Invoice not found |
| 500 | Server Error | Database error, server issue |

---

## Testing Checklist

### Login First
- [ ] Login with admin/cashier credentials
- [ ] Save cookies (`-c cookies.txt`)

### Test Search
- [ ] Search by invoice number (CIN-0007)
- [ ] Search by customer name
- [ ] Get last 24 hours (no search query)
- [ ] Test pagination
- [ ] Verify both walk-in and customer invoices returned

### Test Duplicate Generation
- [ ] Generate duplicate for walk-in invoice
- [ ] Generate duplicate for customer invoice
- [ ] Verify PDF is base64 encoded
- [ ] Test cache (second request should be faster)
- [ ] Try invalid invoice ID (should 400)
- [ ] Try non-existent invoice (should 404)

---

## Invoice Types

### Walk-in Invoice (SIN- prefix)
- Invoice number format: `SIN-0001`, `SIN-0002`, etc.
- Created for walk-in customers
- Full payment at time of purchase
- Fields: `invoice_no`, `customer_name`, `items`, `total_amount`, `payment_method`

### Customer Invoice (CIN- prefix)
- Invoice number format: `CIN-0001`, `CIN-0002`, etc.
- Created for credit customers
- Partial payments allowed
- Fields: `invoice_no`, `customer_name`, `team_name`, `items`, `total_amount`, `balance_due`, `payments_history`

---

## Related Documentation

- [Walk-in Invoice API](walkin-invoice-api.md) - Walk-in invoice management
- [Customer Invoice API](customer-invoice-api.md) - Customer invoice management
- [Authentication](authentication_api.md) - Login and session management
