# Expense Management API

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
| `admin_cashier_employee_required_from_session()` | `admin`, `cashier`, `employee` | All expense endpoints |

**Important Notes**:

All expense endpoints are accessible by **admin, cashier, and employee** roles.

---

## API Endpoints

### Expense CRUD Operations

---

### 1. GET /expenses/ - View Expenses (Paginated)

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get paginated list of expenses ordered by date (oldest first). This is the **main endpoint** used by the frontend.

**Endpoint**: `GET /expenses/?page=1&limit=8&created_by=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (1-based) |
| `limit` | int | 8 | Items per page |
| `created_by` | string | - | Filter by user ID who created expense |

**Example**:
```bash
curl -X GET "http://localhost:8000/expenses/?page=1&limit=8" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid-string",
      "expense_type": "Electricity Bill",
      "expense": "Monthly electricity bill",
      "amount": 15000.00,
      "expense_date": "2026-03-01",
      "branch": "European Sports Light House",
      "created_by": "uuid-string",
      "created_at": "2026-03-01T10:00:00"
    }
  ],
  "page": 1,
  "limit": 8,
  "total": 50,
  "totalPages": 7
}
```

**Response Fields**:
- `data`: Array of expenses (max 8 per page)
- `expense_type`: Type of expense (from expense types)
- `expense`: Description/details of expense
- `amount`: Expense amount
- `expense_date`: Date of expense
- `branch`: Branch where expense occurred
- `created_by`: User ID who created the expense
- `created_at`: Timestamp when record was created

**Note**: Expenses are ordered by `expense_date` ascending (oldest first).

**Error** (401 Unauthorized):
```json
{
  "detail": "Not authenticated"
}
```

---

### 2. GET /expenses/{expense_id} - Get Expense Details

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get specific expense details by ID.

**Endpoint**: `GET /expenses/{expense_id}`

**Path Parameter**: `expense_id` - UUID of the expense

**Example**:
```bash
curl -X GET "http://localhost:8000/expenses/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "expense_type": "Electricity Bill",
  "expense": "Monthly electricity bill",
  "amount": 15000.00,
  "expense_date": "2026-03-01",
  "branch": "European Sports Light House",
  "created_by": "uuid-string",
  "created_at": "2026-03-01T10:00:00"
}
```

**Error** (404 Not Found):
```json
{
  "detail": "Expense not found"
}
```

---

### 3. POST /expenses/ - Create Expense

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Create a new expense. The `created_by` field is automatically set to the current user if not provided.

**Endpoint**: `POST /expenses/`

**Request Body**:
```json
{
  "expense_type": "Electricity Bill",
  "expense": "Monthly electricity bill",
  "amount": 15000.00,
  "expense_date": "2026-03-01",
  "branch": "European Sports Light House",
  "created_by": "uuid-string"
}
```

**Request Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `expense_type` | string | ✅ Yes | Expense type name |
| `expense` | string | ✅ Yes | Expense description |
| `amount` | number | ✅ Yes | Expense amount |
| `expense_date` | string | ❌ No | Date of expense (YYYY-MM-DD) |
| `branch` | string | ❌ No | Branch name |
| `created_by` | string | ❌ No | User ID (auto-set if not provided) |

**Example**:
```bash
curl -X POST "http://localhost:8000/expenses/" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "expense_type": "Electricity Bill",
    "expense": "Monthly electricity bill",
    "amount": 15000.00,
    "branch": "European Sports Light House"
  }'
```

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "expense_type": "Electricity Bill",
  "expense": "Monthly electricity bill",
  "amount": 15000.00,
  "expense_date": "2026-03-01",
  "branch": "European Sports Light House",
  "created_by": "uuid-string",
  "created_at": "2026-03-01T10:00:00"
}
```

**Errors**:

**400 Bad Request** - Missing required fields:
```json
{
  "detail": "Expense type and amount are required"
}
```

---

### 4. PUT /expenses/{expense_id} - Update Expense

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Update an existing expense.

**Endpoint**: `PUT /expenses/{expense_id}`

**Path Parameter**: `expense_id` - UUID of the expense

**Request Body** (all fields optional):
```json
{
  "expense_type": "Updated Type",
  "expense": "Updated description",
  "amount": 20000.00,
  "expense_date": "2026-03-05",
  "branch": "Updated Branch"
}
```

