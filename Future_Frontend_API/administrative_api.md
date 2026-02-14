# Administrative API Documentation

This document provides comprehensive documentation for all administrative endpoints in the Regal POS Backend with session-based authentication, including curl commands for testing and integration.

## Authentication

All admin endpoints require session-based authentication. Obtain a session by logging in:

```bash
curl -X POST http://localhost:8000/auth/session-login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

The login response will include a session cookie that will be automatically sent with subsequent requests when using the `-b` flag with curl or proper cookie handling in applications.

## Admin User Management Endpoints

### 1. Get Admin User Details

**Endpoint**: `GET /admin/getadmin/{id}`

**Description**: Retrieve details of a specific admin user by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the admin user

**Example**:
```bash
curl -X GET http://localhost:8000/admin/getadmin/8fc7528b-c3a2-4b36-a39a-68c13699de80 \
  -b cookies.txt
```

**Response**:
```json
{
  "ad_id": "8fc7528b-c3a2-4b36-a39a-68c13699de80",
  "ad_name": "Admin User",
  "ad_role": "admin",
  "ad_phone": "",
  "ad_address": "",
  "ad_password": "",
  "ad_cnic": "",
  "ad_branch": ""
}
```

### 2. Create Admin User

**Endpoint**: `POST /admin/createadmin`

**Description**: Create a new admin user.

**Authentication**: Admin role required

**Request Body** (JSON):
```json
{
  "ad_name": "Full name of the admin user",
  "ad_role": "Role (admin, cashier, employee)",
  "ad_phone": "Phone number (optional)",
  "ad_address": "Address (optional)",
  "ad_password": "Password (optional, defaults to 'default_password123')",
  "ad_cnic": "CNIC number (optional)",
  "ad_branch": "Branch (optional)"
}
```

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/createadmin" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=your_session_token" \
  -d '{
    "ad_name": "New Admin",
    "ad_role": "admin",
    "ad_phone": "1234567890",
    "ad_address": "New Address",
    "ad_password": "secure_password",
    "ad_cnic": "123456789",
    "ad_branch": "Main Branch"
  }'
```

**Response**:
```json
{
  "ad_id": "uuid-string",
  "ad_name": "New Admin",
  "ad_role": "admin",
  "ad_phone": "1234567890",
  "ad_address": "New Address",
  "ad_cnic": "123456789",
  "ad_branch": "Main Branch",
  "message": "Admin user created successfully"
}
```

### 3. Update Admin User

**Endpoint**: `PUT /admin/updateadmin/{id}`

**Description**: Update details of an existing admin user.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the admin user to update

**Request Body** (JSON, all fields optional):
```json
{
  "ad_name": "Updated full name",
  "ad_role": "Updated role",
  "ad_phone": "Updated phone number",
  "ad_address": "Updated address",
  "ad_password": "Updated password",
  "ad_cnic": "Updated CNIC number",
  "ad_branch": "Updated branch"
}
```

**Example**:
```bash
curl -X PUT "http://localhost:8000/admin/updateadmin/uuid-string" \
  -H "Content-Type: application/json" \
  -H "Cookie: session_token=your_session_token" \
  -d '{
    "ad_name": "Updated Name",
    "ad_phone": "0987654321"
  }'
```

**Response**:
```json
{
  "ad_id": "uuid-string",
  "ad_name": "Updated Name",
  "ad_role": "admin",
  "ad_phone": "0987654321",
  "ad_address": "Previous Address",
  "ad_cnic": "Previous CNIC",
  "ad_branch": "Previous Branch",
  "message": "Admin user updated successfully"
}
```

### 4. Delete Admin User

**Endpoint**: `POST /admin/deleteadmin/{id}`

**Description**: Delete an admin user by ID.

**Authentication**: Admin role required

**Path Parameter**:
- `{id}`: UUID of the admin user to delete

**Note**: Users with audit logs cannot be deleted due to foreign key constraints for compliance purposes.

**Example**:
```bash
curl -X POST http://localhost:8000/admin/deleteadmin/uuid-string \
  -b cookies.txt
```

**Response**:
```json
{
  "success": true,
  "message": "User deleted successfully"
}
```

### 5. View All Admin Users

