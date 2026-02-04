Complete Customer Invoice Management System Documentation

  Overview                                                                                                                                                                                           
  A comprehensive customer invoice system supporting immediate sales, custom orders with work-in-progress tracking, partial payments, and detailed reporting.                                        
  Core Features

  - Simple invoice numbering: CIN-001, CIN-002, etc. (as implemented)
  - Work-in-progress tracking: Custom orders with status progression
  - Partial payment support: Handle multiple payments for one order
  - Customer balance tracking: Aggregate balances across all orders
  - Daily collection reporting: Track payments by date
  - Order management: Navigate from customer → orders → specific order

  Database Models

  CustomerInvoice Model

  class CustomerInvoice(SQLModel, table=True):
      id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
      invoice_no: str = Field(unique=True)  # Auto-generated as CIN-001, CIN-002
      customer_id: uuid.UUID = Field(foreign_key="customers.id")
      salesman_id: Optional[uuid.UUID] = Field(default=None, foreign_key="salesmen.id")
      items: str = Field()  # JSON string for line items
      totals: str = Field()  # JSON string for subtotal, tax, total
      total_amount: Decimal = Field(sa_column=Column(Numeric(10, 2)))  # Total order amount
      amount_paid: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))  # Amount received so far
      balance_due: Decimal = Field(default=0.00, sa_column=Column(Numeric(10, 2)))  # Remaining balance
      payment_status: str = Field(default="unpaid")  # "unpaid", "partial", "paid"
      payments_history: str = Field(default="[]")  # JSON array of payment records
      status: CustomerInvoiceStatus = Field(default=CustomerInvoiceStatus.ISSUED)  # DRAFT, ISSUED, PAID, CANCELLED
      payment_method: str = Field(default="cash")  # Primary payment method
      notes: Optional[str] = Field(default=None)
      created_by: uuid.UUID = Field(foreign_key="users.id")
      created_at: datetime = Field(default_factory=datetime.now)
      updated_at: datetime = Field(default_factory=datetime.now)

  API Endpoints

  1. Create Customer Invoice

  - Endpoint: POST /customer-invoice/SaveCustomerOrders
  - Functionality: Creates a new customer invoice with simple numbering (CIN-001, CIN-002)
  - Response: Base64-encoded PDF receipt
  - Status: Sets to ISSUED initially

  2. Get Customer Balance

  - Endpoint: GET /customer-invoice/get-customer-balance/{customer_id}
  - Functionality: Shows total outstanding balance across all orders for a customer
  - Response:
  {
    "customer_id": "uuid",
    "customer_name": "string",
    "total_balance": "decimal",
    "total_orders": "integer",
    "orders": [
      {
        "order_id": "uuid",
        "invoice_no": "CIN-001",
        "order_total": "decimal",
        "amount_paid": "decimal",
        "balance_due": "decimal",
        "status": "unpaid/partial/paid",
        "created_date": "datetime"
      }
    ]
  }

  3. Get Customer Orders

  - Endpoint: GET /customer-invoice/get-customer-orders/{customer_id}
  - Functionality: Lists all orders for a specific customer
  - Response:
  {
    "customer_id": "uuid",
    "customer_name": "string",
    "orders": [
      {
        "order_id": "uuid",
        "invoice_no": "CIN-001",
        "balance_due": "decimal",
        "status": "unpaid/partial/paid",
        "created_date": "datetime"
      }
    ]
  }

  4. Get Order Details

  - Endpoint: GET /customer-invoice/get-order-details/{order_id}
  - Functionality: Shows complete details of a specific order
  - Response:
  {
    "order_id": "uuid",
    "invoice_no": "CIN-001",
    "customer_name": "string",
    "items": [...],
    "order_total": "decimal",
    "amount_paid": "decimal",
    "balance_due": "decimal",
    "payment_history": [
      {
        "amount": "decimal",
        "payment_method": "string",
        "date": "datetime",
        "description": "string"
      }
    ],
    "status": "unpaid/partial/paid"
  }

  5. Process Payment (Update Functionality)

  - Endpoint: PUT /customer-invoice/process-payment/{order_id}
  - Functionality: Process additional payments for existing orders (updates the order)
  - Request Body:
  {
    "amount": "decimal",           // Amount of this payment
    "payment_method": "string",    // cash/card/online/etc.
    "description": "string",       // Payment description/note
    "payment_date": "string"       // Date of payment (optional, defaults to today)
  }
  - Response:
  {
    "order_id": "uuid",
    "invoice_no": "CIN-001",
    "previous_balance": "decimal",     // Balance before this payment
    "payment_received": "decimal",     // Amount of this payment
    "new_balance": "decimal",          // Balance after this payment
    "total_paid": "decimal",           // Total amount paid so far
    "payment_status": "string",        // "unpaid", "partial", "paid"
    "payment_record": {
      "amount": "decimal",
      "payment_method": "string",
      "date": "datetime",
      "description": "string"
    },
    "updated_payment_history": [
      {
        "amount": "decimal",
        "payment_method": "string",
        "date": "datetime",
        "description": "string"
      }
    ]
  }

  6. Daily Collection Report

  - Endpoint: GET /customer-invoice/daily-collection-report/{date}
  - Functionality: Shows ALL payments collected on a specific date (across all orders)
  - Response:
  {
    "date": "2026-02-04",
    "total_collections": "decimal",      // Sum of ALL payments made on this date
    "collection_count": "integer",       // Number of payment transactions
    "collections": [
      {
        "order_id": "uuid",              // The order this payment belongs to
        "invoice_no": "CIN-001",         // Invoice number
        "customer_name": "string",       // Customer name
        "amount": "decimal",             // Amount paid on this date
        "payment_method": "string",      // How it was paid
        "description": "string",         // Payment description
        "time": "datetime"               // Exact time of payment
      }
    ]
  }

  7. Payment History Tracking

  - Endpoint: GET /customer-invoice/payment-history/{order_id}
  - Functionality: Shows complete payment history for an order
  - Response: Array of all payments made against the order

  8. Date-based Invoice Report (Existing)

  - Endpoint: GET /customer-invoice/customerinvoicesbydate?date=YYYY-MM-DD
  - Functionality: Shows all invoices created on a specific date with detailed product information
  - Response: Includes products array with Orderid, Product, Price, Amount Paid, Quantity, Discount, Total Discount, Cost, Time, Date

  Business Scenarios

  Scenario 1: New Custom Order

  1. Customer places custom order
  2. System creates invoice with CIN-001 number
  3. Status set to ISSUED
  4. Total amount recorded, balance due = total amount
  5. Payment status = "unpaid"

  Scenario 2: Partial Payment Processing

  1. Customer pays partial amount (e.g., 3,000 out of 10,000)
  2. Call PUT /customer-invoice/process-payment/{order_id} with amount: 3000
  3. System updates:
    - amount_paid increases by 3000
    - balance_due decreases by 3000
    - payment_status changes to "partial"
    - adds payment record to payment history
    - payment recorded in daily collection for that date
  4. Customer sees remaining balance: 7,000

  Scenario 3: Second Payment Processing

  1. Customer pays additional amount (e.g., 4,000)
  2. Call same endpoint with amount: 4000
  3. System updates:
    - amount_paid increases by 4000 (now 7000 total)
    - balance_due decreases by 4000 (now 3000 remaining)
    - payment_status remains "partial"
    - adds new payment record to payment history
    - payment recorded in daily collection for that date

  Scenario 4: Final Payment

  1. Customer pays remaining amount (e.g., 3,000)
  2. Call same endpoint with amount: 3000
  3. System updates:
    - amount_paid increases by 3000 (now 10000 total)
    - balance_due decreases by 3000 (now 0 remaining)
    - payment_status changes to "paid"
    - adds final payment record to payment history
    - payment recorded in daily collection for that date

  Scenario 5: Daily Collection Report

  - Shows all payments made on specific date (regardless of which order)
  - Example: Jan 15th shows 5 payments from 3 different orders totaling 15,000
  - Each payment is tracked separately with order and customer info

  Benefits

  - Simple numbering: CIN-001, CIN-002 format as implemented
  - Work-in-progress: Orders can track partial payments and completion status
  - Payment flexibility: Handle multiple payments across different dates
  - Customer visibility: See all orders and balances per customer
  - Daily tracking: Separate collection reports unaffected by payment distribution
  - Audit trail: Complete payment history for each order
  - Real-time updates: Balances update automatically with each payment
  - Scalable: Supports custom orders with complex requirements

  Key Distinctions

  - Order Balance: What's still owed per order (decreases with each payment)
  - Daily Collections: What was collected on each specific day (independent of order)
  - Payment Tracking: Complete history of all payments made over time
  - Customer View: Aggregate view of all orders and balances per customer

  This system integrates all requirements into a cohesive solution that handles immediate sales, custom orders, partial payments, and detailed reporting while maintaining data integrity and
  separation of concerns.
