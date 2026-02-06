# Customer Invoice API Comprehensive Testing

## All Customer Invoice Endpoints

### 1. GET /customer-invoice/GetCustomerDetails
**Description**: Get customer details by name
**Method**: POST
**Parameters**:
- `cus_name` (query parameter)
**Auth**: Required (admin)

### 2. GET /customer-invoice/Getsalesmandetail
**Description**: Get salesman details by name
**Method**: POST
**Parameters**:
- `sal_name` (query parameter)
**Auth**: Required (admin)

### 3. POST /customer-invoice/SaveCustomerOrders
**Description**: Save customer orders (create invoice)
**Method**: POST
**Request Body**:
```json
{
  "items": [
    {
      "pro_name": "T-Shirt",
      "pro_quantity": 2,
      "unit_price": 10.0,
      "discount": 0.0,
      "cat_name": "Clothing"
    }
  ],
  "customer_id": "uuid-string",
  "customer_name": "Customer Name",
  "team_name": "Team Name",
  "payment_method": "cash",
  "initial_paid_amount": 10.0,
  "remarks": "Order remarks",
  "salesman_id": "uuid-string",
  "timezone": "UTC",
  "date": "2026-02-06"
}
```
**Auth**: Required (admin)

### 4. POST /customer-invoice/GetCustomerInvoiceBalance
**Description**: Get customer invoice balance
**Method**: POST
**Parameters**:
- `customer_id` (query parameter, optional)
**Auth**: Required (admin)

### 5. PUT /customer-invoice/UpdateCustomerInvoice/{invoice_id}
**Description**: Update customer invoice by ID
**Method**: PUT
**Path Parameter**:
- `invoice_id` (UUID)
**Query Parameters**:
- `e_name` (string, optional)
- `e_amount` (float, optional)
- `note` (string, optional)
**Auth**: Required (admin)

### 6. GET /customer-invoice/Getorder/{id}
**Description**: Get specific order details by ID
**Method**: GET
**Path Parameter**:
- `id` (UUID)
**Auth**: Required (admin)

### 7. GET /customer-invoice/Viewcustomerorder
**Description**: View customer orders with optional filtering
**Method**: GET
**Query Parameters**:
- `searchString` (string, optional)
- `status` (string, optional)
- `skip` (int, default: 0)
- `limit` (int, default: 100)
**Auth**: Required (admin)

### 8. GET /customer-invoice/customerorderreport
**Description**: Generate customer order report
**Method**: GET
**Query Parameters**:
- `orderid` (string, optional)
- `timezone` (string, optional)
- `printoption` (string, optional)
**Auth**: Required (admin)

### 9. DELETE /customer-invoice/Deletecustomorder/{id}
**Description**: Delete customer order by ID
**Method**: DELETE
**Path Parameter**:
- `id` (UUID)
**Auth**: Required (admin)

### 10. POST /customer-invoice/Customers
**Description**: Create new customer
**Method**: POST
**Query Parameters**:
- `cus_name` (string, required)
- `cus_phone` (string, required)
- `cus_address` (string, required)
- `cus_cnic` (string, required)
- `cus_sal_id_fk` (string, optional)
**Auth**: Required (admin)

### 11. POST /customer-invoice/GetSalesmanDetails
**Description**: Get salesman details by name
**Method**: POST
**Query Parameter**:
- `sal_name` (string, optional)
**Auth**: Required (admin)

### 12. POST /customer-invoice/customerbalance
**Description**: Get customer balance by name
**Method**: POST
**Query Parameter**:
- `cus_name` (string, optional)
**Auth**: Required (admin)

### 13. GET /customer-invoice/customer-balance/{customer_id}
**Description**: Get customer balance by ID
**Method**: GET
**Path Parameter**:
- `customer_id` (UUID)
**Auth**: Required (admin)

### 14. GET /customer-invoice/customer-orders/{customer_id}
**Description**: Get all orders for a specific customer
**Method**: GET
**Path Parameter**:
- `customer_id` (UUID)
**Auth**: Required (admin)

### 15. GET /customer-invoice/order-details/{order_id}
**Description**: Get detailed information for a specific order
**Method**: GET
**Path Parameter**:
- `order_id` (UUID)
**Auth**: Required (admin)

### 16. PUT /customer-invoice/process-payment/{order_id}
**Description**: Process payment for an existing order
**Method**: PUT
**Path Parameter**:
- `order_id` (UUID)
**Query Parameters**:
- `amount` (float, required)
- `payment_method` (string, required)
- `description` (string, required)
- `payment_date` (string, optional)
**Auth**: Required (admin)

### 17. GET /customer-invoice/daily-collection-report/{date}
**Description**: Get all payments collected on a specific date
**Method**: GET
**Path Parameter**:
- `date` (string, format: YYYY-MM-DD)
**Auth**: Required (admin)

### 18. GET /customer-invoice/payment-history/{order_id}
**Description**: Get payment history for a specific order
**Method**: GET
**Path Parameter**:
- `order_id` (UUID)
**Auth**: Required (admin)

### 19. GET /customer-invoice/customerinvoicesbydate
**Description**: Get all customer invoices for a specific date
**Method**: GET
**Query Parameter**:
- `date` (string, format: YYYY-MM-DD)
**Auth**: Required (admin)