**Endpoint**: `GET /admin/viewadmins`

**Description**: Get a list of all admin users with optional search functionality.

**Authentication**: Admin role required (admin or cashier roles can access)

**Query Parameters** (optional):
- `search_string`: Search term to filter users (searches in name, username, email, phone, address, cnic)
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/viewadmins?search_string=admin&limit=10" \
  -b cookies.txt
```

**Response**:
```json
[
  {
    "ad_id": "uuid-string",
    "ad_name": "Admin User",
    "ad_role": "admin",
    "ad_phone": "1234567890",
    "ad_address": "Address",
    "ad_cnic": "123456789",
    "ad_branch": "Branch",
    "is_active": true,
    "created_at": "2026-01-30T10:31:18.150552"
  }
]
```

### 6. View All Salesmen

**Endpoint**: `GET /admin/viewsalesman`

**Description**: Get a list of all salesmen with optional search functionality.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `search_string`: Search term to filter salesmen
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/viewsalesman?search_string=john&limit=10" \
  -b cookies.txt
```

**Response**:
```json
[
  {
    "sal_id": "uuid-string",
    "sal_name": "John Doe",
    "sal_phone": "",
    "sal_address": "",
    "branch": ""
  }
]
```

## Product Management Endpoints

### 7. Get Product by ID

**Endpoint**: `GET /admin/GetProducts/{id}`

**Description**: Retrieve specific product details by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the product

**Example**:
```bash
curl -X GET http://localhost:8000/admin/GetProducts/8fc7528b-c3a2-4b36-a39a-68c13699de80 \
  -b cookies.txt
```

**Response**:
```json
{
  "pro_id": "uuid-string",
  "pro_name": "Product Name",
  "pro_price": 99.99,
  "pro_cost": 79.99,
  "pro_barcode": "1234567890",
  "pro_dis": 0.0,
  "cat_id_fk": "category-id",
  "limitedquan": null,
  "branch": "Main Branch",
  "brand": "Brand Name",
  "pro_image": "image-url"
}
```

### 8. View Products

**Endpoint**: `GET /admin/Viewproduct`

**Description**: View products with search and branch filtering.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `search_string`: Search term to filter products
- `branches`: Branch to filter by
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/Viewproduct?search_string=laptop&branches=Main%20Branch&limit=10" \
  -b cookies.txt
```

**Response**:
```json
[
  {
    "pro_id": "uuid-string",
    "pro_name": "Product Name",
    "pro_price": 99.99,
    "pro_cost": 79.99,
    "pro_barcode": "1234567890",
    "pro_dis": 0.0,
    "cat_id_fk": "category-id",
    "limitedquan": null,
    "branch": "Main Branch",
    "brand": "Brand Name",
    "pro_image": "image-url"
  }
]
```

### 9. Delete Product

**Endpoint**: `POST /admin/Deleteproduct/{id}`

**Description**: Delete a product by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the product to delete

**Example**:
```bash
curl -X POST http://localhost:8000/admin/Deleteproduct/8fc7528b-c3a2-4b36-a39a-68c13699de80 \
  -b cookies.txt
```

**Response**:
```json
{
  "success": true,
  "message": "Product deleted successfully"
}
```

### 10. Delete Product Image

**Endpoint**: `POST /admin/DeleteProductImage/{id}`

**Description**: Delete product image by product ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the product

**Example**:
```bash
curl -X POST http://localhost:8000/admin/DeleteProductImage/8fc7528b-c3a2-4b36-a39a-68c13699de80 \
  -b cookies.txt
```

**Response**:
```json
{
  "success": true,
  "message": "Product image deleted successfully"
}
```

### 11. Create Brand

**Endpoint**: `POST /admin/brand`

**Description**: Add a new brand.

**Authentication**: Admin role required

**Query Parameters**:
- `brand`: Brand name

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/brand?brand=NewBrand" \
  -b cookies.txt
```

**Response**:
```json
{
  "success": true,
  "ID": 1,
  "shelf": "NewBrand"
}
```

### 12. Delete Brand

**Endpoint**: `POST /admin/Deletebrand`

**Description**: Delete a brand.

**Authentication**: Admin role required

