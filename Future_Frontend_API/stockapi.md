# Stock Management API

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
| `admin_cashier_employee_required_from_session()` | `admin`, `cashier`, `employee` | All stock endpoints |

**Important Notes**:

All stock endpoints are accessible by **admin, cashier, and employee** roles.

---

## API Endpoints

### Stock Management

---

### 1. GET /stock/viewstock - View Stock (Paginated)

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get paginated list of stock items with search and branch filtering. Shows only products with stock > 0. This is the **main endpoint** used by the frontend.

**Endpoint**: `GET /stock/viewstock?page=1&limit=8&search_string=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (1-based) |
| `limit` | int | 8 | Items per page |
| `search_string` | string | - | Search by product name, barcode, or SKU |
| `branches` | string | - | Filter by branch name |
| `shelf` | string | - | Filter by shelf (optional) |

**Example**:
```bash
curl -X GET "http://localhost:8000/stock/viewstock?page=1&limit=8&search_string=Nike" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "data": [
    {
      "pro_id": "uuid-string",
      "vendor_name": "Ali Traders",
      "product_name": "Nike Air Max",
      "category": "Shoes",
      "stock": 50,
      "price": 99.99,
      "cost": 79.99,
      "barcode": "1234567890123",
      "margin": 25.0,
      "brand": "Nike",
      "branch": "European Sports Light House"
    }
  ],
  "page": 1,
  "limit": 8,
  "total": 150,
  "total_pages": 19,
  "has_more": true
}
```

**Response Fields**:
- `data`: Array of stock items (max 8 per page)
- `vendor_name`: Latest vendor from stock entries
- `product_name`: Product name
- `category`: Product category
- `stock`: Current stock level
- `price`: Selling price
- `cost`: Cost price
- `barcode`: Product barcode
- `margin`: Profit margin percentage `((price - cost) / price * 100)`
- `brand`: Brand name
- `branch`: Branch location

**Important**: Only returns products with `stock_level > 0`.

**Error** (401 Unauthorized):
```json
{
  "detail": "Not authenticated"
}
```

---

### 2. GET /stock/searchstock - Search Stock

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Search stock by branch and search term. Returns all matching products (no pagination).

**Endpoint**: `GET /stock/searchstock?branches=&search_string=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `branches` | string | - | Filter by branch name |
| `search_string` | string | - | Search by product name |

**Example**:
```bash
curl -X GET "http://localhost:8000/stock/searchstock?branches=Light%20House&search_string=Nike" \
  -b cookies.txt
```

**Response** (200 OK):
```json
[
  {
    "stock_id": "uuid-string",
    "product_name": "Nike Air Max",
    "stock": 50,
    "branch": "European Sports Light House"
  }
]
```

---

### 3. POST /stock/adjuststock - Adjust Stock

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Adjust stock levels for multiple products (increase or decrease). Creates stock entry with type ADJUST.

**Endpoint**: `POST /stock/adjuststock`

**Request Body**:
```json
[
  {
    "product_id": "uuid-string",
    "quantity": 5,
    "action": "increase",
    "reason": "Stock count adjustment"
  },
  {
    "product_id": "uuid-string-2",
    "quantity": 3,
    "action": "decrease",
    "reason": "Damaged goods"
  }
]
```

**Request Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `product_id` | string | ✅ Yes | Product UUID |
| `quantity` | int | ✅ Yes | Quantity to adjust |
| `action` | string | ✅ Yes | `increase` or `decrease` |
| `reason` | string | ❌ No | Reason for adjustment |

**Example**:
```bash
curl -X POST "http://localhost:8000/stock/adjuststock" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '[
    {
      "product_id": "uuid-string",
      "quantity": 5,
      "action": "increase",
      "reason": "Stock count adjustment"
    }
  ]'
```

**Response** (200 OK):
```json
{
  "message": "Stock adjustment completed successfully",
  "results": [
    {
      "product_id": "uuid-string",
      "product_name": "Nike Air Max",
      "action": "increase",
      "quantity_adjusted": 5,
      "old_stock": 50,
      "new_stock": 55,
      "status": "success"
    }
  ]
}
```

**Important**: Stock cannot go below 0. If decrease would result in negative stock, it's set to 0.

---

### 4. POST /stock/savestockin - Save Stock In

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Save stock in transactions for multiple products. Creates stock entry with type IN.

**Endpoint**: `POST /stock/savestockin`

**Request Body**:
```json
[
  {
    "product_id": "uuid-string",
    "vendor_id": "uuid-string",
    "quantity": 50,
    "cost_price": 79.99,
    "date": "2026-03-10"
  }
]
```

