# Dashboard API

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
| `admin_cashier_employee_required_from_session()` | `admin`, `cashier`, `employee` | All dashboard endpoints |

**Important Notes**:

All dashboard endpoints are accessible by **admin, cashier, and employee** roles.

---

## API Endpoints

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

**Important Date Logic**:
- **Current month**: Shows data only up to **today's date** (not future dates)
- **Past months**: Shows data for **full month**
- **Future months**: Shows data for **full month** (if any exists)

**Example** - Current month:
```bash
curl -X GET "http://localhost:8000/salesview/dashboard/stats?month=3&year=2026" \
  -b cookies.txt
```

**Example** - Past month:
```bash
curl -X GET "http://localhost:8000/salesview/dashboard/stats?month=2&year=2026" \
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
    },
    {
      "date": "2026-03-02",
      "sales": 18000.00,
      "expenses": 2000.00,
      "purchases": 7000.00
    }
  ],
  "payment_method_breakdown": {
    "cash": 300000.00,
    "easypaisa_zohaib": 100000.00,
    "easypaisa_yasir": 50000.00,
    "bank": 50000.00
  },
  "daily_cash_summary": {
    "opening": 50000.00,
    "closing": 120000.00,
    "expected": 125000.00,
    "difference": -5000.00
  }
}
```

**Response Fields**:

| Field | Type | Description |
|-------|------|-------------|
| `month` | int | Requested month |
| `year` | int | Requested year |
| `total_sales` | number | Total sales (walk-in + customer payments) |
| `total_expenses` | number | Total expenses for the month |
| `total_purchases` | number | Total purchases/stock-in |
| `gross_profit` | number | Sales - Cost of Goods Sold |
| `net_profit` | number | Gross Profit - Expenses |
| `total_stock_value` | number | Current stock value at cost |
| `daily_chart_data` | array | Daily breakdown for charts |
| `payment_method_breakdown` | object | Sales by payment method |
| `daily_cash_summary` | object | Opening/closing cash summary |

**Daily Chart Data Fields**:
```json
{
  "date": "2026-03-01",
  "sales": 15000.00,
  "expenses": 1500.00,
  "purchases": 6000.00
}
```

**Payment Method Breakdown**:
- `cash`: Cash payments
- `easypaisa_zohaib`: Easypaisa (Zohaib account)
- `easypaisa_yasir`: Easypaisa (Yasir account)
- `bank`: Bank transfers

---

## Calculation Logic

### Total Sales Calculation

**Walk-in Sales** (SIN- prefix):
```sql
SELECT SUM(amount_paid) 
FROM invoices 
WHERE invoice_no LIKE 'SIN-%' 
AND payment_date BETWEEN first_day AND last_day
```

**Customer Payments** (CIN- prefix):
- Iterates through all customer invoices
- Sums payments from `payments_history` JSON array
- Only counts payments made within the date range

**Formula**:
```
Total Sales = Walk-in Sales + Customer Payments in Month
```

### Gross Profit Calculation

```
Gross Profit = Total Sales - Cost of Goods Sold
```

Where:
- Cost of Goods Sold = Sum of (quantity × cost_price) for all sold items

### Net Profit Calculation

```
Net Profit = Gross Profit - Total Expenses
```

### Daily Chart Data

- Shows data for each day of the month
- For current month: Only shows data up to **today**
- For past months: Shows data for **all days** in month
- Includes sales, expenses, and purchases for each day

---

## Frontend API Routes

| Frontend Route | Backend Endpoint |
|----------------|------------------|
| `GET /api/dashboard/stats` | `GET /salesview/dashboard/stats` |

**Example** - Frontend fetch:
```typescript
const fetchDashboardData = async (month: number, year: number) => {
  const params = new URLSearchParams({
    month: month.toString(),
    year: year.toString()
  });

  const response = await fetch(`/api/dashboard/stats?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch dashboard data');
  }

  return response.json();
};

// Usage
const today = new Date();
const data = await fetchDashboardData(
  today.getMonth() + 1,
  today.getFullYear()
);
```

---

## Error Codes

| HTTP Status | Meaning | Common Causes |
|-------------|---------|---------------|
| 200 | OK | Success |
| 400 | Bad Request | Invalid month (not 1-12), invalid year |
| 401 | Unauthorized | Not logged in, invalid session |
| 403 | Forbidden | Insufficient permissions |
| 500 | Server Error | Database error, server issue |

---

## Testing Checklist

### Login First
- [ ] Login with admin credentials
- [ ] Save cookies (`-c cookies.txt`)

### Test Dashboard Stats
- [ ] Fetch current month data
- [ ] Fetch past month data
- [ ] Verify daily chart data only shows up to today for current month
- [ ] Verify payment method breakdown adds up to total sales
- [ ] Verify gross profit calculation
- [ ] Verify net profit calculation

### Test Edge Cases
- [ ] Invalid month (13) - should 400
- [ ] Invalid month (0) - should 400
- [ ] Future month - should return data if exists
- [ ] Month with no data - should return zeros

---

## Related Documentation

- [Sales View API](salesview-api.md) - Sales reports and analytics
- [Authentication](authentication_api.md) - Login and session management
- [User Management](administrative_api.md) - User roles and permissions