**Query Parameters**:
- `brand`: Brand name to delete

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/Deletebrand?brand=OldBrand" \
  -b cookies.txt
```

**Response**:
```json
{
  "success": true,
  "message": "Brand 'OldBrand' deleted successfully"
}
```

### 13. Get Stock Detail

**Endpoint**: `POST /admin/GetStockDetail`

**Description**: Get stock details for a specific product.

**Authentication**: Admin role required

**Query Parameters**:
- `pro_name`: Product name to search for

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/GetStockDetail?pro_name=Laptop" \
  -b cookies.txt
```

**Response**:
```json
{
  "quantity": 10
}
```

### 14. Get Max Product ID

**Endpoint**: `GET /admin/GetMaxProId`

**Description**: Get the maximum product ID for barcode calculation.

**Authentication**: Admin role required

**Example**:
```bash
curl -X GET http://localhost:8000/admin/GetMaxProId \
  -b cookies.txt
```

**Response**:
```
1005
```

## Customer Management Endpoints

### 15. Get Customer by ID

**Endpoint**: `GET /admin/GetCustomer/{id}`

**Description**: Retrieve specific customer details by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the customer

**Example**:
```bash
curl -X GET http://localhost:8000/admin/GetCustomer/8fc7528b-c3a2-4b36-a39a-68c13699de80 \
  -b cookies.txt
```

**Response**:
```json
{
  "cus_id": "uuid-string",
  "cus_name": "Customer Name",
  "cus_phone": "1234567890",
  "cus_cnic": "",
  "cus_address": "Customer Address",
  "cus_sal_id_fk": "1",
  "branch": "Main Branch"
}
```

### 16. View Customers

**Endpoint**: `GET /admin/Viewcustomer`

**Description**: View customers with search and branch filtering.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `search_string`: Search term to filter customers
- `branches`: Branch to filter by
- `searchphone`: Phone number to filter by
- `searchaddress`: Address to filter by
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/Viewcustomer?search_string=john&branches=Main%20Branch&limit=10" \
  -b cookies.txt
```

**Response**:
```json
[
  {
    "cus_id": "uuid-string",
    "cus_name": "Customer Name",
    "cus_phone": "1234567890",
    "cus_cnic": "",
    "cus_address": "Customer Address",
    "cus_sal_id_fk": "1",
    "branch": "Main Branch",
    "cus_balance": 100.0
  }
]
```

### 17. Delete Customer

**Endpoint**: `POST /admin/Deletecustomer/{id}`

**Description**: Delete a customer by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the customer to delete

**Example**:
```bash
curl -X POST http://localhost:8000/admin/Deletecustomer/8fc7528b-c3a2-4b36-a39a-68c13699de80 \
  -b cookies.txt
```

**Response**:
```json
{
  "success": true,
  "message": "Customer deleted successfully"
}
```

### 18. Get Customer Balance

**Endpoint**: `POST /admin/Getcustomerbalance`

**Description**: Get customer balance by branch.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `branches`: Branch to filter by

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/Getcustomerbalance?branches=Main%20Branch" \
  -b cookies.txt
```

**Response**:
```json
{
  "cus_balance": 5000.0
}
```

### 19. Customer View Report

**Endpoint**: `POST /admin/Customerviewreport`

**Description**: Generate customer view report.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `timezone`: Timezone for the report

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/Customerviewreport?timezone=UTC" \
  -b cookies.txt
```

**Response**:
```
base64-encoded-pdf-content
```

## Vendor Management Endpoints

### 20. Get Vendor by ID

**Endpoint**: `GET /admin/GetVendor/{id}`

**Description**: Retrieve specific vendor details by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the vendor

**Example**:
```bash
curl -X GET http://localhost:8000/admin/GetVendor/8fc7528b-c3a2-4b36-a39a-68c13699de80 \
  -b cookies.txt
```

**Response**:
```json
{
  "ven_id": "uuid-string",
  "ven_name": "Vendor Name",
  "ven_phone": "1234567890",
  "ven_address": "Vendor Address",
  "branch": "Main Branch"
}
```

### 21. View Vendors

**Endpoint**: `GET /admin/Viewvendor`

**Description**: View vendors with search and branch filtering.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `search_string`: Search term to filter vendors
- `branches`: Branch to filter by
- `searchphone`: Phone number to filter by
- `searchaddress`: Address to filter by
- `skip`: Number of records to skip (for pagination)
- `limit`: Maximum number of records to return (default 100)

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/Viewvendor?search_string=supplier&branches=Main%20Branch&limit=10" \
  -b cookies.txt
```

