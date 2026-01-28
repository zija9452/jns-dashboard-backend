---
id: 1
title: create-spec
stage: spec
date: 2026-01-28
surface: agent
model: claude-sonnet-4-5-20250929
feature: regal-pos-backend
branch: 001-regal-pos-backend
user: user
command: /sp.specify
labels: ["specification","backend","regal-pos"]
links:
  spec: specs/001-regal-pos-backend/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/001-regal-pos-backend/spec.md
 - specs/001-regal-pos-backend/checklists/requirements.md
tests:
 - none
---

## Prompt

 /sp.specification {
  "project": "dashboard-backend — backend specification",
  "target_audience": "Backend developers, DevOps engineers, QA",
  "focus": "FastAPI (Python) backend only — multi-container (docker-compose) local/dev setup, SQLModel + Alembic migrations, Neon (Postgres-compatible) for production, Redis for cache/broker, RBAC 'better-auth' (JWT access+refresh, bcrypt/argon2, optional 2FA hooks). Implement exact parity with Regal POS admin/cashier/employee tabs and fields. API contract (OpenAPI/Postman/Markdown) will be delivered separately — do NOT include endpoint params/URLs in this specification.",
  "success_criteria": [
    "All domain models implemented (User/Role/Product/Customer/Vendor/Salesman/StockEntry/Expense/Invoice/CustomOrder/Refund/AuditLog) with SQLModel + migrations.",
    "Role-based access enforced for Admin, Cashier, Employee at endpoint and resource level.",
    "Core endpoints implemented and documented (auth, products, customers, vendors, stock, invoices, refunds, expenses, reports) and covered by unit/integration tests.",
    "Dockerized services + docker-compose to run full stack locally (api, redis, worker, local postgres for dev).",
    "OpenAPI spec (openapi.yaml) or Postman collection produced separately that contains full params, request/response examples, auth headers, pagination and error schema.",
    "Automated tests (pytest) with CI config example; linting and basic type checks included.",
    "Audit logs capture critical actions (invoice creation, refunds, stock adjustments, role changes)."
  ],
  "constraints": [
    "All persistent data must be SQLModel-compatible and work with Neon/Postgres.",
    "Do NOT place API params, endpoint URLs, or full request/response examples inside this /sp.specification command.",
    "Local dev uses postgres container; production uses Neon via env-driven connection string.",
    "Use docker-compose for local multi-container orchestration (no k8s required in this spec)."
  ],
  "not_in_scope": [
    "Frontend UI implementation",
    "Payment gateway integrations (unless requested separately)",
    "Physical POS hardware drivers / integrations",
    "Extensive BI dashboards or analytics UIs (logging/metrics hooks may be included)"
  ],
  "deliverables": [
    "docker-compose.yml (api, redis, worker, local postgres for dev)",
    "Dockerfiles for api & worker",
    "FastAPI app organized by domain routers (auth, products, customers, vendors, salesman, stock, expenses, invoices, refunds, reports, admin)",
    "SQLModel models + Alembic migrations",
    "Auth module (RBAC, JWT access+refresh, refresh revocation, password hashing, 2FA hooks)",
    "OpenAPI spec or Postman collection (provided separately on request)",
    "README with local dev, env vars, and Neon production notes",
    "Unit & integration tests (pytest) and CI example (GitHub Actions)"
  ],
  "acceptance_tests": [
    "Create users for each role and verify permitted/forbidden endpoints.",
    "CRUD product lifecycle + stock adjustments and audit log entries.",
    "Create invoice and refund transactions with proper audit trails."
  ]
}

## Response snapshot

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

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST implement role-based access control (RBAC) with distinct permissions for Admin, Cashier, and Employee roles
- **FR-002**: System MUST authenticate users via JWT tokens with refresh/revocation capabilities and bcrypt password hashing
- **FR-003**: Users MUST be able to perform all functions available in Regal POS system according to their role (Admin, Cashier, Employee)
- **FR-004**: System MUST persist all business data using SQLModel-compatible models that work with Neon/PostgreSQL
- **FR-005**: System MUST log all critical actions (invoice creation, refunds, stock adjustments, role changes) in audit logs
- **FR-006**: System MUST support multi-container deployment via docker-compose for local development
- **FR-007**: System MUST be compatible with Neon PostgreSQL in production while using local PostgreSQL for development
- **FR-008**: System MUST implement all domain models specified: User, Role, Product, Customer, Vendor, Salesman, StockEntry, Expense, Invoice, CustomOrder, Refund, and AuditLog
- **FR-009**: System MUST provide endpoints for all specified business functions: auth, products, customers, vendors, stock, invoices, refunds, expenses, reports
- **FR-010**: System MUST support optional 2FA hooks for enhanced security

### Key Entities *(include if feature involves data)*

- **User**: Represents system users with full_name, email, username, password_hash, role_id, is_active, meta, created_at, updated_at attributes
- **Role**: Defines user permissions with id, name, and permissions attributes that control access to system functions
- **Product**: Business product entity with SKU, name, description, pricing, inventory, and attribute information
- **Customer**: Customer information with name, contact details, billing/shipping addresses, and credit limits
- **Invoice**: Transaction record linking customers to purchased items with totals, taxes, discounts, and payment status
- **StockEntry**: Inventory tracking record with product associations, quantity changes, and location information
- **AuditLog**: System activity record capturing entity changes, user actions, and timestamps for compliance

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can successfully authenticate and access appropriate dashboard functions based on their role within 5 seconds of login
- **SC-002**: System supports at least 100 concurrent users performing various operations without performance degradation
- **SC-003**: All domain models are successfully persisted and retrieved with 99.9% data integrity
- **SC-004**: Audit logs capture 100% of critical actions with appropriate detail for compliance purposes
- **SC-005**: Docker-based deployment completes successfully with all services running within 2 minutes
- **SC-006**: System maintains compatibility with both local PostgreSQL and Neon PostgreSQL without code changes
- **SC-007**: All role-based access controls successfully restrict unauthorized access to 99.9% accuracy

## Outcome

- ✅ Impact: Created comprehensive specification for Regal POS backend with clear user scenarios, functional requirements, and success criteria
- 🧪 Tests: none
- 📁 Files: Created specs/001-regal-pos-backend/spec.md and specs/001-regal-pos-backend/checklists/requirements.md
- 🔁 Next prompts: Proceed to planning phase (/sp.plan) or clarifications (/sp.clarify)
- 🧠 Reflection: Specification covers all required aspects with appropriate role-based access scenarios and measurable success criteria

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A