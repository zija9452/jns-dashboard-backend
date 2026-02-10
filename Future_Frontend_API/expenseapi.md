# Expense API Documentation

This document provides comprehensive documentation for all expense-related endpoints in the Regal POS Backend with session-based authentication, including curl commands for testing and integration.

## Authentication

All expense endpoints require session-based authentication. Obtain a session by logging in:

```bash
curl -X POST http://localhost:8000/auth/session-login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

The login response will include a session cookie that will be automatically sent with subsequent requests when using the `-b` flag with curl or proper cookie handling in applications.

## Expense Management Endpoints

### 1. Create Expense

**Endpoint**: `POST /admin/CreateExpense`

**Description**: Create a new expense.

**Authentication**: Admin role required

**Query Parameters**:
- `e_name`: Expense name/type
- `e_amount`: Expense amount
- `et_id_fk`: User ID who created the expense (optional)
- `note`: Additional notes (optional)

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/CreateExpense?e_name=Office Supplies&e_amount=250.00&et_id_fk=user-uuid-string&note=Purchased office supplies" \
  -b cookies.txt
```

**Response**:
```json
{
  "e_id": "uuid-string",
  "e_name": "Office Supplies",
  "e_amount": 250.00,
  "et_id_fk": "user-uuid-string",
  "e_date": "2026-02-03",
  "note": "Purchased office supplies"
}
```

### 2. Get Expense

**Endpoint**: `GET /admin/GetExpense/{id}`

**Description**: Retrieve specific expense details by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the expense

**Example**:
```bash
curl -X GET http://localhost:8000/admin/GetExpense/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "e_id": "uuid-string",
  "e_name": "Rent",
  "e_amount": 1200.00,
  "et_id_fk": "user-uuid-string",
  "e_date": "2026-02-03",
  "note": "Monthly office rent"
}
```

### 2. View Expense

**Endpoint**: `GET /admin/Viewexpense`

**Description**: View expenses with search and branch filtering.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `search_string`: Search term to filter expenses
- `branches`: Branch to filter by
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/Viewexpense?search_string=rent&branches=MainBranch&limit=10" \
  -b cookies.txt
```

**Response**:
```json
[
  {
    "e_id": "uuid-string",
    "e_name": "Rent",
    "e_amount": 1200.00,
    "et_id_fk": "user-uuid-string",
    "e_date": "2026-02-03",
    "note": "Monthly office rent",
    "branch": "MainBranch"
  }
]
```

### 3. Update Expense

**Endpoint**: `PUT /admin/UpdateExpense/{id}`

**Description**: Update an expense.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the expense to update

**Query Parameters** (optional):
- `e_name`: New expense name/type
- `e_amount`: New expense amount
- `note`: New notes

**Example**:
```bash
curl -X PUT "http://localhost:8000/admin/UpdateExpense/uuid-string?e_name=Updated Expense&e_amount=300.00&note=Updated note" \
  -b cookies.txt
```

**Response**:
```json
{
  "e_id": "uuid-string",
  "e_name": "Updated Expense",
  "e_amount": 300.00,
  "et_id_fk": "user-uuid-string",
  "e_date": "2026-02-03",
  "note": "Updated note"
}
```

### 4. Delete Expense

**Endpoint**: `POST /admin/DeleteExpense/{id}`

**Description**: Delete an expense.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the expense to delete

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/DeleteExpense/uuid-string" \
  -b cookies.txt
```

**Response**:
```json
{
  "success": true,
  "message": "Expense deleted successfully"
}
```

### 5. Get Branch Expense

**Endpoint**: `POST /admin/Getbranchexpense`

**Description**: Get total expenses for a specific branch.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `branches`: Branch to get expense total for

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/Getbranchexpense?branches=MainBranch" \
  -b cookies.txt
```

**Response**:
```json
{
  "cus_balance": 5000.00
}
```

### 6. View Expense

**Endpoint**: `GET /admin/Viewexpense`

**Description**: View expenses with search and branch filtering.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `search_string`: Search term to filter expenses
- `branches`: Branch to filter by
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/Viewexpense?search_string=rent&branches=MainBranch&limit=10" \
  -b cookies.txt
```

**Response**:
```json
[
  {
    "e_id": "uuid-string",
    "e_name": "Rent",
    "e_amount": 1200.00,
    "et_id_fk": "user-uuid-string",
    "e_date": "2026-02-03",
    "note": "Monthly office rent",
    "branch": "MainBranch"
  }
]
```

### 4. Get All Expenses (Standard)

**Endpoint**: `GET /expenses/`

**Description**: Get list of expenses with pagination.

