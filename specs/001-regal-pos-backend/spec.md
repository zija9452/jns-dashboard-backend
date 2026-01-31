# Feature Specification: Regal POS Backend

**Feature Branch**: `001-regal-pos-backend`
**Created**: 2026-01-28
**Status**: Draft
**Input**: User description: "FastAPI (Python) backend only — multi-container (docker-compose) local/dev setup, SQLModel + Alembic migrations, Neon (Postgres-compatible) for production, Redis for cache/broker, RBAC 'better-auth' (JWT access+refresh, bcrypt/argon2, optional 2FA hooks). Implement exact parity with Regal POS admin/cashier/employee tabs and fields. API contract (OpenAPI/Postman/Markdown) will be delivered separately — do NOT include endpoint params/URLs in this specification."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Admin Dashboard Access (Priority: P1)

Admin users need to access the backend system with full administrative privileges to manage products, customers, vendors, salesmen, stock, expenses, invoices, and other administrative functions. They must be able to perform all dashboard administration tasks that match the Regal POS system.

**Why this priority**: This is the foundational user journey that enables core business operations and system management capabilities that all other roles depend on.

**Independent Test**: Can be fully tested by creating an admin user account, authenticating successfully, and verifying access to all administrative dashboard sections including products, customers, vendors, stock management, and reporting functions.

**Acceptance Scenarios**:

1. **Given** an admin user with valid credentials, **When** they log in to the system, **Then** they gain access to all administrative dashboard sections including Dashboard Administration, Products, Customers, Vendors, Salesman, Stock, Expenses, Custom Invoice, View Custom Order, Invoice, Sales View, Duplicate Bill, Refund, and Logout.

2. **Given** an admin user is logged in, **When** they navigate to any administrative section, **Then** they can perform all CRUD operations available in the Regal POS system for that section.

---

### User Story 2 - Cashier POS Operations (Priority: P2)

Cashier users need access to POS-focused operations including POS Screen, Quick Sell, Cash Drawer, Shift Close, Daily Reports, Duplicate Bill, and Refund functions. They should have limited access compared to admins but full functionality for daily transaction processing.

**Why this priority**: Critical for daily business operations allowing staff to process sales and handle transactions efficiently.

**Independent Test**: Can be fully tested by creating a cashier user account, authenticating successfully, and verifying access only to cashier-specific functions while being restricted from administrative functions.

**Acceptance Scenarios**:

1. **Given** a cashier user with valid credentials, **When** they log in to the system, **Then** they gain access to POS Screen, Quick Sell, Cash Drawer, Shift Close, Daily Reports, Duplicate Bill, Refund, and Logout functions.

2. **Given** a cashier user is logged in, **When** they attempt to access administrative functions, **Then** they are denied access to those sections.

---

### User Story 3 - Employee General Access (Priority: P3)

Employee users need access to most system functions similar to admin but with limited administrative privileges. They should be able to view and interact with products, customers, vendors, stock, and other business data while having restricted administrative capabilities.

**Why this priority**: Enables staff members to perform their duties with appropriate access levels without full admin privileges.

**Independent Test**: Can be fully tested by creating an employee user account, authenticating successfully, and verifying access to employee-appropriate functions while being restricted from certain administrative functions.

**Acceptance Scenarios**:

1. **Given** an employee user with valid credentials, **When** they log in to the system, **Then** they gain access to Dashboard, Products, Customers, Vendors, Salesman, Stock, Expenses, Custom Invoice, View Custom Order, Invoice, Sales View, Duplicate Bill, Refund, and Logout functions.

2. **Given** an employee user is logged in, **When** they attempt to access highly sensitive administrative functions, **Then** they are appropriately restricted based on their role permissions.

---

### Edge Cases

