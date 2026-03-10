# Sales View API

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
| `admin_cashier_employee_required_from_session()` | `admin`, `cashier`, `employee` | All sales view endpoints |

**Important Notes**:

All sales view endpoints are accessible by **admin, cashier, and employee** roles.

---

## API Endpoints

### Sales Reports

---

### 1. GET /salesview/dashboard/stats - Dashboard Statistics

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get comprehensive dashboard statistics for a specific month including sales, expenses, purchases, stock data, and daily chart data.

**Endpoint**: `GET /salesview/dashboard/stats?month=&year=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `month` | int | current | Month number (1-12) |
| `year` | int | current | Year number (e.g., 2026) |

**Important**: 
- For current month: Shows data only up to **today's date**
- For past/future months: Shows data for **full month**

**Example**:
```bash
curl -X GET "http://localhost:8000/salesview/dashboard/stats?month=3&year=2026" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "month": 3,
  "year": 2026,
  "total_sales": 500000.00,
  "total_expenses": 50000.00,
  "total_purchases": 200000.00,
  "gross_profit": 300000.00,
  "net_profit": 250000.00,
  "total_stock_value": 150000.00,
  "daily_chart_data": [
    {
      "date": "2026-03-01",
      "sales": 15000.00,
      "expenses": 1500.00,
      "purchases": 6000.00
    }
  ],
  "payment_method_breakdown": {
    "cash": 300000.00,
    "easypaisa_zohaib": 100000.00,
    "easypaisa_yasir": 50000.00,
    "bank": 50000.00
  }
}
```

---

### 2. GET /salesview/walkin-invoices - Walk-in Invoice Report

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get walk-in invoices for date range with branch filter.

**Endpoint**: `GET /salesview/walkin-invoices?from_date=&to_date=&branch=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from_date` | string | ✅ Yes | Start date (YYYY-MM-DD) |
| `to_date` | string | ✅ Yes | End date (YYYY-MM-DD) |
| `branch` | string | ❌ No | Filter by branch name |

**Example**:
```bash
curl -X GET "http://localhost:8000/salesview/walkin-invoices?from_date=2026-03-01&to_date=2026-03-10&branch=European%20Sports%20Light%20House" \
  -b cookies.txt
```

**Response** (200 OK):
```json
[
  {
    "id": "uuid-string",
    "invoice_no": "SIN-001",
    "product_name": "Nike Air Max",
    "total_amount": 99.99,
    "amount_paid": 99.99,
    "balance_due": 0.00,
    "payment_status": "paid",
    "payment_method": "cash",
    "quantity": 2,
    "discount": 5.00,
    "total_discount": 10.00,
    "cost": 150.00,
    "created_at": "2026-03-05T10:00:00"
  }
]
```

---

### 3. GET /salesview/walkin-invoices/pdf - Walk-in Invoice PDF Report

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Generate PDF report for walk-in invoices in date range.

**Endpoint**: `GET /salesview/walkin-invoices/pdf?from_date=&to_date=&branch=`

**Query Parameters**: Same as #2

**Example**:
```bash
curl -X GET "http://localhost:8000/salesview/walkin-invoices/pdf?from_date=2026-03-01&to_date=2026-03-10" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "pdf": "base64-encoded-pdf-string"
}
```

---

### 4. GET /salesview/walkin-invoices/excel - Walk-in Invoice Excel Report

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Generate Excel report for walk-in invoices in date range.

**Endpoint**: `GET /salesview/walkin-invoices/excel?from_date=&to_date=&branch=`

**Query Parameters**: Same as #2

**Example**:
```bash
curl -X GET "http://localhost:8000/salesview/walkin-invoices/excel?from_date=2026-03-01&to_date=2026-03-10" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "filename": "walkin_invoices_2026-03-01_to_2026-03-10.xlsx",
  "file": "base64-encoded-excel-string"
}
```

---

### 5. GET /salesview/customized-invoices - Customer Invoice Report

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get customer invoices with payment details for date range (cash basis - payment-wise).

**Endpoint**: `GET /salesview/customized-invoices?from_date=&to_date=&branch=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from_date` | string | ✅ Yes | Start date (YYYY-MM-DD) |
| `to_date` | string | ✅ Yes | End date (YYYY-MM-DD) |
| `branch` | string | ❌ No | Filter by branch name |

**Example**:
```bash
curl -X GET "http://localhost:8000/salesview/customized-invoices?from_date=2026-03-01&to_date=2026-03-10" \
  -b cookies.txt