**Response**:
```json
[
  {
    "ven_id": "uuid-string",
    "ven_name": "Vendor Name",
    "ven_phone": "1234567890",
    "ven_address": "Vendor Address",
    "branch": "Main Branch"
  }
]
```

### 22. Delete Vendor

**Endpoint**: `POST /admin/Deletevendor/{id}`

**Description**: Delete a vendor by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the vendor to delete

**Example**:
```bash
curl -X POST http://localhost:8000/admin/Deletevendor/8fc7528b-c3a2-4b36-a39a-68c13699de80 \
  -b cookies.txt
```

**Response**:
```json
{
  "success": true,
  "message": "Vendor deleted successfully"
}
```

### 23. Get Vendor Balance

**Endpoint**: `POST /admin/Getvendorbalance`

**Description**: Get vendor balance by branch.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `branches`: Branch to filter by

**Example**:
```bash
curl -X POST "http://localhost:8000/admin/Getvendorbalance?branches=Main%20Branch" \
  -b cookies.txt
```

**Response**:
```json
{
  "cus_balance": 5000.0
}
```

### 24. Vendor View Report

**Endpoint**: `POST /admin/Vendorviewreport`

**Description**: Generate vendor view report.

**Authentication**: Admin role required

**Example**:
```bash
curl -X POST http://localhost:8000/admin/Vendorviewreport \
  -b cookies.txt
```

**Response**:
```
base64-encoded-pdf-content
```

## Salesman Management Endpoints

### 25. Get Salesman by ID

**Endpoint**: `GET /admin/GetSalesman/{id}`

**Description**: Retrieve specific salesman details by ID.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the salesman

**Example**:
```bash
curl -X GET http://localhost:8000/admin/GetSalesman/8fc7528b-c3a2-4b36-a39a-68c13699de80 \
  -b cookies.txt
```

**Response**:
```json
{
  "sal_id": "uuid-string",
  "sal_name": "Salesman Name",
  "sal_phone": "1234567890",
  "sal_address": "Salesman Address",
  "branch": "Main Branch"
}
```

### 26. Create Salesman (Admin)

**Endpoint**: `POST /admin/salesman`

**Description**: Create a new salesman via admin endpoint.

**Authentication**: Admin role required

**Request Body**:
```json
{
  "name": "Salesman Name",
  "code": "SM001",
  "phone": "1234567890",
  "address": "Salesman Address",
  "branch": "Main Branch",
  "commission_rate": 5.0
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/admin/salesman \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "John Doe",
    "code": "SM001",
    "phone": "1234567890",
    "address": "123 Main St",
    "branch": "Main Branch",
    "commission_rate": 5.0
  }'
```

**Response**:
```json
{
  "sal_id": "uuid-string",
  "sal_name": "John Doe",
  "sal_phone": "1234567890",
  "sal_address": "123 Main St",
  "branch": "Main Branch",
  "code": "SM001",
  "commission_rate": "5.0"
}
```

### 27. Update Salesman (Admin)

**Endpoint**: `PUT /admin/salesman/{id}`

**Description**: Update a specific salesman by ID via admin endpoint.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the salesman to update

**Request Body**:
```json
{
  "name": "Updated Name",
  "code": "SM002",
  "phone": "0987654321",
  "address": "456 Oak Ave",
  "branch": "Secondary Branch",
  "commission_rate": 7.0
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/admin/salesman/8fc7528b-c3a2-4b36-a39a-68c13699de80 \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "Updated Name",
    "code": "SM002",
    "phone": "0987654321",
    "address": "456 Oak Ave",
    "branch": "Secondary Branch",
    "commission_rate": 7.0
  }'
```

**Response**:
```json
{
  "sal_id": "uuid-string",
  "sal_name": "Updated Name",
  "sal_phone": "0987654321",
  "sal_address": "456 Oak Ave",
  "branch": "Secondary Branch",
  "code": "SM002",
  "commission_rate": "7.0"
}
```

