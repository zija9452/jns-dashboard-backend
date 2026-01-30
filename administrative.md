# Administrative API Endpoints

This document outlines the additional API endpoints needed to support the administrative functionality described in the frontend JavaScript code.

## Required Endpoints

### 1. Admin Management Endpoints

#### GET `/admin/get/{id}`
- **Description**: Retrieve admin user details by ID
- **Parameters**:
  - `id` (path parameter): UUID of the admin user
- **Response**: Admin user object with fields:
  - `ad_id`: User ID
  - `ad_name`: Full name
  - `ad_role`: Role name
  - `ad_phone`: Phone number
  - `ad_address`: Address
  - `ad_password`: Password (hashed, only for internal use)
  - `ad_cnic`: CNIC number
  - `ad_branch`: Branch assignment
- **Authorization**: Admin role required

#### POST `/admin/delete/{id}`
- **Description**: Delete admin user by ID
- **Parameters**:
  - `id` (path parameter): UUID of the admin user to delete
- **Response**:
  - `success`: boolean indicating success
  - `message`: success/error message
- **Authorization**: Admin role required

#### GET `/admin/view-salesman`
- **Description**: View salesman with optional search functionality
- **Parameters**:
  - `searchString` (query parameter, optional): Search term to filter salesman
- **Response**: Paginated list of salesman matching criteria
- **Authorization**: Admin role required

#### GET `/admin/view-admins`
- **Description**: View all admin users with optional search functionality
- **Parameters**:
  - `searchString` (query parameter, optional): Search term to filter admins
- **Response**: Paginated list of admin users matching criteria
- **Authorization**: Admin role required

### 2. Additional Admin Endpoints Needed

#### POST `/admin/create`
- **Description**: Create a new admin user
- **Request Body**:
  - `ad_name`: Full name
  - `ad_role`: Role name
  - `ad_phone`: Phone number
  - `ad_address`: Address
  - `ad_password`: Password
  - `ad_cnic`: CNIC number
  - `ad_branch`: Branch assignment
- **Response**: Created admin user object
- **Authorization**: Admin role required

#### PUT `/admin/update/{id}`
- **Description**: Update admin user details
- **Parameters**:
  - `id` (path parameter): UUID of the admin user to update
- **Request Body**:
  - `ad_name`: Full name (optional)
  - `ad_role`: Role name (optional)
  - `ad_phone`: Phone number (optional)
  - `ad_address`: Address (optional)
  - `ad_password`: Password (optional)
  - `ad_cnic`: CNIC number (optional)
  - `ad_branch`: Branch assignment (optional)
- **Response**: Updated admin user object
- **Authorization**: Admin role required

### 3. Field Mapping

The JavaScript code expects these specific field names in the response objects:
- `ad_id`: User ID
- `ad_name`: User's full name
- `ad_role`: User's role
- `ad_phone`: User's phone number
- `ad_address`: User's address
- `ad_password`: User's password
- `ad_cnic`: User's CNIC number
- `ad_branch`: User's assigned branch
- `ad_branch` (from form): Selected branch from dropdown

### 4. Implementation Notes

1. The current User model has fields like `full_name`, `email`, `username`, `role_id`, etc., but the frontend expects `ad_*` prefixed fields
2. Need to map the existing User model fields to the expected frontend fields
3. The phone, address, CNIC, and branch fields may need to be stored in the `meta` JSON field or require extending the User model
4. Need to implement proper search functionality for salesman and admin views
5. Need to implement soft delete or hard delete for admin users with proper authorization checks

### 5. Security Considerations

- All endpoints require admin authorization
- Proper validation of user inputs
- Sanitize and validate all parameters
- Log administrative actions for audit purposes
- Prevent privilege escalation