```

**Response** (200 OK):
```json
[
  {
    "id": "uuid-string",
    "invoice_no": "CIN-001",
    "customer_name": "John Doe",
    "team_name": "Team A",
    "total_amount": 5000.00,
    "payment_in_selected_range": 2000.00,
    "total_paid": 4000.00,
    "pending": 1000.00,
    "payment_status": "partial",
    "payment_methods_used": ["cash", "easypaisa"],
    "quantity": 10,
    "invoice_created_at": "2026-03-01T10:00:00",
    "payment_time": "14:30:00",
    "payments_in_range": [
      {
        "date": "2026-03-05",
        "amount": 2000.00,
        "method": "cash",
        "description": "Partial payment"
      }
    ]
  }
]
```

**Important**: Shows payments made in selected date range, not invoice creation date.

---

### 6. GET /salesview/customized-invoices/pdf - Customer Invoice PDF Report

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Generate PDF report for customer invoices in date range.

**Endpoint**: `GET /salesview/customized-invoices/pdf?from_date=&to_date=&branch=`

**Example**:
```bash
curl -X GET "http://localhost:8000/salesview/customized-invoices/pdf?from_date=2026-03-01&to_date=2026-03-10" \
  -b cookies.txt
```

**Response**: Base64-encoded PDF string.

---

### 7. GET /salesview/customized-invoices/excel - Customer Invoice Excel Report

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Generate Excel report for customer invoices in date range.

**Endpoint**: `GET /salesview/customized-invoices/excel?from_date=&to_date=&branch=`

**Example**:
```bash
curl -X GET "http://localhost:8000/salesview/customized-invoices/excel?from_date=2026-03-01&to_date=2026-03-10" \
  -b cookies.txt
```

**Response**: Base64-encoded Excel string with filename.

---

### 8. GET /salesview/customized-summary - Payment Method Summary

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get summary of collections by payment method for date range.

**Endpoint**: `GET /salesview/customized-summary?from_date=&to_date=&branch=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from_date` | string | ✅ Yes | Start date (YYYY-MM-DD) |
| `to_date` | string | ✅ Yes | End date (YYYY-MM-DD) |
| `branch` | string | ❌ No | Filter by branch name |

**Example**:
```bash
curl -X GET "http://localhost:8000/salesview/customized-summary?from_date=2026-03-01&to_date=2026-03-10" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "total_collection": 100000.00,
  "cash": 60000.00,
  "easypaisa_zohaib": 20000.00,
  "easypaisa_yasir": 10000.00,
  "bank": 10000.00,
  "invoices_count": 25
}
```

---

### 9. GET /salesview/summary - Overall Sales Summary

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get overall sales summary including opening, sales, expenses, recoveries, etc.

**Endpoint**: `GET /salesview/summary?from_date=&to_date=&branch=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from_date` | string | ✅ Yes | Start date (YYYY-MM-DD) |
| `to_date` | string | ✅ Yes | End date (YYYY-MM-DD) |
| `branch` | string | ❌ No | Filter by branch name |

**Example**:
```bash
curl -X GET "http://localhost:8000/salesview/summary?from_date=2026-03-01&to_date=2026-03-10" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "opening": 50000.00,
  "totalSale": 200000.00,
  "grossProfit": 120000.00,
  "totalExpense": 30000.00,
  "totalRecovery": 180000.00,
  "vendorPayments": 100000.00,
  "netCash": 170000.00,
  "totalPurchase": 150000.00,
  "totalRefund": 5000.00,
  "netProfit": 85000.00,
  "walkin_sales": 100000.00,
  "customer_payments": 100000.00
}
```

---

### 10-15. PDF/Excel Reports for Other Types

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

| Endpoint | Description |
|----------|-------------|
| `GET /salesview/expenses/pdf` | PDF report for expenses |
| `GET /salesview/expenses/excel` | Excel report for expenses |
| `GET /salesview/stock-adjustments/pdf` | PDF report for stock adjustments |
| `GET /salesview/stock-adjustments/excel` | Excel report for stock adjustments |
| `GET /salesview/refunds/pdf` | PDF report for refunds |
| `GET /salesview/refunds/excel` | Excel report for refunds |

All use same query parameters: `from_date`, `to_date`, `branch`

---

## Frontend API Routes

| Frontend Route | Backend Endpoint |
|----------------|------------------|
| `GET /api/dashboard/stats` | `GET /salesview/dashboard/stats` |
| `GET /api/salesview/walkin-invoices` | `GET /salesview/walkin-invoices` |
| `GET /api/salesview/customized-invoices` | `GET /salesview/customized-invoices` |
| `GET /api/salesview/customized-summary` | `GET /salesview/customized-summary` |
| `GET /api/salesview/summary` | `GET /salesview/summary` |

---

## Error Codes

| HTTP Status | Meaning | Common Causes |
|-------------|---------|---------------|
| 200 | OK | Success |
| 400 | Bad Request | Invalid date format, invalid month |
| 401 | Unauthorized | Not logged in, invalid session |
| 403 | Forbidden | Insufficient permissions |
| 500 | Server Error | Database error, server issue |

---

## Related Documentation

- [Dashboard API](dashboard_api.md) - Dashboard statistics
- [Walk-in Invoice API](walkin-invoice-api.md) - Walk-in invoice management
- [Customer Invoice API](customer-invoice-api.md) - Customer invoice management
