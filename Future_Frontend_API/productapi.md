# Product Management API

## 🔐 Authentication & Authorization

### Login Required

Before using any of these endpoints, you **MUST** login first:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123"
  }' \
  -c cookies.txt
```

**Save the cookie!** All subsequent requests require the session cookie (`-b cookies.txt`).

---

### 🔑 Access Control

| Decorator | Allowed Roles | Used By |
|-----------|--------------|---------|
| `admin_cashier_employee_required_from_session()` | `admin`, `cashier`, `employee` | GET products, GET single product |
| `employee_required_from_session()` | `admin`, `cashier`, `employee` | POST, PUT, DELETE operations |
| `admin_required_from_session()` | `admin` only | DELETE product (permanent) |

**Important Notes**:

1. **GET /products/viewproduct** - Requires **any authenticated user** (admin, cashier, employee)
   - All authenticated users can view products

2. **POST /products/** - Requires **employee** or higher
   - Employee, cashier, admin can create products

3. **PUT /products/{id}** - Requires **employee** or higher
   - Employee, cashier, admin can update products

4. **DELETE /products/{id}** - Requires **admin** only
   - Only admins can permanently delete products

---

## API Endpoints

### Product CRUD Operations

---

### 1. GET /products/viewproduct - View Products (Paginated)

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get paginated list of products with search and branch filtering. This is the **main endpoint** used by the frontend.

**Endpoint**: `GET /products/viewproduct?page=1&limit=8&search_string=`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number (1-based) |
| `limit` | int | 8 | Items per page |
| `search_string` | string | - | Search by name, barcode, or SKU |
| `branches` | string | - | Filter by branch name |

**Example**:
```bash
curl -X GET "http://localhost:8000/products/viewproduct?page=1&limit=8&search_string=Nike" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "data": [
    {
      "pro_id": "uuid-string",
      "pro_name": "Nike Shoes",
      "pro_price": 99.99,
      "pro_cost": 79.99,
      "pro_barcode": "1234567890123",
      "pro_dis": 10.0,
      "cat_id_fk": "Shoes",
      "limitedquan": 5,
      "branch": "European Sports Light House",
      "brand": "Nike",
      "pro_image": "",
      "stock": 50
    }
  ],
  "page": 1,
  "limit": 8,
  "total": 100,
  "total_pages": 13,
  "has_more": true
}
```

**Response Fields**:
- `data`: Array of products (max 8 per page)
- `page`: Current page number
- `limit`: Items per page
- `total`: Total number of products matching search
- `total_pages`: Total pages (for pagination UI)
- `has_more`: True if more pages available

**Error** (401 Unauthorized):
```json
{
  "detail": "Not authenticated"
}
```

---

### 2. POST /products/ - Create Product

**Access**: `employee_required_from_session()` - **Employee, Cashier, Admin**

**Description**: Create a new product.

**Endpoint**: `POST /products/`

**Request Body**:
```json
{
  "sku": "SKU-1234567890",
  "name": "Nike Air Max",
  "unit_price": 99.99,
  "cost_price": 79.99,
  "stock_level": 50,
  "barcode": "1234567890123",
  "discount": 10.0,
  "category": "Shoes",
  "branch": "European Sports Light House",
  "limited_qty": 5,
  "brand_action": "Nike",
  "attributes": "data:image/png;base64,..."
}
```

**Request Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sku` | string | ✅ Yes | Unique SKU (auto-generated) |
| `name` | string | ✅ Yes | Product name |
| `unit_price` | number | ✅ Yes | Selling price |
| `cost_price` | number | ✅ Yes | Cost price |
| `stock_level` | int | ✅ Yes | Initial stock (default: 0) |
| `barcode` | string | ❌ No | Barcode (auto-generated) |
| `discount` | number | ❌ No | Discount percentage |
| `category` | string | ❌ No | Category name |
| `branch` | string | ❌ No | Branch name |
| `limited_qty` | int | ❌ No | Limited quantity threshold |
| `brand_action` | string | ❌ No | Brand name |
| `attributes` | string | ❌ No | Image (base64 or URL) |