**Authentication**: Employee role or higher required

**Query Parameters** (optional):
- `created_by`: User ID to filter by
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/expenses/?skip=0&limit=10" \
  -b cookies.txt
```

**Response**:
```json
[
  {
    "id": "uuid-string",
    "expense_type": "Rent",
    "amount": "1200.00",
    "expense_date": "2026-02-03",
    "note": "Monthly office rent",
    "created_by": "user-uuid-string",
    "created_at": "2026-02-03T10:31:18.150552"
  }
]
```

### 5. Get Expense by ID (Standard)

**Endpoint**: `GET /expenses/{id}`

**Description**: Get a specific expense by ID.

**Authentication**: Employee role or higher required

**Parameters**:
- `{id}`: UUID of the expense

**Example**:
```bash
curl -X GET http://localhost:8000/expenses/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "id": "uuid-string",
  "expense_type": "Rent",
  "amount": "1200.00",
  "expense_date": "2026-02-03",
  "note": "Monthly office rent",
  "created_by": "user-uuid-string",
  "created_at": "2026-02-03T10:31:18.150552"
}
```

### 6. Create Expense (Standard)

**Endpoint**: `POST /expenses/`

**Description**: Create a new expense.

**Authentication**: Employee role or higher required

**Request Body**:
```json
{
  "expense_type": "Office Supplies",
  "amount": 250.00,
  "date": "2026-02-03",
  "note": "Purchased office supplies",
  "created_by": "user-uuid-string"
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/expenses/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "expense_type": "Office Supplies",
    "amount": 250.00,
    "date": "2026-02-03",
    "note": "Purchased office supplies",
    "created_by": "user-uuid-string"
  }'
```

**Response**:
```json
{
  "id": "uuid-string",
  "expense_type": "Office Supplies",
  "amount": "250.00",
  "expense_date": "2026-02-03",
  "note": "Purchased office supplies",
  "created_by": "user-uuid-string",
  "created_at": "2026-02-03T10:31:18.150552"
}
```

### 7. Update Expense (Standard)

**Endpoint**: `PUT /expenses/{id}`

**Description**: Update a specific expense by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the expense to update

**Request Body** (all fields optional):
```json
{
  "expense_type": "Updated Expense Type",
  "amount": 300.00,
  "date": "2026-02-03",
  "note": "Updated note"
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/expenses/uuid-string \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "expense_type": "Updated Office Supplies",
    "amount": 350.00
  }'
```

**Response**:
```json
{
  "id": "uuid-string",
  "expense_type": "Updated Office Supplies",
  "amount": "350.00",
  "expense_date": "2026-02-03",
  "note": "Purchased office supplies",
  "created_by": "user-uuid-string",
  "created_at": "2026-02-03T10:31:18.150552"
}
```

### 8. Delete Expense (Standard)

**Endpoint**: `DELETE /expenses/{id}`

**Description**: Delete a specific expense by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the expense to delete

**Example**:
```bash
curl -X DELETE http://localhost:8000/expenses/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "message": "Expense deleted successfully"
}
```

## CRUD Operations Summary

### Create Operations
- `POST /expenses/` - Create a new expense (standard endpoint)
- `POST /admin/CreateExpense` - Create a new expense (frontend compatible)

### Read Operations
- `GET /admin/GetExpense/{id}` - Get specific expense details (frontend compatible)
- `GET /admin/Viewexpense` - View expenses with filtering (frontend compatible)
- `GET /expenses/` - Get list of expenses (standard endpoint)
- `GET /expenses/{id}` - Get specific expense (standard endpoint)

### Update Operations
- `PUT /expenses/{id}` - Update an expense (standard endpoint)
- `PUT /admin/UpdateExpense/{id}` - Update an expense (frontend compatible)

### Delete Operations
- `DELETE /expenses/{id}` - Delete an expense (standard endpoint)
- `POST /admin/DeleteExpense/{id}` - Delete an expense (frontend compatible)

### Report Operations
- `POST /admin/Getbranchexpense` - Get branch expense total

## Database Schema

The Expense model includes the following fields:
- `id`: UUID (Primary Key)
- `expense_type`: String (max 50 chars) - Type of expense (e.g., rent, utilities)
- `amount`: Decimal (10,2) - Expense amount
- `expense_date`: Date - Date of expense
- `note`: String (Optional) - Additional notes
- `created_by`: UUID (Foreign Key) - User who created the expense
- `created_at`: DateTime - Creation timestamp

## Frontend-Compatible Endpoints

The following endpoints are provided for JavaScript frontend compatibility:

- `POST /admin/CreateExpense` - Create a new expense
- `GET /admin/GetExpense/{id}` - Get specific expense details
- `GET /admin/Viewexpense` - View expenses with search and branch filtering
- `PUT /admin/UpdateExpense/{id}` - Update an expense
- `POST /admin/DeleteExpense/{id}` - Delete an expense
- `POST /admin/Getbranchexpense` - Get branch expense total

## Error Handling

All endpoints return standardized error responses:

```json
{
  "error": {
    "type": "error_type",
    "message": "Human-readable error message",
    "status_code": 400,
    "path": "/endpoint/path",
    "timestamp": "2026-01-31T11:00:00.000000"
  }
}
```

## Security Notes

- All endpoints require appropriate role-based access control using session cookies
- Expense data is protected by role-based access control
- Audit logs are maintained for all expense-related actions
- Only admins can modify expense records
- Cashiers and employees can view expenses
- Session-based authentication with cookie management for enhanced security
- Protection against JWT token theft from client-side storage
- Instant logout capability across all devices
- Full control over active sessions

## Production Ready Features

- Async/await implementation for high concurrency
- Pydantic v2 validation
- Proper error handling and logging
- Database transaction safety
- Session-based authentication with cookie management
- Role-based access control
- Input sanitization and validation
- Comprehensive API documentation
- Server-side session control for better security
- Instant logout capability across all devices
- Better compliance with audit trails and regulations

## CRUD Commands for Expense Operations

### Create Expense (Frontend Compatible)
```bash
curl -X POST "http://localhost:8000/admin/CreateExpense?e_name=Office%20Supplies&e_amount=250.00&et_id_fk=user-uuid-string&note=Purchased%20office%20supplies" \
  -b cookies.txt
