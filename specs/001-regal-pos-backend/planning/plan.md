# Implementation Plan: Regal POS Backend

**Feature**: Regal POS Backend Clone
**Branch**: 001-regal-pos-backend
**Created**: 2026-01-28
**Status**: Draft

## Technical Context

**Language**: Python 3.10+
**Framework**: FastAPI
**ORM**: SQLModel (SQLAlchemy-compatible)
**Migrations**: Alembic
**Database**: PostgreSQL (Neon-compatible for production, local container for dev)
**Authentication**: JWT with 15-minute access tokens and 30-day refresh tokens with rotation and revocation on logout, role-based access control
**Cache/Broker**: Redis (for sessions, rate-limiting, celery broker)
**Containers**: Docker + docker-compose
**Architecture**: Monolithic API with domain-based routers

**Resolved Unknowns**:
- Product model fields include: id, sku, name, desc, unit_price, cost_price, tax_rate, vendor_id, stock_level, attributes, barcode, discount, category, branch, limited_qty, brand_action
- User model fields include: id, full_name, email, username, password_hash, role_id, is_active, meta, created_at, updated_at
- JWT token lifecycle: 15-minute access tokens, 30-day refresh tokens with rotation and revocation on logout
- Role-based access control matrix defined for admin, cashier, and employee roles
- Database connection strategy supports both local PostgreSQL and Neon PostgreSQL via environment variables
- Docker development environment uses bind mounts for hot-reload and named volumes for persistent data

## Constitution Check

This implementation must comply with the project constitution regarding:

✅ **Exact Feature Parity**: Backend must achieve exact feature parity with Regal POS admin dashboard
✅ **Security-First Architecture**: Implement role-based access control, secure JWT tokens, audit logging
✅ **Containerized & Environment-Driven**: Fully containerized with docker-compose for local development
✅ **Typed Models & Validation**: Use SQLModel for type safety and Pydantic for validation
✅ **Testable & Maintainable**: Modular, testable components with comprehensive tests
✅ **Production-Ready Operations**: Include observability, health checks, and operational readiness

## Gate Evaluations

- [x] **Constitution Compliance**: All constitutional requirements addressed (exact parity, security-first, containerized, typed models, testable architecture)
- [x] **Technical Feasibility**: Architecture supports all required functionality (FastAPI, SQLModel, JWT auth, RBAC, Redis integration)
- [x] **Resource Adequacy**: Available tools/technologies can fulfill requirements (Python 3.10+, FastAPI, SQLModel, Docker, PostgreSQL)
- [x] **Risk Assessment**: Critical risks identified and mitigation strategies in place (token security, database compatibility, cross-platform development)

## Phase 0: Outline & Research

### Completed Research

1. **Field Mapping Research**: Map Regal POS UI fields to backend models - **COMPLETED** (see [research.md](./research.md))
2. **Authentication Patterns**: Best practices for JWT token lifecycle management - **COMPLETED** (see [research.md](./research.md))
3. **Database Connection**: Neon PostgreSQL compatibility considerations - **COMPLETED** (see [research.md](./research.md))
4. **Role-Based Access**: Implementation patterns for admin/cashier/employee permissions - **COMPLETED** (see [research.md](./research.md))

### Outcomes Achieved

- [x] Complete field mapping from Regal POS to backend models
- [x] JWT token lifecycle policy confirmed (15-min access, 30-day refresh with rotation)
- [x] Database connection strategy for Neon/local compatibility
- [x] RBAC matrix defining permissions for each role

## Phase 1: Design & Contracts

### Data Models

- [x] User model with role-based permissions (see [data-model.md](./data-model.md))
- [x] Product model with inventory tracking (see [data-model.md](./data-model.md))
- [x] Customer/Vendor models (see [data-model.md](./data-model.md))
- [x] Invoice/Order models (see [data-model.md](./data-model.md))
- [x] Audit logging model (see [data-model.md](./data-model.md))

### API Contracts

- [x] Authentication endpoints (see [contracts/api-contracts.md](./contracts/api-contracts.md))
- [x] Product management endpoints (see [contracts/api-contracts.md](./contracts/api-contracts.md))
- [x] Customer/Vendor endpoints (see [contracts/api-contracts.md](./contracts/api-contracts.md))
- [x] Invoice/Order endpoints (see [contracts/api-contracts.md](./contracts/api-contracts.md))
- [x] Reporting endpoints (planned in [contracts/api-contracts.md](./contracts/api-contracts.md))

### Infrastructure

- [x] Dockerfile for API service (planned in [quickstart.md](./quickstart.md))
- [x] docker-compose for local development (planned in [quickstart.md](./quickstart.md))
- [x] Alembic migration setup (planned in [quickstart.md](./quickstart.md))
- [x] Redis integration for caching/session management (planned in [quickstart.md](./quickstart.md))

## Phase 2: Implementation

### Core Implementation

- [ ] FastAPI application structure
- [ ] SQLModel database models
- [ ] Authentication and authorization module
- [ ] Domain-specific routers and services

### Testing & Documentation

- [ ] Unit and integration tests
- [ ] API documentation (OpenAPI)
- [ ] Developer setup guide
- [ ] Deployment instructions

## Phase 3: Validation & Delivery

### Quality Assurance

- [ ] End-to-end functionality testing
- [ ] Security validation
- [ ] Performance testing
- [ ] Acceptance criteria verification

### Delivery

- [ ] Production deployment guide
- [ ] Monitoring and logging setup
- [ ] Maintenance runbooks
- [ ] Handover documentation