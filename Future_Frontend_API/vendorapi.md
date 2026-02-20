# Vendor API Documentation

This document provides comprehensive documentation for all vendor-related endpoints in the Regal POS Backend with session-based authentication, including curl commands for testing and integration.

## Authentication

All vendor endpoints require session-based authentication. Obtain a session by logging in:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}' \
  -c cookies.txt
```

The login response will include a session cookie that will be automatically sent with subsequent requests when using the `-b` flag with curl.

**Login Response:**
```json
{
  "message": "Login successful",
  "user": {
    "id": "uuid-string",
    "username": "admin",
    "role": "admin",
    "company_id": null
  }
}
```

---

## Vendor Model

### Fields:
```json
{
  "id": "uuid-string",           // Auto-generated UUID
  "name": "Vendor Name",          // VARCHAR(100)
  "contacts": "{}",               // JSON string (phone, email, address)
  "branch": "Branch Name",        // VARCHAR(200), NEW FIELD
  "terms": "{}",                  // JSON string (optional)
  "created_at": "2026-02-20",     // DateTime
  "updated_at": "2026-02-20"      // DateTime
}
```

### Frontend Response Format (viewvendor):
```json
[
  {
    "ven_id": "uuid-string",
    "ven_name": "Vendor Name",
    "ven_phone": "1234567890",
    "ven_address": "123 Main St",
    "branch": "European Sports Light House",
    "vend_balance": 0.0
  }
]
```

---

## CRUD Endpoints (vendors.py router)

**Base URL:** `http://localhost:8000/vendors`

**Authentication:** Admin role required for ALL endpoints

### 1. Create Vendor

**Endpoint:** `POST /vendors/`

**Description:** Create a new vendor.

**Authentication:** Admin required

**Request Body (JSON):**
```json
{
  "name": "Vendor Name",
  "contacts": "{\"phone\":\"1234567890\",\"email\":\"\",\"address\":\"123 Main St\"}",
  "branch": "European Sports Light House",
  "terms": null
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/vendors/ \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"name":"New Vendor","contacts":"{\"phone\":\"1234567890\",\"email\":\"\",\"address\":\"123 Main St\"}","branch":"European Sports Light House"}'
```

**Response:**
```json
{
  "id": "uuid-string",
  "name": "New Vendor",
  "contacts": "{\"phone\":\"1234567890\",\"email\":\"\",\"address\":\"123 Main St\"}",
  "branch": "European Sports Light House",
  "terms": null,
  "created_at": "2026-02-20T00:00:00",
  "updated_at": "2026-02-20T00:00:00"
}
```

---

### 2. Get All Vendors (Paginated)

**Endpoint:** `GET /vendors/?skip=0&limit=100`

**Description:** Get list of vendors with pagination.

**Authentication:** Admin required

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records to return (default: 100)

**Example:**
```bash
curl -X GET "http://localhost:8000/vendors/?skip=0&limit=10" \
  -b cookies.txt
```

**Response:**
```json
[
  {
    "id": "uuid-string",
    "name": "Vendor Name",
    "contacts": "{\"phone\":\"1234567890\",\"email\":\"\",\"address\":\"123 Main St\"}",
    "branch": "European Sports Light House",
    "terms": null,
    "created_at": "2026-02-20T00:00:00",
    "updated_at": "2026-02-20T00:00:00"
  }
]
```

---

### 3. Get Vendor by ID

**Endpoint:** `GET /vendors/{vendor_id}`

**Description:** Get a specific vendor by ID.

**Authentication:** Admin required

**Path Parameter:**
- `{vendor_id}`: UUID of the vendor

**Example:**
```bash
curl -X GET http://localhost:8000/vendors/uuid-string \
  -b cookies.txt
```

**Response:** Same as Create Vendor response

---

### 4. Update Vendor

**Endpoint:** `PUT /vendors/{vendor_id}`

