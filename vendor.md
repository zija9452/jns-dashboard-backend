# Vendor API Requirements Analysis

## Current State
The existing vendor API in the Regal POS Backend provides basic CRUD operations:
- GET /vendors/ - Get list of vendors
- POST /vendors/ - Create a new vendor
- GET /vendors/{id} - Get specific vendor
- PUT /vendors/{id} - Update a vendor
- DELETE /vendors/{id} - Delete a vendor

## Required Fields from JavaScript Code
The JavaScript frontend expects these fields for vendors:
- `ven_name` - Vendor name
- `ven_phone` - Vendor phone
- `ven_address` - Vendor address
- `ven_id` - Vendor ID
- `branch` - Branch assignment

## Missing Endpoints Required by JavaScript Code

### 1. GET `/Admin/GetVendor/{id}`
- **Description**: Retrieve specific vendor details by ID
- **Response**: Vendor object with fields mapped to expected JavaScript properties
- **Required**: Currently missing

### 2. GET `/Admin/Viewvendor`
- **Description**: View vendors with search and branch filtering capabilities
- **Parameters**:
  - `searchString` (optional): Search term for vendor filtering
  - `branches` (optional): Branch filter
  - `searchphone` (optional): Phone number filter
  - `searchaddress` (optional): Address filter
- **Response**: Paginated list of vendors matching criteria
- **Required**: Currently missing

### 3. POST `/Admin/Deletevendor/{id}`
- **Description**: Delete a vendor by ID
- **Response**:
  - `success`: boolean indicating success
  - `message`: success/error message
- **Required**: Currently missing (existing DELETE endpoint returns different format)

### 4. POST `/Admin/Getvendorbalance`
- **Description**: Get vendor balance by branch
- **Request Body**: Branch name
- **Response**:
  - `cus_balance`: Balance amount (note: field name is cus_balance despite being for vendor)
  - `error`: Error message if applicable
- **Required**: Currently missing

### 5. POST `/Admin/Vendorviewreport`
- **Description**: Generate vendor view report
- **Response**: Base64 encoded PDF report
- **Required**: Currently missing

## Field Mapping Requirements

The existing Vendor model fields need to be mapped to JavaScript expected fields:
- `name` → `ven_name`
- `contacts` (JSON) → `ven_phone` (extract phone from contacts JSON)
- `contacts` (JSON) → `ven_address` (extract address from contacts JSON)
- `id` → `ven_id`
- Need to add branch field → `branch`

## Required Enhancements

### 1. Enhanced Vendor Model
- Add branch field to store branch assignment
- Enhance contacts JSON to properly store phone numbers and addresses

### 2. Vendor Balance Tracking
- Implement vendor balance tracking system
- Add endpoints to retrieve vendor balances
- Connect to financial/purchase data to calculate balances

### 3. Advanced Search & Filtering
- Implement search functionality for vendors
- Add branch-based filtering
- Add phone and address search capabilities
- Add pagination support for large datasets

### 4. Report Generation
- Implement vendor report generation
- Support PDF export functionality
- Include reporting capabilities

## Security Considerations
- All endpoints should require appropriate authentication (admin/employee)
- Proper validation of all input parameters
- Sanitize and validate all user inputs
- Prevent unauthorized access to vendor management features

## Implementation Priority
1. **High Priority**: GET `/Admin/GetVendor/{id}`, GET `/Admin/Viewvendor`
2. **Medium Priority**: POST `/Admin/Deletevendor/{id}`, POST `/Admin/Getvendorbalance`
3. **Low Priority**: Report generation functionality