- What happens when a user attempts to access resources without proper role permissions?
- How does system handle expired JWT tokens during long operations?
- What occurs when database connections fail during critical transactions?
- How does the system handle concurrent stock adjustments to prevent race conditions?
- What happens when audit logging fails during critical operations?
- How does the system handle instant logout when browser window is closed?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement role-based access control (RBAC) with distinct permissions for Admin, Cashier, and Employee roles
- **FR-002**: System MUST authenticate users via JWT tokens with 15-minute access tokens and 30-day refresh tokens with rotation and revocation on logout
- **FR-003**: Users MUST be able to perform all functions available in Regal POS system according to their role (Admin, Cashier, Employee)
- **FR-004**: System MUST persist all business data using SQLModel-compatible models that work with Neon/PostgreSQL
- **FR-005**: System MUST log all critical actions (invoice creation, refunds, stock adjustments, role changes) in audit logs with 7-year retention policy
- **FR-006**: System MUST support multi-container deployment via docker-compose for local development
- **FR-007**: System MUST be compatible with Neon PostgreSQL in production while using local PostgreSQL for development
- **FR-008**: System MUST implement all domain models specified: User, Role, Product (with SKU, name, price, cost, barcode, category, brand, stock quantity, and standard validation), Customer, Vendor, Salesman, StockEntry, Expense, Invoice, CustomOrder, Refund, and AuditLog
- **FR-009**: System MUST provide endpoints for all specified business functions: auth, products, customers, vendors, stock, invoices, refunds, expenses, reports
- **FR-010**: System MUST support future biometric authentication (thumb scanning) implementation for employee login
- **FR-011**: System MUST support pagination with default 50 items per page and maximum 200 items per page
- **FR-012**: System MUST implement instant logout when browser window is closed
- **FR-013**: System MUST provide endpoints with configurable pagination limits for frontend flexibility
- **FR-014**: System MUST implement asynchronous operations using async/await patterns for improved performance and scalability with high-concurrency POS operations

### Key Entities *(include if feature involves data)*

- **User**: Represents system users with full_name, email, username, password_hash, role_id, is_active, meta, created_at, updated_at attributes
- **Role**: Defines user permissions with id, name, and permissions attributes that control access to system functions
- **Product**: Business product entity with SKU, name, price, cost, barcode, category, brand, stock quantity, description, unit_price, cost_price, tax_rate, vendor_id, stock_level, and attribute information with appropriate validation
- **Customer**: Customer information with name, contact details, billing/shipping addresses, and credit limits
- **Invoice**: Transaction record linking customers to purchased items with totals, taxes, discounts, and payment status
- **StockEntry**: Inventory tracking record with product associations, quantity changes, and location information
- **AuditLog**: System activity record capturing entity changes, user actions, and timestamps for compliance with 7-year retention policy

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully authenticate and access appropriate dashboard functions based on their role within 5 seconds of login
- **SC-002**: System supports at least 100 concurrent users performing various operations without performance degradation
- **SC-003**: All domain models are successfully persisted and retrieved with 99.9% data integrity
- **SC-004**: Audit logs capture 100% of critical actions with appropriate detail for compliance purposes and retain for 7 years
- **SC-005**: Docker-based deployment completes successfully with all services running within 2 minutes
- **SC-006**: System maintains compatibility with both local PostgreSQL and Neon PostgreSQL without code changes
- **SC-007**: All role-based access controls successfully restrict unauthorized access to 99.9% accuracy
- **SC-008**: Pagination works consistently across all collection endpoints with configurable limits (default 50, max 200)

## Clarifications

### Session 2026-01-28

- Q: What should be the JWT token expiration policy? → A: Access token = 15 minutes, Refresh token = 30 days with rotation and revocation on logout
- Q: What specific fields and validation should be applied to the Product entity? → A: Basic fields: SKU, name, price, cost, barcode, category, brand, stock quantity with standard validation
- Q: Which method should be used for two-factor authentication? → A: Future biometric authentication (thumb scanning) for employee login, no current 2FA implementation
- Q: How long should audit logs be retained for compliance? → A: 7 years retention for financial records and critical actions
- Q: What should be the default pagination settings for API endpoints? → A: Default: 50 items per page, Maximum: 200 items per page