**Request Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `product_id` | string | ✅ Yes | Product UUID |
| `vendor_id` | string | ✅ Yes | Vendor UUID |
| `quantity` | int | ✅ Yes | Quantity to add |
| `cost_price` | number | ❌ No | Cost price per unit |
| `date` | string | ❌ No | Date of stock in (YYYY-MM-DD) |

**Example**:
```bash
curl -X POST "http://localhost:8000/stock/savestockin" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '[
    {
      "product_id": "uuid-string",
      "vendor_id": "uuid-string",
      "quantity": 50,
      "cost_price": 79.99
    }
  ]'
```

**Response** (200 OK):
```json
{
  "message": "Stock in completed successfully",
  "results": [
    {
      "product_id": "uuid-string",
      "product_name": "Nike Air Max",
      "quantity_added": 50,
      "new_stock_level": 100,
      "vendor_id": "uuid-string",
      "status": "success"
    }
  ]
}
```

---

### 5. POST /stock/savestockinwithbarcode - Save Stock In with Barcodes

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Save stock in transactions AND generate ZPL barcode commands for printing.

**Endpoint**: `POST /stock/savestockinwithbarcode`

**Request Body**:
```json
[
  {
    "product_id": "uuid-string",
    "vendor_id": "uuid-string",
    "quantity": 50,
    "cost_price": 79.99,
    "selling_price": 99.99,
    "date": "2026-03-10"
  }
]
```

**Request Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `product_id` | string | ✅ Yes | Product UUID |
| `vendor_id` | string | ✅ Yes | Vendor UUID |
| `quantity` | int | ✅ Yes | Quantity to add |
| `cost_price` | number | ❌ No | Cost price per unit |
| `selling_price` | number | ❌ No | Selling price for barcode |
| `date` | string | ❌ No | Date of stock in (YYYY-MM-DD) |

**Example**:
```bash
curl -X POST "http://localhost:8000/stock/savestockinwithbarcode" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '[
    {
      "product_id": "uuid-string",
      "vendor_id": "uuid-string",
      "quantity": 50,
      "selling_price": 99.99
    }
  ]'
```

**Response** (200 OK):
```json
{
  "message": "Stock in completed successfully with barcodes",
  "results": [
    {
      "product_id": "uuid-string",
      "product_name": "Nike Air Max",
      "quantity_added": 50,
      "new_stock_level": 100,
      "vendor_id": "uuid-string",
      "status": "success"
    }
  ],
  "zpl_commands": [
    {
      "product_id": "uuid-string",
      "product_name": "Nike Air Max",
      "barcode": "1234567890123",
      "quantity": 50,
      "unit_index": 1,
      "price": 99.99,
      "zpl": "^XA^FO160,50^BY2,3,80^BCN,80,Y,N,N^FD1234567890123^FS..."
    }
  ]
}
```

**ZPL Commands**: One ZPL command per unit for barcode printing (Zebra GX420d compatible).

---

### 6. POST /stock/stockreport - Stock Report (PDF)

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Generate stock report in PDF format (base64 encoded). Shows only products with stock > 0.

**Endpoint**: `POST /stock/stockreport`

**Query Parameters** (optional):
| Parameter | Type | Description |
|-----------|------|-------------|
| `cat_name` | string | Filter by category |
| `pro_name` | string | Filter by product name |
| `branches` | string | Filter by branch |
| `ven_name` | string | Filter by vendor name |
| `timezone` | string | Timezone for report |

**Example**:
```bash
curl -X POST "http://localhost:8000/stock/stockreport" \
  -b cookies.txt
```

**Response** (200 OK):
```
Base64 encoded PDF string
```

**Report Contents**:
- Product name
- Category
- Stock level
- Price
- Cost
- Margin %
- Barcode
- Brand
- Branch
- Total product count

---

### 7. POST /stock/stockinreport - Stock In Report (PDF)

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Generate date-wise stock-in report (PDF base64). Shows quantity added per product within date range.

**Endpoint**: `POST /stock/stockinreport?date_from=&date_to=`

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `date_from` | string | ✅ Yes | Start date (YYYY-MM-DD) |
| `date_to` | string | ✅ Yes | End date (YYYY-MM-DD) |

**Example**:
```bash
curl -X POST "http://localhost:8000/stock/stockinreport?date_from=2026-03-01&date_to=2026-03-10" \
  -b cookies.txt
```

**Response** (200 OK):
```
Base64 encoded PDF string
```

**Report Contents**:
- Product name
- Barcode
- Total quantity received in date range
- First entry date
- Date range covered

---

### 8. GET /stock/generatebarcodesonly - Generate Barcodes

**Access**: `employee_required_from_session()` - **Employee, Cashier, Admin**

**Description**: Generate ZPL barcode commands for existing products.

