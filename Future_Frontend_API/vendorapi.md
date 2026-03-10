# Vendor Management API

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
| `admin_cashier_employee_required_from_session()` | `admin`, `cashier`, `employee` | GET /viewvendor |
| `admin_required_from_session()` | `admin` only | POST, PUT, DELETE operations |

**Important Notes**:

1. **GET /vendors/viewvendor** - Requires **any authenticated user** (admin, cashier, employee)
   - All authenticated users can view vendors

2. **POST /vendors/** - Requires **admin** only
   - Only admins can create vendors

3. **PUT /vendors/{id}** - Requires **admin** only
   - Only admins can update vendors

4. **POST /vendors/deletevendor/{id}** - Requires **admin** only
   - Only admins can delete vendors

---

## API Endpoints

### Vendor CRUD Operations

---

### 1. GET /vendors/viewvendor - View Vendors (Paginated)

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get paginated list of vendors with search and branch filtering. This is the **main endpoint** used by the frontend.

**Endpoint**: `GET /vendors/viewvendor?page=1&limit=8&search_string=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (1-based) |
| `limit` | int | 8 | Items per page |
| `search_string` | string | - | Search by vendor name |
| `branches` | string | - | Filter by branch name |
| `searchphone` | string | - | Search by phone (optional) |
| `searchaddress` | string | - | Search by address (optional) |

**Example**:
```bash
curl -X GET "http://localhost:8000/vendors/viewvendor?page=1&limit=8&search_string=Ali" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "data": [
    {
      "ven_id": "uuid-string",
      "ven_name": "Ali Traders",
      "ven_phone": "03001234567",
      "ven_address": "123 Market Street",
      "branch": "European Sports Light House",
      "vend_balance": 0.00
    }
  ],
  "page": 1,
  "limit": 8,
  "total": 25,
  "totalPages": 4
}
```

**Response Fields**:
- `data`: Array of vendors (max 8 per page)
- `page`: Current page number
- `limit`: Items per page
- `total`: Total number of vendors matching search
- `totalPages`: Total pages (for pagination UI)

**Error** (401 Unauthorized):
```json
{
  "detail": "Not authenticated"
}
```

---

### 2. POST /vendors/ - Create Vendor

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Create a new vendor.

**Endpoint**: `POST /vendors/`

**Request Body**:
```json
{
  "name": "Ali Traders",
  "contacts": "{\"phone\": \"03001234567\", \"email\": \"\", \"address\": \"123 Market Street\"}",
  "branch": "European Sports Light House"
}
```

**Request Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ Yes | Vendor name |
| `contacts` | string | ✅ Yes | JSON string with phone, email, address |
| `branch` | string | ❌ No | Branch name |
| `terms` | string | ❌ No | JSON string for payment terms (optional) |

**Example**:
```bash
curl -X POST "http://localhost:8000/vendors/" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "Ali Traders",
    "contacts": "{\"phone\": \"03001234567\", \"email\": \"\", \"address\": \"123 Market Street\"}",
    "branch": "European Sports Light House"
  }'
```

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "name": "Ali Traders",
  "contacts": "{\"phone\": \"03001234567\", \"email\": \"\", \"address\": \"123 Market Street\"}",
  "branch": "European Sports Light House",
  "terms": "{}",
  "created_at": "2026-03-10T10:00:00",
  "updated_at": "2026-03-10T10:00:00"
}
```

**Errors**:

**400 Bad Request** - Invalid JSON:
```json
{
  "detail": "Invalid contacts format"
}
```

---

### 3. PUT /vendors/{vendor_id} - Update Vendor

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Update an existing vendor.

**Endpoint**: `PUT /vendors/{vendor_id}`

**Path Parameter**: `vendor_id` - UUID of the vendor

**Request Body** (all fields optional):
```json
{
  "name": "Updated Vendor Name",
  "contacts": "{\"phone\": \"03009876543\", \"email\": \"new@email.com\", \"address\": \"456 New Street\"}",
  "branch": "Updated Branch",
  "terms": "{\"payment_days\": 30}"
}
```

**Example**:
```bash
curl -X PUT "http://localhost:8000/vendors/uuid-string" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "Updated Vendor Name",
    "contacts": "{\"phone\": \"03009876543\", \"address\": \"456 New Street\"}"
  }'
```

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "name": "Updated Vendor Name",
  "contacts": "{\"phone\": \"03009876543\", \"email\": \"\", \"address\": \"456 New Street\"}",
  "branch": "Updated Branch",
  "terms": "{}",
  "updated_at": "2026-03-10T11:00:00"
}
```

**Errors**:

**404 Not Found**:
```json
{
  "detail": "Vendor not found"
}
```

---

### 4. POST /vendors/deletevendor/{id} - Delete Vendor

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Delete a vendor by ID (frontend-compatible endpoint).

**Endpoint**: `POST /vendors/deletevendor/{id}`

**Path Parameter**: `id` - UUID of the vendor

**Important**: Only admins can delete vendors.

**Example**:
```bash
curl -X POST "http://localhost:8000/vendors/deletevendor/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Vendor deleted successfully"
}
```

**Errors**:

**404 Not Found**:
```json
{
  "detail": "Vendor not found"
}
```

---

### 5. GET /vendors/getvendor/{id} - Get Vendor Details

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Get specific vendor details by ID.

**Endpoint**: `GET /vendors/getvendor/{id}`

**Path Parameter**: `id` - UUID of the vendor

**Example**:
```bash
curl -X GET "http://localhost:8000/vendors/getvendor/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "ven_id": "uuid-string",
  "ven_name": "Ali Traders",
  "ven_phone": "03001234567",
  "ven_address": "123 Market Street",
  "branch": "European Sports Light House"
}
```

---

### 6. POST /vendors/getvendorbalance - Get Vendor Balance

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Get vendor balance by branch (placeholder for future implementation).

**Endpoint**: `POST /vendors/getvendorbalance`

**Request Body** (optional):
```json
{
  "branches": "European Sports Light House"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/vendors/getvendorbalance" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "branches": "European Sports Light House"
  }'
```

**Response** (200 OK):
```json
{
  "cus_balance": 5000.00
}
```

**Note**: Currently returns placeholder value. Actual balance calculation to be implemented.

---

### 7. POST /vendors/vendorviewreport - Vendor Report

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Generate vendor details report (PDF, used by ReportModal).

**Endpoint**: `POST /vendors/vendorviewreport`

**Example**:
```bash
curl -X POST "http://localhost:8000/vendors/vendorviewreport" \
  -b cookies.txt
```

**Response** (200 OK):
```
Base64 encoded PDF string
```

**Report Contents**:
- Vendor name
- Phone number
- Address
- Branch
- Balance (currently 0, to be implemented)
- Total market balance

---

## Frontend API Routes

The frontend uses Next.js API routes as proxies:

| Frontend Route | Backend Endpoint |
|----------------|------------------|
| `GET /api/admin/viewvendor` | `GET /vendors/viewvendor` |
| `POST /api/vendors/` | `POST /vendors/` |
| `PUT /api/vendors/{id}` | `PUT /vendors/{id}` |
| `POST /api/admin/deletevendor/{id}` | `POST /vendors/deletevendor/{id}` |
| `GET /api/vendors/getvendor/{id}` | `GET /vendors/getvendor/{id}` |
| `POST /api/vendors/getvendorbalance` | `POST /vendors/getvendorbalance` |
| `POST /api/vendors/vendorviewreport` | `POST /vendors/vendorviewreport` |

**Example** - Frontend fetch with pagination:
```typescript
const fetchVendors = async (page: number = 1, searchTerm: string = '') => {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: '8',
    search_string: searchTerm
  });

  const response = await fetch(`/api/admin/viewvendor?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch vendors');
  }

  return response.json();
};
```

---

## Error Codes

| HTTP Status | Meaning | Common Causes |
|-------------|---------|---------------|
| 200 | OK | Success |
| 400 | Bad Request | Invalid input, invalid JSON format |
| 401 | Unauthorized | Not logged in, invalid session |
| 403 | Forbidden | Insufficient permissions (not admin) |
| 404 | Not Found | Vendor not found |
| 500 | Server Error | Database error, server issue |

---

## Testing Checklist

### Login First
- [ ] Login with admin credentials
- [ ] Save cookies (`-c cookies.txt`)

### Test GET /vendors/viewvendor
- [ ] Fetch first page (page=1, limit=8)
- [ ] Fetch with search term
- [ ] Fetch with branch filter
- [ ] Verify pagination response format

### Test POST /vendors/
- [ ] Create new vendor with all fields
- [ ] Create vendor without branch (optional)
- [ ] Try invalid contacts JSON (should fail)

### Test PUT /vendors/{id}
- [ ] Update vendor name
- [ ] Update vendor phone
- [ ] Update vendor branch
- [ ] Try update as non-admin (should fail with 403)

### Test POST /vendors/deletevendor/{id}
- [ ] Delete vendor (admin only)
- [ ] Try delete as non-admin (should fail with 403)
- [ ] Try delete non-existent vendor (should 404)

### Test Other Endpoints
- [ ] Get vendor details by ID
- [ ] Get vendor balance (placeholder)
- [ ] Generate vendor report (PDF)

---

## Vendor Data Model

### Database Schema:
```python
class Vendor(SQLModel, table=True):
    __tablename__ = "vendors"
    
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    contacts: str = Field()  # JSON: {phone, email, address}
    branch: Optional[str] = Field(default=None, max_length=200)
    terms: Optional[str] = Field(default="{}")  # JSON: payment terms
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

### Contacts JSON Format:
```json
{
  "phone": "03001234567",
  "email": "vendor@example.com",
  "address": "123 Market Street, Karachi"
}
```

### Terms JSON Format (Optional):
```json
{
  "payment_days": 30,
  "discount_percent": 2.0,
  "notes": "Net 30 days payment terms"
}
```

---

## Related Documentation

- [Authentication](authentication_api.md) - Login and session management
- [User Management](administrative_api.md) - User CRUD operations
- [Product API](productapi.md) - Product management
- [Customer Invoice API](customer-invoice-api.md) - Customer and order management
- [Stock API](stockapi.md) - Stock management