**Description:** Update a specific vendor by ID.

**Authentication:** Admin required

**Path Parameter:**
- `{vendor_id}`: UUID of the vendor

**Request Body (JSON) - All fields optional:**
```json
{
  "name": "Updated Vendor Name",
  "contacts": "{\"phone\":\"9876543210\",\"email\":\"\",\"address\":\"456 New St\"}",
  "branch": "European Sports Light House",
  "terms": "Net 30"
}
```

**Example:**
```bash
curl -X PUT http://localhost:8000/vendors/uuid-string \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"name":"Updated Vendor Name","contacts":"{\"phone\":\"9876543210\",\"email\":\"\",\"address\":\"456 New St\"}","branch":"European Sports Light House"}'
```

**Response:** Same as Create Vendor response

---

### 5. Delete Vendor

**Endpoint:** `DELETE /vendors/{vendor_id}`

**Description:** Delete a specific vendor by ID.

**Authentication:** Admin required

**Path Parameter:**
- `{vendor_id}`: UUID of the vendor

**Example:**
```bash
curl -X DELETE http://localhost:8000/vendors/uuid-string \
  -b cookies.txt
```

**Response:**
```json
{
  "message": "Vendor deleted successfully"
}
```

---

## Frontend-Compatible Endpoints

These endpoints return data in frontend-specific format.

**Base URL:** `http://localhost:8000/vendors`

### 6. View Vendors (Frontend Format)

**Endpoint:** `GET /vendors/viewvendor`

**Description:** View vendors with search and branch filtering (frontend format).

**Authentication:** Admin required

**Query Parameters (optional):**
- `search_string`: Search by vendor name
- `branches`: Filter by branch
- `searchphone`: Search by phone number
- `searchaddress`: Search by address
- `skip`: Pagination offset (default: 0)
- `limit`: Max records (default: 100)

**Example:**
```bash
curl -X GET "http://localhost:8000/vendors/viewvendor?skip=0&limit=8" \
  -b cookies.txt
```

**Response:**
```json
[
  {
    "ven_id": "uuid-string",
    "ven_name": "Vendor Name",
    "ven_phone": "1234567890",
    "ven_address": "123 Main St",
    "branch": "European Sports Light House",
    "vend_balance": 0.0
  }
]
```

**Note:** `vend_balance` is the vendor balance field (NOT `cus_balance` which is for customers)

---

### 7. Get Vendor Details (Frontend Format)

**Endpoint:** `GET /vendors/getvendor/{id}`

**Description:** Retrieve specific vendor details in frontend format.

**Authentication:** Admin required

**Path Parameter:**
- `{id}`: UUID of the vendor

**Example:**
```bash
curl -X GET http://localhost:8000/vendors/getvendor/uuid-string \
  -b cookies.txt
```

**Response:**
```json
{
  "ven_id": "uuid-string",
  "ven_name": "Vendor Name",
  "ven_phone": "1234567890",
  "ven_address": "123 Main St",
  "branch": "European Sports Light House"
}
```

---

### 8. Delete Vendor (Frontend Format)

**Endpoint:** `POST /vendors/deletevendor/{id}`

**Description:** Delete a vendor (frontend-compatible response).

**Authentication:** Admin required

**Path Parameter:**
- `{id}`: UUID of the vendor

**Example:**
```bash
curl -X POST http://localhost:8000/vendors/deletevendor/uuid-string \
  -b cookies.txt
```

**Response:**
```json
{
  "success": true,
  "message": "Vendor deleted successfully"
}
```

---

### 9. Get Vendor Balance

**Endpoint:** `POST /vendors/getvendorbalance`

**Description:** Get vendor balance by branch.

**Authentication:** Admin required

**Query Parameters (optional):**
- `branches`: Branch name to get balance for

**Example:**
```bash
curl -X POST "http://localhost:8000/vendors/getvendorbalance?branches=European%20Sports%20Light%20House" \
  -b cookies.txt
```

