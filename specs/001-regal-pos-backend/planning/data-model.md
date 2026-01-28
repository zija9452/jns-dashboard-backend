# Data Model: Regal POS Backend

**Date**: 2026-01-28
**Feature**: Regal POS Backend Clone

## Entity Relationships

```
User (1) -> (n) Role
User (1) -> (n) Invoice
Product (1) -> (n) StockEntry
Product (1) -> (n) InvoiceItem
Customer (1) -> (n) Invoice
Vendor (1) -> (n) Product
Salesman (1) -> (n) Invoice
Invoice (1) -> (n) Refund
AuditLog (n) -> (various entities)
```

## Entity Definitions

### User
**Purpose**: System users with role-based permissions
**Fields**:
- id: UUID (primary key)
- full_name: String (required, max 100 chars)
- email: String (required, unique, valid email format)
- username: String (required, unique, 3-30 chars)
- password_hash: String (required, bcrypt hash)
- role_id: UUID (foreign key to Role)
- is_active: Boolean (default: true)
- meta: JSON (optional, for extensibility)
- created_at: DateTime (auto-generated)
- updated_at: DateTime (auto-generated, updated on change)

**Validation**:
- Email must be unique and valid
- Username must be 3-30 alphanumeric chars with underscores/hyphens
- Password must meet strength requirements when set

### Role
**Purpose**: Defines user permissions and access levels
**Fields**:
- id: UUID (primary key)
- name: String (required, unique, admin/cashier/employee)
- permissions: JSON (role-specific permissions)
- created_at: DateTime (auto-generated)

**Validation**:
- Name must be one of: 'admin', 'cashier', 'employee'

### Product
**Purpose**: Business product catalog items
**Fields**:
- id: UUID (primary key)
- sku: String (required, unique, max 50 chars)
- name: String (required, max 100 chars)
- desc: Text (optional, product description)
- unit_price: Decimal (required, positive, precision: 10,2)
- cost_price: Decimal (required, positive, precision: 10,2)
- tax_rate: Decimal (optional, default: 0.00)
- vendor_id: UUID (foreign key to Vendor, optional)
- stock_level: Integer (required, default: 0)
- attributes: JSON (optional, for extensibility)
- barcode: String (optional, unique, max 50 chars)
- discount: Decimal (optional, default: 0.00)
- category: String (optional, max 50 chars)
- branch: String (optional, max 50 chars)
- limited_qty: Boolean (optional, default: false)
- brand_action: String (optional, max 100 chars)
- created_at: DateTime (auto-generated)
- updated_at: DateTime (auto-generated, updated on change)

**Validation**:
- SKU must be unique
- Prices must be positive
- Stock level must be non-negative

### Customer
**Purpose**: Business customer information
**Fields**:
- id: UUID (primary key)
- name: String (required, max 100 chars)
- contacts: JSON (required, phone, email, etc.)
- billing_addr: JSON (optional, address structure)
- shipping_addr: JSON (optional, address structure)
- credit_limit: Decimal (optional, default: 0.00)
- created_at: DateTime (auto-generated)
- updated_at: DateTime (auto-generated, updated on change)

**Validation**:
- Name required
- Contacts must contain at least one contact method

### Vendor
**Purpose**: Product suppliers/vendors
**Fields**:
- id: UUID (primary key)
- name: String (required, max 100 chars)
- contacts: JSON (required, phone, email, address)
- terms: JSON (optional, payment terms, etc.)
- created_at: DateTime (auto-generated)
- updated_at: DateTime (auto-generated, updated on change)

### Salesman
**Purpose**: Sales personnel tracking
**Fields**:
- id: UUID (primary key)
- name: String (required, max 100 chars)
- code: String (required, unique, max 20 chars)
- commission_rate: Decimal (optional, default: 0.00)
- created_at: DateTime (auto-generated)
- updated_at: DateTime (auto-generated, updated on change)

**Validation**:
- Code must be unique

### StockEntry
**Purpose**: Inventory tracking system
**Fields**:
- id: UUID (primary key)
- product_id: UUID (foreign key to Product, required)
- qty: Integer (required, positive/negative based on type)
- type: String (required, enum: IN, OUT, ADJUST)
- location: String (optional, max 100 chars)
- batch: String (optional, max 50 chars)
- expiry: Date (optional)
- ref: String (optional, reference to transaction)
- created_at: DateTime (auto-generated)

**Validation**:
- Quantity must be non-zero
- Type must be one of: IN, OUT, ADJUST

### Expense
**Purpose**: Business expense tracking
**Fields**:
- id: UUID (primary key)
- type: String (required, max 50 chars)
- amount: Decimal (required, positive, precision: 10,2)
- date: Date (required, default: today)
- note: Text (optional)
- created_by: UUID (foreign key to User, required)
- created_at: DateTime (auto-generated)

### Invoice
**Purpose**: Sales transaction records
**Fields**:
- id: UUID (primary key)
- invoice_no: String (required, unique, auto-generated)
- customer_id: UUID (foreign key to Customer, required)
- items: JSON (required, line items with quantities/prices)
- totals: JSON (calculated, subtotal, tax, total)
- taxes: Decimal (calculated, total tax amount)
- discounts: Decimal (optional, applied discount)
- status: String (required, enum: draft, issued, paid, cancelled)
- payments: JSON (payment records)
- created_at: DateTime (auto-generated)
- updated_at: DateTime (auto-generated, updated on change)

**Validation**:
- Invoice number must be unique
- Status must be one of: draft, issued, paid, cancelled

### CustomOrder
**Purpose**: Custom orders that may link to invoices
**Fields**:
- id: UUID (primary key)
- fields: JSON (required, custom order data)
- status: String (required, enum: pending, in_progress, completed, cancelled)
- linked_invoice: UUID (foreign key to Invoice, optional)
- created_at: DateTime (auto-generated)
- updated_at: DateTime (auto-generated, updated on change)

### Refund
**Purpose**: Transaction refund records
**Fields**:
- id: UUID (primary key)
- invoice_id: UUID (foreign key to Invoice, required)
- items: JSON (required, refunded items)
- amount: Decimal (required, positive, precision: 10,2)
- reason: Text (required)
- processed_by: UUID (foreign key to User, required)
- created_at: DateTime (auto-generated)

### AuditLog
**Purpose**: System activity tracking for compliance
**Fields**:
- id: UUID (primary key)
- entity: String (required, name of affected entity)
- action: String (required, CREATE, UPDATE, DELETE, ACCESS)
- user_id: UUID (foreign key to User, optional for system actions)
- changes: JSON (detailed changes made)
- timestamp: DateTime (auto-generated)

**Retention Policy**: 7 years as per specification