### 28. Delete Salesman (Admin)

**Endpoint**: `DELETE /admin/salesman/{id}`

**Description**: Delete a specific salesman by ID via admin endpoint.

**Authentication**: Admin role required

**Parameters**:
- `{id}`: UUID of the salesman to delete

**Example**:
```bash
curl -X DELETE http://localhost:8000/admin/salesman/8fc7528b-c3a2-4b36-a39a-68c13699de80 \
  -b cookies.txt
```

**Response**:
```json
{
  "success": true,
  "message": "Salesman deleted successfully"
}
```

## System Management Endpoints

### 29. Get Customer/Vendor by Branch

**Endpoint**: `GET /admin/GetCustomerVendorByBranch`

**Description**: Get salesmen by branch for customer form.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `branch`: Branch to filter by

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/GetCustomerVendorByBranch?branch=Main%20Branch" \
  -b cookies.txt
```

**Response**:
```json
{
  "salesmans": [
    {
      "sal_id": "uuid-string",
      "sal_name": "Salesman Name"
    }
  ]
}
```

### 30. Get Admin Dashboard

**Endpoint**: `GET /admin/`

**Description**: Get admin dashboard overview with key metrics.

**Authentication**: Admin role required

**Example**:
```bash
curl -X GET http://localhost:8000/admin/ \
  -b cookies.txt
```

**Response**:
```json
{
  "summary": {
    "total_users": 10,
    "total_products": 100,
    "total_customers": 50,
    "total_invoices": 200,
    "total_expenses": 25
  },
  "recent_activity": {
    "recent_invoices": ["INV-001", "INV-002"],
    "recent_customers": ["Customer 1", "Customer 2"]
  },
  "last_updated": "2026-02-02T14:45:00.000000"
}
```

### 31. Get Reports

**Endpoint**: `GET /admin/reports`

**Description**: Get various reports for admin.

**Authentication**: Admin role required

**Query Parameters** (optional):
- `report_type`: Type of report (daily, sales, inventory) - default "daily"
- `start_date`: Start date in YYYY-MM-DD format
- `end_date`: End date in YYYY-MM-DD format

**Example**:
```bash
curl -X GET "http://localhost:8000/admin/reports?report_type=sales&start_date=2026-01-01&end_date=2026-01-31" \
  -b cookies.txt
```

**Response**:
```json
{
  "report_type": "sales",
  "period": {
    "start": "2026-01-01T00:00:00",
    "end": "2026-01-31T23:59:59"
  },
  "metrics": {
    "total_revenue": 10000.0,
    "total_invoices": 100,
    "average_invoice_value": 100.0
  }
}
```

### 32. Get Settings

**Endpoint**: `GET /admin/settings`

**Description**: Get admin settings.

**Authentication**: Admin role required

**Example**:
```bash
curl -X GET http://localhost:8000/admin/settings \
  -b cookies.txt
```

**Response**:
```json
{
  "app_version": "1.0.0",
  "database_status": "connected",
  "backup_schedule": "daily at 2 AM",
  "audit_retention_days": 2555,
  "default_timezone": "UTC",
  "features_enabled": {
    "pos_operations": true,
    "inventory_management": true,
    "customer_management": true,
    "reporting": true
  }
}
```

### 33. Update Settings

**Endpoint**: `PUT /admin/settings`

**Description**: Update admin settings.

**Authentication**: Admin role required

**Request Body**:
```json
{
  "backup_schedule": "daily at 3 AM",
  "default_timezone": "US/Eastern"
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/admin/settings \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "backup_schedule": "daily at 3 AM",
    "default_timezone": "US/Eastern"
  }'