**Example**:
```bash
curl -X PUT "http://localhost:8000/expenses/uuid-string" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "expense_type": "Updated Type",
    "amount": 20000.00
  }'
```

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "expense_type": "Updated Type",
  "expense": "Monthly electricity bill",
  "amount": 20000.00,
  "expense_date": "2026-03-01",
  "branch": "European Sports Light House",
  "created_by": "uuid-string",
  "created_at": "2026-03-01T10:00:00"
}
```

**Errors**:

**404 Not Found**:
```json
{
  "detail": "Expense not found"
}
```

---

### 5. DELETE /expenses/{expense_id} - Delete Expense

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Delete an expense by ID.

**Endpoint**: `DELETE /expenses/{expense_id}`

**Path Parameter**: `expense_id` - UUID of the expense

**Example**:
```bash
curl -X DELETE "http://localhost:8000/expenses/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "message": "Expense deleted successfully"
}
```

**Errors**:

**404 Not Found**:
```json
{
  "detail": "Expense not found"
}
```

---

## Expense Type Endpoints (Related)

### 6. GET /expense-type/ - View Expense Types

**Access**: `employee_required_from_session()` - **Employee, Cashier, Admin**

**Description**: Get list of expense types for dropdown (used in expense form).

**Endpoint**: `GET /expense-type/?page=1&limit=1000`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `limit` | int | 100 | Max records (use 1000 for dropdown) |

**Example**:
```bash
curl -X GET "http://localhost:8000/expense-type/?page=1&limit=1000" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid-string",
      "name": "Electricity Bill",
      "created_at": "2026-03-01T10:00:00"
    },
    {
      "id": "uuid-string-2",
      "name": "Water Bill",
      "created_at": "2026-03-01T10:00:00"
    }
  ],
  "page": 1,
  "limit": 1000,
  "total": 10,
  "totalPages": 1
}
```

---

## Frontend API Routes

The frontend uses Next.js API routes as proxies:

| Frontend Route | Backend Endpoint |
|----------------|------------------|
| `GET /api/expenses/` | `GET /expenses/` |
| `GET /api/expenses/{id}` | `GET /expenses/{id}` |
| `POST /api/expenses/` | `POST /expenses/` |
| `PUT /api/expenses/{id}` | `PUT /expenses/{id}` |
| `DELETE /api/expenses/{id}` | `DELETE /expenses/{id}` |
| `GET /api/expense-type/` | `GET /expense-type/` |

**Example** - Frontend fetch with pagination:
```typescript
const fetchExpenses = async (page: number = 1) => {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: '8'
  });

  const response = await fetch(`/api/expenses/?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch expenses');
  }

  return response.json();
};
```

---

## Error Codes

| HTTP Status | Meaning | Common Causes |
|-------------|---------|---------------|
| 200 | OK | Success |
| 400 | Bad Request | Invalid input, missing required fields, invalid date format |
| 401 | Unauthorized | Not logged in, invalid session |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Expense not found, expense type not found |
| 500 | Server Error | Database error, server issue |

---

## Testing Checklist

### Login First
- [ ] Login with admin credentials
- [ ] Save cookies (`-c cookies.txt`)

### Test GET /expenses/
- [ ] Fetch first page (page=1, limit=8)
- [ ] Verify expenses ordered by date (oldest first)
- [ ] Fetch with created_by filter
- [ ] Verify pagination response format

### Test POST /expenses/
- [ ] Create new expense with all fields
- [ ] Create expense without expense_date (should use current date)
- [ ] Create expense without created_by (should auto-set)
- [ ] Try create without expense_type (should fail)
- [ ] Try create without amount (should fail)

### Test GET /expenses/{id}
- [ ] Get expense details by ID
- [ ] Get non-existent ID (should 404)

### Test PUT /expenses/{id}
- [ ] Update expense amount
- [ ] Update expense description
- [ ] Update expense date
- [ ] Try update non-existent ID (should 404)

### Test DELETE /expenses/{id}
- [ ] Delete expense
- [ ] Try delete non-existent expense (should 404)

### Test Expense Types
- [ ] Fetch expense types for dropdown
- [ ] Verify expense types are available for selection

---

## Expense Data Model

### Database Schema:
```python
class Expense(SQLModel, table=True):
    __tablename__ = "expenses"
    
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    expense_type: str = Field(max_length=100)  # Expense type name
    expense: str = Field(max_length=500)       # Expense description
    amount: Decimal = Field(sa_column=Column(Numeric(10, 2)))
    expense_date: date = Field(default_factory=date.today)
    branch: Optional[str] = Field(default=None, max_length=200)
    created_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

### Frontend Response Format:
```json
{
  "id": "uuid-string",
  "expense_type": "Electricity Bill",
  "expense": "Monthly electricity bill",
  "amount": 15000.00,
  "expense_date": "2026-03-01",
  "branch": "European Sports Light House",
  "created_by": "uuid-string",
  "created_at": "2026-03-01T10:00:00"
}
```

### Expense Type Schema:
```python
class ExpenseType(SQLModel, table=True):
    __tablename__ = "expense_types"
    
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100, unique=True)
    created_at: datetime = Field(default_factory=datetime.now)
```

---

## Common Expense Types

Examples of common expense types used in the system:

| Expense Type | Description |
|--------------|-------------|
| Electricity Bill | Monthly electricity charges |
| Water Bill | Monthly water charges |
| Gas Bill | Monthly gas charges |
| Internet Bill | Monthly internet charges |
| Rent | Monthly rent payment |
| Salary | Employee salaries |
| Maintenance | Equipment/building maintenance |
| Office Supplies | Stationery, paper, etc. |
| Marketing | Advertising, promotions |
| Travel | Business travel expenses |
| Miscellaneous | Other expenses |

---

## Related Documentation

- [Authentication](authentication_api.md) - Login and session management
- [User Management](administrative_api.md) - User CRUD operations
- [Expense Type API](expense_type_api.md) - Expense type management
- [Vendor API](vendorapi.md) - Vendor management
- [Stock API](stockapi.md) - Stock management