```

### Create Expense (Standard)
```bash
curl -X POST http://localhost:8000/expenses/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "expense_type": "Office Supplies",
    "amount": 250.00,
    "note": "Purchased office supplies",
    "created_by": "user-uuid-string"
  }'
```

### Get All Expenses
```bash
curl -X GET "http://localhost:8000/expenses/?skip=0&limit=100" \
  -b cookies.txt
```

### Get Specific Expense (Standard)
```bash
curl -X GET http://localhost:8000/expenses/uuid-string \
  -b cookies.txt
```

### Get Specific Expense (Frontend Compatible)
```bash
curl -X GET http://localhost:8000/admin/GetExpense/uuid-string \
  -b cookies.txt
```

### View Expenses (Frontend Compatible)
```bash
curl -X GET "http://localhost:8000/admin/Viewexpense?search_string=office&limit=50" \
  -b cookies.txt
```

### Update Expense (Standard)
```bash
curl -X PUT http://localhost:8000/expenses/uuid-string \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "expense_type": "Updated Expense Type",
    "amount": 300.00
  }'
```

### Update Expense (Frontend Compatible)
```bash
curl -X PUT "http://localhost:8000/admin/UpdateExpense/uuid-string?e_name=Updated%20Expense&e_amount=300.00&note=Updated%20note" \
  -b cookies.txt
```

### Delete Expense (Standard)
```bash
curl -X DELETE http://localhost:8000/expenses/uuid-string \
  -b cookies.txt
```

### Delete Expense (Frontend Compatible)
```bash
curl -X POST "http://localhost:8000/admin/DeleteExpense/uuid-string" \
  -b cookies.txt
```

### Get Branch Expense Total
```bash
curl -X POST "http://localhost:8000/admin/Getbranchexpense?branches=MainBranch" \
  -b cookies.txt
```

### Get All Expenses
```bash
curl -X GET "http://localhost:8000/expenses/?skip=0&limit=100" \
  -b cookies.txt
```

### Get Specific Expense
```bash
curl -X GET http://localhost:8000/expenses/uuid-string \
  -b cookies.txt
```

### Update Expense
```bash
curl -X PUT http://localhost:8000/expenses/uuid-string \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "expense_type": "Updated Expense Type",
    "amount": 300.00
  }'
```

### Delete Expense
```bash
curl -X DELETE http://localhost:8000/expenses/uuid-string \
  -b cookies.txt
```

### Get Expense (Frontend Compatible)
```bash
curl -X GET http://localhost:8000/admin/GetExpense/uuid-string \
  -b cookies.txt
```

### View Expenses (Frontend Compatible)
```bash
curl -X GET "http://localhost:8000/admin/Viewexpense?search_string=office&limit=50" \
  -b cookies.txt
```

### Get Branch Expense Total
```bash
curl -X POST "http://localhost:8000/admin/Getbranchexpense?branches=MainBranch" \
  -b cookies.txt
```