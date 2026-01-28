---
id: 1
title: create-project-constitution
stage: constitution
date: 2026-01-28
surface: agent
model: claude-sonnet-4-5-20250929
feature: none
branch: master
user: user
command: /sp.constitution
labels: ["constitution","setup","governance"]
links:
  spec: null
  ticket: null
  adr: null
  pr: null
files:
 - .specify/memory/constitution.md
tests:
 - none
---

## Prompt

 /sp.constitution {
  "project_name": "dashbard-backend",
  "title": "Regal POS-style backend (FastAPI + Python, multi-container, Neon SQL)",
  "description": "Backend only: exact parity with Regal POS admin dashboard. FastAPI (Python), SQLModel + Alembic, multi-container local dev (docker-compose), production-ready notes for Neon (Postgres-compatible). Role-based 'better-auth' (JWT + refresh, bcrypt/2FA hooks). DO NOT include API params/URLs here — API contract will be provided separately.",
  "core_principles": [
    "Exact feature parity with Regal POS admin dashboard (same tabs/fields/flows).",
    "Security-first (RBAC, secure tokens, audit logs).",
    "Containerized & env-driven (local docker-compose, Neon for prod).",
    "Typed models & validation (SQLModel/Pydantic).",
    "Testable & maintainable (pytest, modular routers/services)."
  ],
  "stack": {
    "language": "python >=3.10",
    "framework": "FastAPI",
    "orm": "SQLModel (SQLAlchemy-compatible)",
    "migrations": "Alembic",
    "db": "Neon (Postgres-compatible) (SQL Modal) for prod; postgres container for local dev",
    "auth": "RBAC (Better-auth) with JWT (access+refresh), bcrypt/argon2, optional 2FA hooks",
    "cache_broker": "Redis (sessions, rate-limiting, celery broker)",
    "worker": "Optional (celery or FastAPI background tasks)",
    "proxy": "Nginx or Traefik",
    "containers": "Dockerfiles + docker-compose"
  },
  "roles_and_tabs": {
    "admin": [
      "Dashboard Administration", "Products", "Customers","Vendors", "Salesman", "Stock", "Expenses", "Custom Invoice", "View Custom Order", "Invoice", "Sales View", "Duplicate Bill", "Refund", "Logout"],
    "cashier": ["POS Screen","Quick Sell","Cash Drawer", "Shift Close","Daily Reports", "Duplicate Bill", "Refund", "Logout"],
    "employee": [
"Dashboard", "Products", "Customers", "Vendors", "Salesman", "Stock", "Expenses", "Custom Invoice",  "View Custom Order", "Invoice", "Sales View", "Duplicate Bill", "Refund", "Logout"]
  },
  "domain_models": [
    "User(id, full_name, email, username, password_hash, role_id, is_active, meta, created_at, updated_at)",
    "Role(id, name, permissions)",
    "Product(id, sku, name, desc, unit_price, cost_price, tax_rate, vendor_id, stock_level, attributes, Barcode, Discount, Category, Branch, Limited Qty, Brand Action)",
    "Customer(id, name, contacts, billing_addr, shipping_addr, credit_limit)",
    "Vendor(id, name, contacts, terms)",
    "Salesman(id, name, code, commission_rate)",
    "StockEntry(id, product_id, qty, type(IN/OUT/ADJUST), location, batch, expiry, ref)",
    "Expense(id, type, amount, date, note, created_by)",
    "Invoice(id, invoice_no, customer_id, items, totals, taxes, discounts, status, payments)",
    "CustomOrder(id, fields, status, linked_invoice)",
    "Refund(id, invoice_id, items, amount, reason, processed_by)",
    "AuditLog(entity, action, user_id, changes, timestamp)"
  ],
  "deliverables": [
    "docker-compose.yml (api, redis, worker, nginx, local postgres)",
    "Dockerfiles for api & worker",
    "FastAPI app organized by domain routers (auth, products, customers, vendors, salesman, stock, expenses, invoices, refunds, reports, admin)",
    "SQLModel models + Alembic migrations",
    "Auth module (RBAC, JWT access+refresh, refresh revocation, password hashing)",
    "README (local dev, env vars, Neon notes)",
    "OpenAPI spec / Postman collection (separate artifact)",
    "Unit & integration tests (pytest) and CI example"
  ],
  "constraints": [
    "All persistent data must use SQLModel and be compatible with Neon/Postgres.",
    "Do NOT include API params, endpoint URLs, or full request/response examples inside this constitution.",
    "Match Regal POS fields & flows as closely as possible; provide parity in models and scopes."
  ],
  "api_contract_note": "API parameters, endpoint URLs, request/response schemas, auth header examples, pagination and sample curl requests will be generated as a separate OpenAPI (openapi.yaml) or Postman collection when requested by the user.",
  "next_actio

## Response snapshot

# dashbard-backend Constitution

## Core Principles

### I. Exact Feature Parity
Backend must achieve exact feature parity with Regal POS admin dashboard, including identical tabs, fields, and user flows across all roles (admin, cashier, employee). All UI elements, data structures, and business logic must mirror the existing Regal POS system to ensure seamless transition and user familiarity.

### II. Security-First Architecture
Security is paramount in all system designs. Implement role-based access control (RBAC), secure JWT token management with refresh/revocation, bcrypt password hashing, and comprehensive audit logging. All data access must be authenticated and authorized, with sensitive operations logged for compliance and security monitoring.

### III. Containerized & Environment-Driven Development
System must be fully containerized with docker-compose for local development and designed for production deployment on Neon (PostgreSQL-compatible). Configuration must be environment-driven with no hardcoded values, supporting seamless transitions between local, staging, and production environments.

### IV. Typed Models & Validation
All data models must use SQLModel for type safety and Pydantic for validation. Every API endpoint must validate input/output with strict typing, preventing runtime errors and ensuring data integrity throughout the system lifecycle.

### V. Testable & Maintainable Architecture
Code must be organized in modular, testable components with comprehensive unit and integration tests. Services, routers, and business logic must be decoupled to enable isolated testing and easy maintenance. Follow SOLID principles and dependency injection patterns.

### VI. Production-Ready Operations
System must include observability features (logging, metrics, tracing), health checks, and operational readiness from day one. Include proper error handling, graceful degradation, and monitoring capabilities to support 24/7 operations in production environments.

## Technical Stack Requirements

All implementations must use Python >=3.10 with FastAPI as the web framework. Database interactions must use SQLModel (SQLAlchemy-compatible) with Alembic for migrations, ensuring compatibility with Neon PostgreSQL. Authentication must implement RBAC with JWT tokens, refresh mechanisms, and password hashing. Redis is required for caching, sessions, and rate limiting.

## Domain Model Compliance

All persistent data models must align with the specified domain entities: User, Role, Product, Customer, Vendor, Salesman, StockEntry, Expense, Invoice, CustomOrder, Refund, and AuditLog. Field definitions and relationships must match the specified schema to ensure data consistency with Regal POS requirements.

## Role-Based Access Control

System must implement three distinct user roles with specific permissions: Admin (full dashboard administration), Cashier (POS-focused operations), and Employee (limited administrative functions). Each role must have precisely defined access rights matching the Regal POS role structure.

## Governance

This constitution governs all development activities for the dashbard-backend project. All code changes, architectural decisions, and feature implementations must align with these principles. Deviations require formal amendment procedures with stakeholder approval. Code reviews must verify compliance with all principles before merging. System evolution must maintain backward compatibility where possible and include migration strategies for breaking changes.

**Version**: 1.0.0 | **Ratified**: 2026-01-28 | **Last Amended**: 2026-01-28

## Outcome

- ✅ Impact: Created initial project constitution document with 6 core principles and governance structure
- 🧪 Tests: none
- 📁 Files: Updated .specify/memory/constitution.md
- 🔁 Next prompts: Continue with project setup tasks (models, auth, etc.)
- 🧠 Reflection: Constitution successfully captures all required principles and constraints from user input

## Evaluation notes (flywheel)

- Failure modes observed: none
- Graders run and results (PASS/FAIL): N/A
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): N/A