**Example**:
```bash
curl -X POST "http://localhost:8000/products/" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "sku": "SKU-1234567890",
    "name": "Nike Air Max",
    "unit_price": 99.99,
    "cost_price": 79.99,
    "stock_level": 50,
    "barcode": "1234567890123",
    "discount": 10.0,
    "category": "Shoes",
    "branch": "European Sports Light House",
    "limited_qty": 5,
    "brand_action": "Nike"
  }'
```

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "sku": "SKU-1234567890",
  "name": "Nike Air Max",
  "unit_price": "99.99",
  "cost_price": "79.99",
  "stock_level": 50,
  "barcode": "1234567890123",
  "discount": "10.00",
  "category": "Shoes",
  "branch": "European Sports Light House",
  "limited_qty": 5,
  "brand_action": "Nike",
  "created_at": "2026-02-17T05:00:00.000000",
  "updated_at": "2026-02-17T05:00:00.000000"
}
```

**Errors**:

**400 Bad Request** - SKU exists:
```json
{
  "detail": "Product with this SKU already exists"
}
```

---

### 3. PUT /products/{product_id} - Update Product

**Access**: `employee_required_from_session()` - **Employee, Cashier, Admin**

**Description**: Update an existing product.

**Endpoint**: `PUT /products/{product_id}`

**Path Parameter**: `product_id` - UUID of the product

**Request Body** (all fields optional):
```json
{
  "name": "Updated Name",
  "unit_price": 109.99,
  "cost_price": 89.99,
  "stock_level": 60,
  "barcode": "9876543210987",
  "discount": 15.0,
  "category": "Updated Category",
  "branch": "Updated Branch",
  "limited_qty": 10,
  "brand_action": "Updated Brand",
  "attributes": "new-image-url"
}
```

**Example**:
```bash
curl -X PUT "http://localhost:8000/products/uuid-string" \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "name": "Updated Name",
    "unit_price": 109.99,
    "discount": 15.0
  }'
```

**Response** (200 OK):
```json
{
  "id": "uuid-string",
  "sku": "SKU-1234567890",
  "name": "Updated Name",
  "unit_price": "109.99",
  "cost_price": "79.99",
  "stock_level": 50,
  "barcode": "1234567890123",
  "discount": "15.00",
  "category": "Shoes",
  "branch": "European Sports Light House",
  "limited_qty": 5,
  "brand_action": "Nike",
  "updated_at": "2026-02-17T06:00:00.000000"
}
```

**Errors**:

**404 Not Found**:
```json
{
  "detail": "Product not found"
}
```

---

### 4. DELETE /products/deleteproduct/{id} - Delete Product

**Access**: `admin_employee_required_from_session()` - **Admin, Employee** (NOT Cashier)

**Description**: Delete a product by ID (frontend-compatible endpoint).

**Endpoint**: `POST /products/deleteproduct/{id}`

**Path Parameter**: `id` - UUID of the product

**Important**: 
- ✅ **Admin** can delete products
- ✅ **Employee** can delete products
- ❌ **Cashier** CANNOT delete products (403 Forbidden)

**Example**:
```bash
curl -X POST "http://localhost:8000/products/deleteproduct/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Product deleted successfully"
}
```

**Error** (403 Forbidden) - Cashier trying to delete:
```json
{
  "detail": "Admin or employee access required. Cashiers cannot perform this action."
}
```

**Errors**:

**404 Not Found**:
```json
{
  "detail": "Product not found"
}
```

---

### 5. GET /products/generatebarcode - Generate Barcode

**Access**: `employee_required_from_session()` - **Employee, Cashier, Admin**

**Description**: Generate a unique barcode for new products (auto-increment approach).

**Endpoint**: `GET /products/generatebarcode`

**Example**:
```bash
curl -X GET "http://localhost:8000/products/generatebarcode" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "barcode": "6901234567890"
}
```

---

### 6. GET /products/searchbybarcode - Search by Barcode

**Access**: `employee_required_from_session()` - **Employee, Cashier, Admin**

**Description**: Search product by barcode (Redis cached, very fast).

**Endpoint**: `GET /products/searchbybarcode?barcode=`

**Query Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `barcode` | string | Barcode to search |

**Example**:
```bash
curl -X GET "http://localhost:8000/products/searchbybarcode?barcode=1234567890123" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "pro_id": "uuid-string",
  "pro_name": "Nike Air Max",
  "pro_price": 99.99,
  "pro_cost": 79.99,
  "pro_barcode": "1234567890123",
  "pro_dis": 10.0,
  "cat_id_fk": "Shoes",
  "limitedquan": 5,
  "branch": "European Sports Light House",
  "brand": "Nike",
  "pro_image": "",
  "stock": 50
}
```

**Error** (404 Not Found):
```json
{
  "detail": "Product not found"
}
```

---

### 7. GET /products/getproducts/{id} - Get Product Details

**Access**: `admin_cashier_employee_required_from_session()` - **Any authenticated user**

**Description**: Get specific product details by ID (frontend-compatible format).

**Endpoint**: `GET /products/getproducts/{id}`

**Path Parameter**: `id` - UUID of the product

**Example**:
```bash
curl -X GET "http://localhost:8000/products/getproducts/uuid-string" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "pro_id": "uuid-string",
  "pro_name": "Nike Air Max",
  "pro_price": 99.99,
  "pro_cost": 79.99,
  "pro_barcode": "1234567890123",
  "pro_dis": 10.0,
  "cat_id_fk": "Shoes",
  "limitedquan": 5,
  "branch": "European Sports Light House",
  "brand": "Nike",
  "pro_image": ""
}
```

---

## Category & Brand Endpoints (Used by Product Page)

### 8. GET /category/ - Get All Categories

**Access**: `employee_required_from_session()` - **Any authenticated user**

**Description**: Get all categories for dropdown (used in product form).

**Endpoint**: `GET /category/?page=1&limit=1000`

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Page number |
| `limit` | int | 100 | Max records (use 1000 for dropdown) |

**Example**:
```bash
curl -X GET "http://localhost:8000/category/?page=1&limit=1000" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid-string",
      "name": "Shoes",
      "branch": "Light House",
      "created_at": "2026-02-17T05:00:00.000000"
    }
  ],
  "page": 1,
  "limit": 1000,
  "total": 10,
  "total_pages": 1
}
```

---

### 9. GET /brand/ - Get All Brands

**Access**: `employee_required_from_session()` - **Any authenticated user**

**Description**: Get all brands for dropdown (used in product form).

**Endpoint**: `GET /brand/?page=1&limit=1000`

**Example**:
```bash
curl -X GET "http://localhost:8000/brand/?page=1&limit=1000" \
  -b cookies.txt