```

**Response**:
```json
{
  "message": "Settings updated successfully",
  "updated_fields": ["backup_schedule", "default_timezone"],
  "timestamp": "2026-02-02T14:45:00.000000"
}
```

## CRUD Operations Summary

### Create Operations
- `POST /admin/createadmin` - Create admin user
- `POST /admin/salesman` - Create salesman
- `POST /admin/brand` - Create brand
- `POST /admin/Deleteproduct/{id}` - Delete product (note: this is a POST method despite the name)

### Read Operations
- `GET /admin/getadmin/{id}` - Get admin user
- `GET /admin/viewsalesman` - View salesmen
- `GET /admin/GetProducts/{id}` - Get product
- `GET /admin/Viewproduct` - View products
- `GET /admin/GetCustomer/{id}` - Get customer
- `GET /admin/Viewcustomer` - View customers
- `GET /admin/GetVendor/{id}` - Get vendor
- `GET /admin/Viewvendor` - View vendors
- `GET /admin/GetSalesman/{id}` - Get salesman
- `GET /admin/viewadmins` - View admin users
- `GET /admin/` - Get dashboard
- `GET /admin/reports` - Get reports
- `GET /admin/settings` - Get settings

### Update Operations
- `PUT /admin/updateadmin/{id}` - Update admin user
- `PUT /admin/salesman/{id}` - Update salesman
- `PUT /admin/settings` - Update settings

### Delete Operations
- `POST /admin/deleteadmin/{id}` - Delete admin user
- `DELETE /admin/salesman/{id}` - Delete salesman
- `POST /admin/Deleteproduct/{id}` - Delete product
- `POST /admin/DeleteProductImage/{id}` - Delete product image
- `POST /admin/Deletebrand` - Delete brand
- `POST /admin/Deletecustomer/{id}` - Delete customer
- `POST /admin/Deletevendor/{id}` - Delete vendor

## Role Management
Admin users can create, update, and delete other users and assign different roles (admin, cashier, employee) as needed. Role changes can be performed dynamically using the update admin endpoint:

- Change from admin to cashier: `PUT /admin/updateadmin/{id}?ad_role=cashier`
- Change from cashier to admin: `PUT /admin/updateadmin/{id}?ad_role=admin`
- Change from admin to employee: `PUT /admin/updateadmin/{id}?ad_role=employee`
- Change from employee to admin: `PUT /admin/updateadmin/{id}?ad_role=admin`

Role changes can be performed bidirectionally between admin, cashier, and employee roles as needed for organizational management.

## Compatibility Endpoints

The following endpoints are also available for JavaScript frontend compatibility (capitalized versions):

- `GET /admin/GetAdmin/{id}` - Same as `/admin/getadmin/{id}`
- `POST /admin/DeleteAdmin/{id}` - Same as `/admin/deleteadmin/{id}`
- `GET /admin/GetSalesman/{id}` - Same as `/admin/getsalesman/{id}`
- `GET /admin/ViewSalesman` - Same as `/admin/viewsalesman`
- `GET /admin/ViewAdmins` - Same as `/admin/viewadmins`
- `POST /admin/CreateAdmin` - Same as `/admin/createadmin`
- `PUT /admin/UpdateAdmin/{id}` - Same as `/admin/updateadmin/{id}`
- `GET /admin/GetProducts/{id}` - Same as `/admin/getproducts/{id}`
- `GET /admin/Viewproduct` - Same as `/admin/viewproduct`
- `POST /admin/Deleteproduct/{id}` - Same as `/admin/deleteproduct/{id}`
- `GET /admin/GetCustomer/{id}` - Same as `/admin/getcustomer/{id}`
- `GET /admin/Viewcustomer` - Same as `/admin/viewcustomer`
- `POST /admin/Deletecustomer/{id}` - Same as `/admin/deletecustomer/{id}`
- `GET /admin/GetVendor/{id}` - Same as `/admin/getvendor/{id}`
- `GET /admin/Viewvendor` - Same as `/admin/viewvendor`
- `POST /admin/Deletevendor/{id}` - Same as `/admin/deletevendor/{id}`

## Error Handling

All endpoints return standardized error responses:

```json
{
  "detail": "Human-readable error message"
}
```

Or for more detailed errors:

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

- All endpoints require admin role authentication
- Passwords are never returned in responses
- User data is protected by role-based access control
- Audit logs are maintained for all administrative actions
- Foreign key constraints prevent deletion of users with historical records

## Production Ready Features

- Async/await implementation for high concurrency
- Pydantic v2 validation
- Proper error handling and logging
- Database transaction safety
- JWT token-based authentication
- Role-based access control
- Input sanitization and validation