**Endpoint**: `GET /stock/generatebarcodesonly`

**Example**:
```bash
curl -X GET "http://localhost:8000/stock/generatebarcodesonly" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "zpl_commands": [
    {
      "product_id": "uuid-string",
      "product_name": "Nike Air Max",
      "barcode": "1234567890123",
      "zpl": "^XA^FO160,50^BY2,3,80^BCN,80,Y,N,N^FD1234567890123^FS..."
    }
  ]
}
```

---

## Frontend API Routes

The frontend uses Next.js API routes as proxies:

| Frontend Route | Backend Endpoint |
|----------------|------------------|
| `GET /api/stock/viewstock` | `GET /stock/viewstock` |
| `GET /api/stock/searchstock` | `GET /stock/searchstock` |
| `POST /api/stock/adjuststock` | `POST /stock/adjuststock` |
| `POST /api/stock/savestockin` | `POST /stock/savestockin` |
| `POST /api/stock/savestockinwithbarcode` | `POST /stock/savestockinwithbarcode` |
| `POST /api/stock/stockreport` | `POST /stock/stockreport` |
| `POST /api/stock/stockinreport` | `POST /stock/stockinreport` |
| `GET /api/stock/generatebarcodesonly` | `GET /stock/generatebarcodesonly` |

**Example** - Frontend fetch with pagination:
```typescript
const fetchStock = async (page: number = 1, searchTerm: string = '') => {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: '8',
    search_string: searchTerm
  });

  const response = await fetch(`/api/stock/viewstock?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch stock');
  }

  return response.json();
};
```

---

## Error Codes

| HTTP Status | Meaning | Common Causes |
|-------------|---------|---------------|
| 200 | OK | Success |
| 400 | Bad Request | Invalid input, invalid date format, invalid action |
| 401 | Unauthorized | Not logged in, invalid session |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Product not found, vendor not found |
| 500 | Server Error | Database error, server issue |

---

## Testing Checklist

### Login First
- [ ] Login with admin credentials
- [ ] Save cookies (`-c cookies.txt`)

### Test GET /stock/viewstock
- [ ] Fetch first page (page=1, limit=8)
- [ ] Fetch with search term
- [ ] Fetch with branch filter
- [ ] Verify only products with stock > 0 are returned
- [ ] Verify pagination response format

### Test POST /stock/adjuststock
- [ ] Increase stock for product
- [ ] Decrease stock for product
- [ ] Try invalid action (should fail)
- [ ] Try decrease below 0 (should set to 0)

### Test POST /stock/savestockin
- [ ] Add stock with vendor
- [ ] Add stock without cost price
- [ ] Try non-existent product (should fail)
- [ ] Try non-existent vendor (should fail)

### Test POST /stock/savestockinwithbarcode
- [ ] Add stock with barcode generation
- [ ] Verify ZPL commands in response
- [ ] Test with product without barcode

### Test Reports
- [ ] Generate stock report (PDF)
- [ ] Generate stock-in report with date range
- [ ] Generate barcodes only

---

## Stock Data Models

### Stock Entry Types:
```python
class StockEntryType(str, Enum):
    IN = "IN"        # Stock received from vendor
    OUT = "OUT"      # Stock sold/removed
    ADJUST = "ADJUST" # Stock adjustment
```

### Stock Entry Schema:
```python
class StockEntry(SQLModel, table=True):
    __tablename__ = "stock_entries"
    
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    product_id: UUID = Field(foreign_key="products.id")
    vendor_id: Optional[UUID] = Field(foreign_key="vendors.id", default=None)
    qty: int
    cost_price: Optional[Decimal] = Field(default=None)
    type: StockEntryType
    location: Optional[str] = Field(default=None)
    ref: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

### Stock Adjust Request:
```json
{
  "product_id": "uuid-string",
  "quantity": 5,
  "action": "increase",
  "reason": "Stock count adjustment"
}
```

### Stock In Request:
```json
{
  "product_id": "uuid-string",
  "vendor_id": "uuid-string",
  "quantity": 50,
  "cost_price": 79.99,
  "date": "2026-03-10"
}
```

---

## Margin Calculation

Margin percentage is calculated as:

```
Margin % = ((Selling Price - Cost Price) / Selling Price) × 100
```

**Example**:
- Selling Price: Rs. 100
- Cost Price: Rs. 80
- Margin: ((100 - 80) / 100) × 100 = 20%

---

## Related Documentation

- [Authentication](authentication_api.md) - Login and session management
- [User Management](administrative_api.md) - User CRUD operations
- [Product API](productapi.md) - Product management
- [Vendor API](vendorapi.md) - Vendor management
- [Stock Adjustment](stock_adjustment.md) - Stock adjustment workflow
