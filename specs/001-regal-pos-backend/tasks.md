# Task List: Regal POS Backend

**Feature**: Regal POS Backend Clone
**Branch**: 001-regal-pos-backend
**Created**: 2026-01-28
**Status**: Draft

## Implementation Strategy

Build an MVP with User Story 1 (Admin Dashboard Access) first, then incrementally add other user stories. Each user story should be independently testable and deliver value.

## Phase 1: Setup

### Goal
Initialize project structure and foundational components needed by all user stories.

### Independent Test
Project can be built and basic health check passes.

### Tasks

- [X] T001 Create project directory structure (src/, tests/, docs/, docker/, etc.)
- [X] T002 Initialize Python project with requirements.txt including FastAPI, SQLModel, Alembic, Redis, PyJWT
- [X] T003 Create initial Dockerfile for API service
- [X] T004 Create docker-compose.yml with services: api, postgres, redis
- [X] T005 Configure development environment with .env, .gitignore, .dockerignore
- [X] T006 Set up basic FastAPI application structure with main.py and routers directory

## Phase 2: Foundational Components

### Goal
Implement shared components that block all user stories: authentication, database, and core models.

### Independent Test
Database connectivity works, authentication module functions, and core models can be created/queried.

### Tasks

- [X] T007 Implement database configuration with SQLModel and asyncpg
- [X] T008 Set up Alembic for database migrations
- [X] T009 Create JWT authentication module with token creation/verification
- [X] T010 Implement refresh token rotation and revocation mechanism
- [X] T011 Create base model classes and database session management
- [X] T012 Implement role-based access control (RBAC) decorators
- [X] T013 Create audit logging utility functions

## Phase 3: User Story 1 - Admin Dashboard Access (P1)

### Goal
Enable admin users to access the backend system with full administrative privileges to manage products, customers, vendors, salesmen, stock, expenses, invoices, and other administrative functions.

### User Story Priority
P1 - This is the foundational user journey that enables core business operations and system management capabilities that all other roles depend on.

### Independent Test
Can create an admin user account, authenticate successfully, and verify access to all administrative dashboard sections including products, customers, vendors, stock management, and reporting functions.

### Tasks

- [X] T014 [P] [US1] Create User model with full_name, email, username, password_hash, role_id, is_active, meta, created_at, updated_at
- [X] T015 [P] [US1] Create Role model with id, name, and permissions attributes
- [X] T016 [P] [US1] Create Product model with SKU, name, price, cost, barcode, category, brand, stock_quantity, and validation
- [X] T017 [P] [US1] Create Customer model with name, contact details, billing/shipping addresses, and credit limits
- [X] T018 [P] [US1] Create Vendor model with name, contact details, and terms
- [X] T019 [P] [US1] Create Salesman model with name, code, and commission_rate
- [X] T020 [P] [US1] Create StockEntry model for inventory tracking
- [X] T021 [P] [US1] Create Expense model for expense tracking
- [X] T022 [P] [US1] Create Invoice model for transaction records
- [X] T023 [P] [US1] Create CustomOrder model for custom orders
- [X] T024 [P] [US1] Create Refund model for refund records
- [X] T025 [P] [US1] Create AuditLog model for system activity tracking
- [X] T026 [US1] Create UserService for user management operations
- [X] T027 [US1] Create ProductService for product management operations
- [X] T028 [US1] Create CustomerService for customer management operations
- [X] T029 [US1] Create VendorService for vendor management operations
- [X] T030 [US1] Create SalesmanService for salesman management operations
- [X] T031 [US1] Create StockService for inventory management operations
- [X] T032 [US1] Create ExpenseService for expense management operations
- [X] T033 [US1] Create InvoiceService for invoice management operations
- [X] T034 [US1] Create CustomOrderService for custom order operations
- [X] T035 [US1] Create RefundService for refund operations
- [X] T036 [US1] Implement authentication endpoints (login, refresh, logout)
- [X] T037 [US1] Implement user management endpoints (CRUD operations)
- [X] T038 [US1] Implement product management endpoints (CRUD operations)
- [X] T039 [US1] Implement customer management endpoints (CRUD operations)
- [X] T040 [US1] Implement vendor management endpoints (CRUD operations)
- [X] T041 [US1] Implement salesman management endpoints (CRUD operations)
- [X] T042 [US1] Implement stock management endpoints (CRUD operations)
- [X] T043 [US1] Implement expense management endpoints (CRUD operations)
- [X] T044 [US1] Implement invoice management endpoints (CRUD operations)
- [X] T045 [US1] Implement custom order endpoints (CRUD operations)
- [X] T046 [US1] Implement refund endpoints (CRUD operations)
- [X] T047 [US1] Implement admin dashboard endpoints for all administrative functions
- [X] T048 [US1] Implement role-based access controls for admin functions

