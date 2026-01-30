# Customer API Requirements Analysis

## Current State
The existing customer API in the Regal POS Backend provides basic CRUD operations:
- GET /customers/ - Get list of customers
- POST /customers/ - Create a new customer
- GET /customers/{id} - Get specific customer
- PUT /customers/{id} - Update a customer
- DELETE /customers/{id} - Delete a customer

## Required Fields from JavaScript Code
The JavaScript frontend expects these fields for customers:
- `cus_name` - Customer name
- `cus_phone` - Customer phone
- `cus_cnic` - Customer CNIC
- `cus_address` - Customer address
- `cus_balance` - Customer balance
- `cus_sal_id_fk` - Salesman ID (foreign key)
- `cus_id` - Customer ID
- `branch` - Branch assignment

## Missing Endpoints Required by JavaScript Code

### 1. GET `/Admin/GetCustomer/{id}`
- **Description**: Retrieve specific customer details by ID
- **Response**: Customer object with fields mapped to expected JavaScript properties
- **Required**: Currently missing

### 2. GET `/Admin/Viewcustomer`
- **Description**: View customers with search and branch filtering capabilities
- **Parameters**:
  - `searchString` (optional): Search term for customer filtering
  - `branches` (optional): Branch filter
  - `searchphone` (optional): Phone number filter
  - `searchaddress` (optional): Address filter
- **Response**: Paginated list of customers matching criteria
- **Required**: Currently missing

### 3. POST `/Admin/Deletecustomer/{id}`
- **Description**: Delete a customer by ID
- **Response**:
  - `success`: boolean indicating success
  - `message`: success/error message
- **Required**: Currently missing (existing DELETE endpoint returns different format)

### 4. POST `/Admin/Getcustomerbalance`
- **Description**: Get customer balance by branch
- **Request Body**: Branch name
- **Response**:
  - `cus_balance`: Balance amount
  - `error`: Error message if applicable
- **Required**: Currently missing

### 5. GET `/Admin/Customerviewreport`
- **Description**: Generate customer view report
- **Request Body**: Timezone information
- **Response**: Base64 encoded PDF report
- **Required**: Currently missing

### 6. GET `/Admin/GetCustomerVendorByBranch`
- **Description**: Get customers and salesmen by branch
- **Parameters**:
  - `branch`: Branch name to filter by
- **Response**:
  - `salesmans`: Array of salesman objects with `sal_id` and `sal_name`
- **Required**: Currently missing

## Field Mapping Requirements

The existing Customer model fields need to be mapped to JavaScript expected fields:
- `name` → `cus_name`
- `contacts` (JSON) → `cus_phone` (extract phone from contacts JSON)
- `billing_addr` or `shipping_addr` (JSON) → `cus_address` (extract address from JSON)
- `id` → `cus_id`
- `created_at` or other field → `cus_balance` (may need additional balance tracking field)
- Need to add salesman relationship field → `cus_sal_id_fk`
- Need to add branch field → `branch`

## Required Enhancements

### 1. Enhanced Customer Model
- Add branch field to store branch assignment
- Add salesman relationship field
- Add balance tracking capability
- Enhance contacts JSON to properly store phone numbers
- Enhance address JSON to properly store addresses

### 2. Customer Balance Tracking
- Implement customer balance tracking system
- Add endpoints to retrieve customer balances
- Connect to financial/invoice data to calculate balances

### 3. Advanced Search & Filtering
- Implement search functionality for customers
- Add branch-based filtering
- Add phone and address search capabilities
- Add pagination support for large datasets

### 4. Report Generation
- Implement customer report generation
- Support PDF export functionality
- Include timezone-aware reporting

### 5. Relationship Management
- Implement proper salesman-customer relationships
- Add foreign key constraints where appropriate
- Create proper joins for related data

## Security Considerations
- All endpoints should require appropriate authentication (admin/cashier/employee)
- Proper validation of all input parameters
- Sanitize and validate all user inputs
- Prevent unauthorized access to customer management features

## Implementation Priority
1. **High Priority**: GET `/Admin/GetCustomer/{id}`, GET `/Admin/Viewcustomer`
2. **Medium Priority**: POST `/Admin/Deletecustomer/{id}`, POST `/Admin/Getcustomerbalance`
3. **Low Priority**: Report generation, advanced relationship management