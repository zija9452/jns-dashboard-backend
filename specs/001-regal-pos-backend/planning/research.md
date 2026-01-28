# Research Findings: Regal POS Backend Implementation

**Date**: 2026-01-28
**Feature**: Regal POS Backend Clone

## Field Mapping Research

### Decision: Product Model Fields
**Rationale**: Based on the constitution and specification, the Product model should include all fields mentioned in the domain models section to ensure exact parity with Regal POS.

**Fields Identified**:
- Basic: id, sku, name, desc
- Pricing: unit_price, cost_price, tax_rate
- Inventory: vendor_id, stock_level
- Attributes: attributes, Barcode, Discount, Category, Branch, Limited Qty, Brand Action

**Alternatives Considered**:
- Minimal product model (name, price only) - rejected as insufficient for POS functionality
- Extended product model with supplier chain data - deemed unnecessary for initial implementation

### Decision: User Model Fields
**Rationale**: Following standard authentication patterns with role-based access for the three required user types (admin, cashier, employee).

**Fields Identified**:
- id, full_name, email, username, password_hash, role_id, is_active, meta, created_at, updated_at

**Alternatives Considered**:
- Simplified user model without role_id - rejected as role-based access is required
- Expanded user model with extensive profile data - deemed unnecessary for core POS functionality

## Authentication Patterns

### Decision: JWT Token Lifecycle
**Rationale**: Based on clarifications from the specification phase, implementing 15-minute access tokens with 30-day refresh tokens that rotate on refresh and revoke on logout.

**Configuration**:
- Access token: 15 minutes TTL
- Refresh token: 30 days TTL with rotation
- Storage: In-memory revocation list for refresh tokens
- Security: Secure HTTP-only cookies in production, headers for development

**Alternatives Considered**:
- Longer access tokens (1 hour) - rejected for security reasons
- Session-based authentication - rejected as JWT was specified
- Shorter refresh tokens (7 days) - rejected as it would inconvenience users

## Database Connection Strategy

### Decision: Neon-Compatible PostgreSQL Setup
**Rationale**: Ensuring compatibility with both local development and production Neon PostgreSQL through environment-driven configuration.

**Implementation**:
- Use asyncpg with SQLAlchemy/SQLModel
- Environment variables for connection strings
- Connection pooling with configurable limits
- Alembic for database migrations

**Alternatives Considered**:
- Separate database technologies for dev/prod - rejected for complexity
- ORM-specific connection handling - SQLModel already provides this
- Connection pooling via external tools (PgBouncer) - deferred to production deployment

## Role-Based Access Control

### Decision: Role Matrix Implementation
**Rationale**: Defining clear permissions for admin, cashier, and employee roles based on Regal POS functionality.

**Permissions Matrix**:
- **Admin**: Full access to all dashboard sections (Administration, Products, Customers, Vendors, Salesman, Stock, Expenses, Custom Invoice, View Custom Order, Invoice, Sales View, Duplicate Bill, Refund)
- **Cashier**: POS Screen, Quick Sell, Cash Drawer, Shift Close, Daily Reports, Duplicate Bill, Refund
- **Employee**: Same as admin but with limited administrative functions

**Alternatives Considered**:
- Simple yes/no permissions - insufficient granularity
- Attribute-based access control - overkill for this use case
- Permission inheritance - already covered by role definitions

## Docker & Containerization

### Decision: Development Container Strategy
**Rationale**: Supporting hot-reload development with persistent data storage using named volumes.

**Configuration**:
- docker-compose with services: api, redis, postgres (dev), nginx (optional)
- Bind mounts for code with :delegated flag on macOS
- Named volumes for database persistence
- Separate build vs image strategies for dev/prod

**Alternatives Considered**:
- Single container approach - insufficient for realistic POS system
- Direct host mounting for DB - risky for data persistence
- Kubernetes for local dev - overkill for development environment