**Response:**
```json
{
  "cus_balance": 5000.0
}
```

**Note:** Returns `cus_balance` field name for frontend compatibility

---

### 10. Generate Vendor Report (PDF)

**Endpoint:** `POST /vendors/vendorviewreport`

**Description:** Generate vendor view report in PDF format (base64 encoded).

**Authentication:** Admin required

**Example:**
```bash
curl -X POST http://localhost:8000/vendors/vendorviewreport \
  -b cookies.txt
```

**Response:**
```json
"JVBERi0xLjQKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKPj4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovTWVkaWFCb3ggWzAgMCA2MTIgNzkyXQovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL0xlbmd0aCA0NAo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjcyIDcyMCBUZAooVmVuZG9yIFJlcG9ydCkgVGoKRVQKZW5kc3RyZWFtCmVuZG9iagp4cmVmCjAgNQp0cmFpbGVyCjw8Ci9TaXplIDUKL1Jvb3QgMSAwIFIKPj4KJSVFT0Y="
```

**Usage:** Decode base64 string to get PDF file

---

## Removed/Duplicate Endpoints

The following endpoints have been **REMOVED** from `admin.py` to avoid duplication:

- ❌ `GET /admin/getvendor/{id}` - Use `/vendors/getvendor/{id}`
- ❌ `GET /admin/viewvendor` - Use `/vendors/viewvendor`
- ❌ `POST /admin/deletevendor/{id}` - Use `/vendors/deletevendor/{id}`
- ❌ `POST /admin/getvendorbalance` - Use `/vendors/getvendorbalance`
- ❌ `POST /admin/vendorviewreport` - Use `/vendors/vendorviewreport`

**All vendor endpoints are now in `vendors.py` router only.**

---

## Error Handling

All endpoints return standardized error responses:

```json
{
  "error": {
    "type": "error_type",
    "message": "Human-readable error message",
    "status_code": 400,
    "path": "/endpoint/path",
    "timestamp": "2026-02-20T00:00:00.000000"
  }
}
```

### Common Error Types:
- `validation_error` - Invalid request data (422)
- `http_error` - Resource not found (404)
- `authentication_error` - Invalid/missing credentials (401)
- `authorization_error` - Insufficient permissions (403)
- `internal_error` - Server error (500)

---

## Security Notes

- **All vendor endpoints require Admin role** (no employee access)
- Session-based authentication with cookies
- Audit logs maintained for all vendor actions
- Input validation and sanitization
- CORS configured for frontend URLs
- Security headers enabled (XSS, CSRF, clickjacking protection)

---

## Frontend Integration

### Next.js API Routes:
```
/api/admin/viewvendor        → GET  /vendors/viewvendor
/api/admin/deletevendor/[id] → POST /vendors/deletevendor/{id}
/api/vendors/vendorviewreport → POST /vendors/vendorviewreport
```

### Frontend Pages:
```
/vendors          - Vendor list with CRUD operations
/vendor-payment   - Vendor payment management
/vendor-details   - Vendor report viewer
```

---

## Production Ready Features

- ✅ Async/await implementation for high concurrency
- ✅ Pydantic v2 validation
- ✅ Proper error handling and logging
- ✅ Database transaction safety
- ✅ Session-based authentication
- ✅ Role-based access control (Admin only)
- ✅ Input sanitization and validation
- ✅ Audit trail logging
- ✅ Structured logging with correlation IDs
- ✅ Request compression
- ✅ Performance metrics

---

## Testing Checklist

- [ ] Login and obtain session cookie
- [ ] Create a new vendor
- [ ] Get all vendors (paginated)
- [ ] Get vendor by ID
- [ ] Update vendor
- [ ] View vendors with search
- [ ] Generate vendor report
- [ ] Delete vendor
- [ ] Test authentication errors
- [ ] Test authorization errors
