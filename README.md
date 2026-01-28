# Regal POS Backend

Backend API for Regal POS system with exact parity to admin dashboard, built with FastAPI and SQLModel.

## Features

- **Authentication**: JWT-based authentication with refresh token rotation and revocation
- **Role-Based Access Control**: Admin, Cashier, and Employee roles with granular permissions
- **Full CRUD Operations**: For all entities (Users, Products, Customers, Vendors, Salesmen, Stock, Expenses, Invoices, Refunds)
- **Inventory Management**: Track stock levels with automated adjustments
- **Audit Logging**: Comprehensive logging of all critical actions with 7-year retention
- **Docker Support**: Multi-container setup with hot-reload for development
- **Rate Limiting**: Protection against brute force attacks on authentication endpoints
- **Input Validation & Sanitization**: Protection against XSS and injection attacks
- **Health Checks**: Comprehensive health and readiness endpoints

## Tech Stack

- **Language**: Python 3.10+
- **Framework**: FastAPI
- **ORM**: SQLModel (SQLAlchemy + Pydantic)
- **Database**: PostgreSQL (compatible with Neon)
- **Authentication**: JWT with refresh token rotation
- **Cache/Broker**: Redis (for sessions, rate-limiting)
- **Containerization**: Docker + Docker Compose
- **Security**: Rate limiting, input sanitization, RBAC

## Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.10+ (for local development without containers)

### Local Development

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-name>
   ```

2. Copy the environment file and update the values:
   ```bash
   cp .env .env.local
   # Edit .env.local with your configuration
   ```

3. Start the development environment:
   ```bash
   docker-compose up --build
   ```

4. The API will be available at `http://localhost:8000`
5. API documentation will be available at `http://localhost:8000/docs`

### Manual Setup (without Docker)

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   ```bash
   export DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/regal_pos_dev
   export ACCESS_TOKEN_SECRET_KEY=your-secret-key
   export REFRESH_TOKEN_SECRET_KEY=your-refresh-secret-key
   ```

4. Run the application:
   ```bash
   uvicorn src.api.main:app --reload
   ```

## API Endpoints

### Health Checks
- `GET /health` - Overall health status
- `GET /health/db` - Database connectivity check
- `GET /health/ready` - Readiness status for serving traffic

### Authentication
- `POST /auth/login` - Login and get JWT tokens
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout and revoke refresh token

### Users
- `GET /users` - Get all users
- `POST /users` - Create a new user
- `GET /users/{id}` - Get a specific user
- `PUT /users/{id}` - Update a user
- `DELETE /users/{id}` - Delete a user

### Products
- `GET /products` - Get all products
- `POST /products` - Create a new product
- `GET /products/{id}` - Get a specific product
- `PUT /products/{id}` - Update a product
- `DELETE /products/{id}` - Delete a product

### POS Operations (Cashier)
- `POST /pos/quick-sell` - Quick sell functionality
- `POST /pos/cash-drawer/open` - Open cash drawer
- `POST /pos/cash-drawer/close` - Close cash drawer
- `POST /pos/shift-close` - Close cashier's shift
- `GET /pos/shift-report` - Get shift report
- `GET /pos/daily-report` - Get daily report
- `GET /pos/sales-report` - Get sales report
- `GET /pos/duplicate-bill/{id}` - Get duplicate bill

### Invoices
- `GET /invoices` - Get all invoices
- `POST /invoices` - Create a new invoice
- `GET /invoices/{id}` - Get a specific invoice
- `PUT /invoices/{id}` - Update an invoice
- `DELETE /invoices/{id}` - Delete an invoice

### Other endpoints available for:
- Customers
- Vendors
- Salesmen
- Stock entries
- Expenses
- Custom orders
- Refunds
- Admin dashboard

## Default Credentials

After initial setup, a default admin user is created:
- **Username**: `admin`
- **Password**: `admin123`

## Database Migrations

Using Alembic for database migrations:
```bash
# Create a new migration
alembic revision --autogenerate -m "Migration description"

# Apply migrations
alembic upgrade head
```

## Environment Variables

- `DATABASE_URL` - Database connection string
- `ACCESS_TOKEN_SECRET_KEY` - Secret key for access tokens
- `REFRESH_TOKEN_SECRET_KEY` - Secret key for refresh tokens
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Access token expiration time (default: 15)
- `REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token expiration time (default: 30)
- `REDIS_URL` - Redis connection string
- `APP_ENV` - Application environment (development/production)
- `DEBUG` - Enable/disable debug mode
- `DEFAULT_PAGE_SIZE` - Default pagination size (default: 50)
- `MAX_PAGE_SIZE` - Maximum pagination size (default: 200)

## Role-Based Access Control

- **Admin**: Full access to all endpoints and functions
- **Cashier**: Access to POS-related functions, invoices, payments, customers, reports
- **Employee**: Access to most functions but with limited administrative capabilities

## Audit Logging

All critical actions are logged with:
- Entity affected
- Action performed
- User who performed the action
- Timestamp
- Changes made

Audit logs are retained for 7 years as per compliance requirements.

## Security Features

- **Rate Limiting**: Authentication endpoints are protected against brute force attacks
- **Input Sanitization**: All user inputs are sanitized to prevent XSS
- **JWT Tokens**: Secure authentication with refresh token rotation
- **Role-Based Access Control**: Fine-grained permissions per user role
- **Secure Headers**: Proper security headers are set

## Docker Compose Services

- **api**: FastAPI application
- **postgres**: PostgreSQL database
- **redis**: Redis for caching and session management
- **nginx**: Optional reverse proxy (uncomment in docker-compose.yml if needed)

## Production Deployment

For production deployment with Neon:
1. Update the `NEON_DATABASE_URL` in your environment
2. Ensure SSL is enabled
3. Use production-grade Redis and PostgreSQL configurations
4. Implement proper secret management
5. Set DEBUG=False
6. Use proper logging and monitoring

## Error Handling

The application implements comprehensive error handling:
- HTTP error responses with detailed messages
- Validation error responses with field-specific details
- Internal server error handling with logging
- Graceful degradation for partial failures

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Testing

To run tests:
```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_module.py
```

## License

This project is licensed under the MIT License.