```

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "uuid-string",
      "name": "Nike",
      "created_at": "2026-02-17T05:00:00.000000"
    }
  ],
  "page": 1,
  "limit": 1000,
  "total": 5,
  "total_pages": 1
}
```

---

## Frontend API Routes

The frontend uses Next.js API routes as proxies:

| Frontend Route | Backend Endpoint |
|----------------|------------------|
| `GET /api/products` | `GET /products/viewproduct` |
| `POST /api/products` | `POST /products/` |
| `PUT /api/products/{id}` | `PUT /products/{id}` |
| `DELETE /api/products/{id}` | `POST /products/deleteproduct/{id}` |
| `GET /api/products/generatebarcode` | `GET /products/generatebarcode` |
| `GET /api/category` | `GET /category/` |
| `GET /api/brand` | `GET /brand/` |

**Example** - Frontend fetch with pagination:
```typescript
const fetchProducts = async (page: number = 1, searchTerm: string = '') => {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: '8',
    search_string: searchTerm
  });

  const response = await fetch(`/api/products?${params.toString()}`, {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to fetch products');
  }

  return response.json();
};
```

---

## Error Codes

| HTTP Status | Meaning | Common Causes |
|-------------|---------|---------------|
| 200 | OK | Success |
| 400 | Bad Request | Invalid input, SKU exists |
| 401 | Unauthorized | Not logged in, invalid session |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Product not found |
| 500 | Server Error | Database error, server issue |
| 504 | Gateway Timeout | Request timeout (>2 min) |

---

## Testing Checklist

### Login First
- [ ] Login with admin credentials
- [ ] Save cookies (`-c cookies.txt`)

### Test GET /products/viewproduct
- [ ] Fetch first page (page=1, limit=8)
- [ ] Fetch with search term
- [ ] Fetch with branch filter
- [ ] Verify pagination response format

### Test POST /products/
- [ ] Create new product with all fields
- [ ] Create product with auto-generated barcode
- [ ] Try duplicate SKU (should fail)

### Test PUT /products/{id}
- [ ] Update product price
- [ ] Update product name
- [ ] Update product image

### Test DELETE /products/deleteproduct/{id}
- [ ] Delete product (admin only)
- [ ] Try delete as non-admin (should fail)

### Test GET /products/generatebarcode
- [ ] Generate unique barcode
- [ ] Verify barcode format (13 digits)

### Test GET /products/searchbybarcode
- [ ] Search existing barcode
- [ ] Search non-existent barcode (should 404)

### Test Category & Brand
- [ ] Fetch all categories (for dropdown)
- [ ] Fetch all brands (for dropdown)

---

## Related Documentation

- [Authentication](authentication_api.md) - Login and session management
- [User Management](administrative_api.md) - User CRUD operations
- [Stock API](stockapi.md) - Stock management
- [Category API](category_api.md) - Category CRUD
- [Brand API](brand_api.md) - Brand CRUD
