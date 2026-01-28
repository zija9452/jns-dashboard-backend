<!-- SYNC IMPACT REPORT:
Version change: N/A (initial creation) → 1.0.0
Modified principles: None (new creation)
Added sections: All sections added as per requirements
Removed sections: None
Templates requiring updates: ✅ .specify/templates/plan-template.md (to reference new principles)
                             ✅ .specify/templates/spec-template.md (to reference new principles)
                             ✅ .specify/templates/tasks-template.md (to reference new principles)
                             ⚠️ README.md (may need updates to reflect new principles) - pending
Follow-up TODOs: None
-->

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