## Phase 4: User Story 2 - Cashier POS Operations (P2)

### Goal
Enable cashier users to access POS-focused operations including POS Screen, Quick Sell, Cash Drawer, Shift Close, Daily Reports, Duplicate Bill, and Refund functions with limited access compared to admins.

### User Story Priority
P2 - Critical for daily business operations allowing staff to process sales and handle transactions efficiently.

### Independent Test
Can create a cashier user account, authenticate successfully, and verify access only to cashier-specific functions while being restricted from administrative functions.

### Tasks

- [X] T049 [US2] Create POS-specific endpoints for cashier operations
- [X] T050 [US2] Implement Quick Sell functionality for cashier users
- [X] T051 [US2] Implement Cash Drawer operations for cashier users
- [X] T052 [US2] Implement Shift Close functionality for cashier users
- [X] T053 [US2] Implement Daily Reports generation for cashier users
- [X] T054 [US2] Implement Duplicate Bill functionality for cashier users
- [X] T055 [US2] Implement role-based access controls for cashier functions
- [X] T056 [US2] Restrict cashier access to administrative functions

## Phase 5: User Story 3 - Employee General Access (P3)

### Goal
Enable employee users to access most system functions similar to admin but with limited administrative privileges to view and interact with products, customers, vendors, stock, and other business data.

### User Story Priority
P3 - Enables staff members to perform their duties with appropriate access levels without full admin privileges.

### Independent Test
Can create an employee user account, authenticate successfully, and verify access to employee-appropriate functions while being restricted from certain administrative functions.

### Tasks

- [X] T057 [US3] Implement role-based access controls for employee functions
- [X] T058 [US3] Allow employee access to most functions except highly sensitive administrative functions
- [X] T059 [US3] Implement appropriate restrictions for employee role on administrative functions

## Phase 6: API Documentation and Testing

### Goal
Generate API documentation and implement comprehensive tests for all functionality.

### Independent Test
OpenAPI specification is available and comprehensive tests pass.

### Tasks

- [X] T060 Create OpenAPI specification (openapi.yaml) with all endpoints
- [X] T061 Write unit tests for all models
- [X] T062 Write unit tests for all services
- [X] T063 Write integration tests for authentication flows
- [X] T064 Write integration tests for all user stories
- [X] T065 Write end-to-end tests for critical user journeys
- [X] T066 Implement test coverage reporting

## Phase 7: Polish & Cross-Cutting Concerns

### Goal
Finalize the implementation with production readiness features and documentation.

### Independent Test
Application is production-ready with proper documentation, configuration, and deployment setup.

### Tasks

- [X] T067 Implement proper error handling and logging
- [X] T068 Add input validation and sanitization
- [X] T069 Implement rate limiting for authentication endpoints
- [X] T070 Add health check endpoints
- [X] T071 Create comprehensive README with setup instructions
- [X] T072 Document Neon deployment configuration
- [X] T073 Create deployment guides for different environments
- [X] T074 Optimize database queries and add indexes
- [X] T075 Perform security review and add security headers
- [X] T076 Create backup and migration runbook
- [X] T077 Update audit log retention policy implementation to 7 years
- [X] T078 Add pagination support with default 50/max 200 items per page
- [X] T079 Standardize async patterns across all service files
- [X] T080 Fix middleware to properly handle async operations
- [X] T081 Test concurrent request handling for async performance
- [X] T082 Update documentation to reflect async implementation

## Dependencies

### User Story Completion Order
1. User Story 1 (Admin Dashboard Access) - Foundation for all other roles
2. User Story 2 (Cashier POS Operations) - Dependent on authentication and basic models
3. User Story 3 (Employee General Access) - Dependent on authentication and role system

### Critical Path
T001 → T002 → T007 → T009 → T014-T025 (models) → T036 (auth endpoints) → T047 (admin endpoints) → T049 (cashier endpoints) → T057 (employee access)

## Parallel Execution Opportunities

- **Model Creation (T014-T025)**: All models can be created in parallel [P] tags indicated
- **Service Implementation (T026-T035)**: Services can be developed in parallel after models are created
- **Endpoint Implementation (T036-T059)**: Endpoints can be developed in parallel after services are implemented

## Acceptance Criteria

- All domain models implemented and accessible via Alembic migrations
- Authentication flows work with JWT tokens and role-based access
- Admin users can access all dashboard functions
- Cashier users can access POS functions but not admin functions
- Employee users can access appropriate functions with limited admin access
- Docker-based deployment works with hot-reload in development
- OpenAPI spec is available and importable into tools like Swagger UI
- Comprehensive tests pass for all functionality
- Audit logs capture all critical actions with 7-year retention