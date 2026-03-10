# Salesman Management API

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
| `admin_cashier_employee_required_from_session()` | `admin`, `cashier`, `employee` | GET /viewsalesman |
| `employee_required_from_session()` | `admin`, `cashier`, `employee` | GET /, GET /{id} |
| `admin_required_from_session()` | `admin` only | POST, PUT, DELETE |

**Important Notes**:

1. **GET /salesman/viewsalesman** - Requires **any authenticated user** (admin, cashier, employee)
   - All authenticated users can view salesmen list

2. **GET /salesman/** - Requires **employee** or higher
   - Employee, cashier, admin can view salesmen (standard REST endpoint)

3. **POST /salesman/** - Requires **admin** only
   - Only admins can create salesmen

4. **PUT /salesman/{id}** - Requires **admin** only
   - Only admins can update salesmen

5. **DELETE /salesman/{id}** - Requires **admin** only
   - Only admins can delete salesmen

---

## API Endpoints

### Salesman CRUD Operations

---

### 1. GET /salesman/viewsalesman - View Salesmen (Paginated)

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get paginated list of salesmen with search and branch filtering. This is the **main endpoint** used by the frontend.

**Endpoint**: `GET /salesman/viewsalesman?page=1&limit=8&search_string=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (1-based) |
| `limit` | int | 8 | Items per page |
| `search_string` | string | - | Search by salesman name |
| `branches` | string | - | Filter by branch name |
| `searchphone` | string | - | Search by phone (optional) |

**Example**:
```bash
curl -X GET "http://localhost:8000/salesman/viewsalesman?page=1&limit=8&search_string=John" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "data": [
    {
      "sal_id": "uuid-string",
      "sal_name": "John Smith",
      "sal_phone": "03001234567",
      "sal_address": "123 Market Street",
      "branch": "European Sports Light House"
    }
  ],
  "page": 1,
  "limit": 8,
  "total": 15,
  "totalPages": 2
}
```

**Response Fields**:
- `data`: Array of salesmen (max 8 per page)
- `page`: Current page number
- `limit`: Items per page
- `total`: Total number of salesmen matching search
- `totalPages`: Total pages (for pagination UI)

**Error** (401 Unauthorized):
```json
{
  "detail": "Not authenticated"
}
```

---

### 2. POST /salesman/ - Create Salesman

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Create a new salesman.

**Endpoint**: `POST /salesman/`

**Request Body**:
```json
{
  "name": "John Smith",
  "phone": "03001234567",
  "address": "123 Market Street",
  "branch": "European Sports Light House"
}
```

**Request Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | ✅ Yes | Salesman name |
| `phone` | string | ✅ Yes | Phone number |
| `address` | string | ✅ Yes | Address |
| `branch` | string | ❌ No | Branch name |

**Example**:
```bash
curl -X POST "http://localhost:8000/salesman/" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "John Smith",
    "phone": "03001234567",
    "address": "123 Market Street",
    "branch": "European Sports Light House"
  }'
```

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "name": "John Smith",
  "phone": "03001234567",
  "address": "123 Market Street",
  "branch": "European Sports Light House",
  "created_at": "2026-03-10T10:00:00",
  "updated_at": "2026-03-10T10:00:00"
}
```

**Errors**:

**400 Bad Request** - Missing required fields:
```json
{
  "detail": "Name is required"
}
```

---

### 3. GET /salesman/{salesman_id} - Get Salesman Details

**Access**: `employee_required_from_session()` - **Employee, Cashier, Admin**

**Description**: Get specific salesman details by ID.

**Endpoint**: `GET /salesman/{salesman_id}`

**Path Parameter**: `salesman_id` - UUID of the salesman

**Example**:
```bash
curl -X GET "http://localhost:8000/salesman/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "name": "John Smith",
  "phone": "03001234567",
  "address": "123 Market Street",
  "branch": "European Sports Light House",
  "created_at": "2026-03-10T10:00:00",
  "updated_at": "2026-03-10T10:00:00"
}
```

**Error** (404 Not Found):
```json
{
  "detail": "Salesman not found"
}
```

---

### 4. PUT /salesman/{salesman_id} - Update Salesman

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Update an existing salesman.

**Endpoint**: `PUT /salesman/{salesman_id}`

**Path Parameter**: `salesman_id` - UUID of the salesman

**Request Body** (all fields optional):
```json
{
  "name": "John Smith Updated",
  "phone": "03009876543",
  "address": "456 New Street",
  "branch": "Updated Branch"
}
```

**Example**:
```bash
curl -X PUT "http://localhost:8000/salesman/uuid-string" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "John Smith Updated",
    "phone": "03009876543",
    "address": "456 New Street"
  }'
```

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "name": "John Smith Updated",
  "phone": "03009876543",
  "address": "456 New Street",
  "branch": "European Sports Light House",
  "updated_at": "2026-03-10T11:00:00"
}
```

**Errors**:

**404 Not Found**:
```json
{
  "detail": "Salesman not found"
}
```

---

### 5. DELETE /salesman/{salesman_id} - Delete Salesman

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Delete a salesman by ID.

**Endpoint**: `DELETE /salesman/{salesman_id}`

**Path Parameter**: `salesman_id` - UUID of the salesman

**Important**: Only admins can delete salesmen.

**Example**:
```bash
curl -X DELETE "http://localhost:8000/salesman/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "message": "Salesman deleted successfully"
}
```

**Errors**:

**404 Not Found**:
```json
{
  "detail": "Salesman not found"
}
```

---

### 6. POST /salesman/salesmanviewreport - Salesman Report

**Access**: `admin_required_from_session()` - **Admin only**

**Description**: Generate salesman details report (PDF, used by ReportModal).

**Endpoint**: `POST /salesman/salesmanviewreport`

**Example**:
```bash
curl -X POST "http://localhost:8000/salesman/salesmanviewreport" \
  -b cookies.txt
```

**Response** (200 OK):
```
Base64 encoded PDF string
```

**Report Contents**:
- Salesman name
- Phone number
- Address
- Branch
- Total count

---

## Frontend API Routes

The frontend uses Next.js API routes as proxies:

| Frontend Route | Backend Endpoint |
|----------------|------------------|
| `GET /api/salesman/viewsalesman` | `GET /salesman/viewsalesman` |
| `POST /api/salesman/` | `POST /salesman/` |
| `GET /api/salesman/{id}` | `GET /salesman/{id}` |
| `PUT /api/salesman/{id}` | `PUT /salesman/{id}` |
| `DELETE /api/salesman/{id}` | `DELETE /salesman/{id}` |
| `POST /api/salesman/report` | `POST /salesman/salesmanviewreport` |

**Example** - Frontend fetch with pagination:
```typescript
const fetchSalesmen = async (page: number = 1, searchTerm: string = '') => {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: '8',
    search_string: searchTerm
  });

  const response = await fetch(`/api/salesman/viewsalesman?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch salesmen');
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
| 403 | Forbidden | Insufficient permissions (not admin) |
| 404 | Not Found | Salesman not found |
| 500 | Server Error | Database error, server issue |

---

## Testing Checklist

### Login First
- [ ] Login with admin credentials
- [ ] Save cookies (`-c cookies.txt`)

### Test GET /salesman/viewsalesman
- [ ] Fetch first page (page=1, limit=8)
- [ ] Fetch with search term
- [ ] Fetch with branch filter
- [ ] Verify pagination response format

### Test POST /salesman/
- [ ] Create new salesman with all fields
- [ ] Create salesman without branch (optional)
- [ ] Try create without name (should fail)
- [ ] Try create as non-admin (should fail with 403)

### Test GET /salesman/{id}
- [ ] Get salesman details by ID
- [ ] Get non-existent ID (should 404)

### Test PUT /salesman/{id}
- [ ] Update salesman name
- [ ] Update salesman phone
- [ ] Update salesman branch
- [ ] Try update as non-admin (should fail with 403)

### Test DELETE /salesman/{id}
- [ ] Delete salesman (admin only)
- [ ] Try delete as non-admin (should fail with 403)
- [ ] Try delete non-existent salesman (should 404)

### Test Report
- [ ] Generate salesman report (PDF)

---

## Salesman Data Model

### Database Schema:
```python
class Salesman(SQLModel, table=True):
    __tablename__ = "salesmen"
    
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    phone: Optional[str] = Field(default=None, max_length=20)
    address: Optional[str] = Field(default=None)
    branch: Optional[str] = Field(default=None, max_length=200)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

### Frontend Response Format:
```json
{
  "sal_id": "uuid-string",
  "sal_name": "John Smith",
  "sal_phone": "03001234567",
  "sal_address": "123 Market Street",
  "branch": "European Sports Light House"
}
```

---

## Related Documentation

- [Authentication](authentication_api.md) - Login and session management
- [User Management](administrative_api.md) - User CRUD operations
- [Product API](productapi.md) - Product management
- [Customer Invoice API](customer-invoice-api.md) - Customer and order management
- [Vendor API](vendorapi.md) - Vendor management
