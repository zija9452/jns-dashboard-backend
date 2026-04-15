from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from decimal import Decimal

from src.routers import auth, users, products, customers, vendors, salesman, stock, expenses, customer_invoice, refunds, admin, pos, walkin_invoice, walkin_refund, category, brand, expense_type, sales_view, duplicate_bill, customer_category, ideal_price, warehouse_stock
from src.utils.error_handlers import setup_error_handlers
from src.middleware.security import SecurityHeadersMiddleware
from src.utils.metrics import MetricsMiddleware, start_metrics_server
from src.utils.structured_logging import setup_structured_logging, CorrelationIdMiddleware
from src.middleware.compression import CompressionMiddleware
from src.utils.tracing import setup_tracing

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from src.app_startup import initialize_database
    from src.database.database import init_cache
    await initialize_database()
    
    # Initialize Redis cache
    await init_cache()

    # Start metrics server in a background thread
    import threading
    from src.utils.metrics import start_metrics_server
    metrics_thread = threading.Thread(target=start_metrics_server, daemon=True)
    metrics_thread.start()

    yield

    # Shutdown
    from src.database.database import close_cache
    await close_cache()

app = FastAPI(
    title="Regal POS Backend",
    description="Backend API for Regal POS system with exact parity to admin dashboard",
    version="1.0.0",
    lifespan=lifespan,
    # Configure JSON encoders to handle Decimal serialization
    json_encoders={Decimal: float}
)

# Setup structured logging
setup_structured_logging(level="INFO", format_type="json")

# Setup error handlers
setup_error_handlers(app)

# Add correlation ID middleware
app.add_middleware(CorrelationIdMiddleware)

# Add compression middleware
app.add_middleware(CompressionMiddleware)

# Setup and add tracing middleware
app = setup_tracing(app)

# Metrics middleware
app.add_middleware(MetricsMiddleware)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware - More secure configuration for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else ["http://localhost:3000", "http://127.0.0.1:3000"],  # Specify your frontend URLs
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    # Expose headers that browsers are allowed to access
    expose_headers=["Access-Control-Allow-Origin", "Access-Control-Allow-Credentials"]
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Regal POS Backend API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "regal-pos-backend"}

@app.get("/health/db")
async def db_health():
    """Check database connectivity"""
    from sqlmodel import select
    from src.models.user import User
    from src.models.customer_invoice import CustomerInvoice

    try:
        # Attempt to connect to the database and perform a simple query using async session
        from src.database.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            # Check that we can query both user and customer invoice tables
            await session.execute(select(User).limit(1))
            await session.execute(select(CustomerInvoice).limit(1))
        return {"status": "healthy", "service": "database"}
    except Exception as e:
        return {"status": "unhealthy", "service": "database", "error": str(e)}, 503

@app.get("/health/ready")
def readiness_check():
    """Check if the service is ready to serve traffic"""
    # Add any additional readiness checks here
    # For example, checking if all required services are available
    return {"status": "ready", "service": "regal-pos-backend"}

@app.get("/health/customer-invoice")
async def customer_invoice_health():
    """Check customer invoice functionality"""
    from sqlmodel import select
    from src.models.customer_invoice import CustomerInvoice

    try:
        from src.database.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            # Try to query the customer invoice table
            stmt = select(CustomerInvoice).limit(1)
            result = await session.execute(stmt)
            # Just test that we can execute the query
            _ = result.scalars().first()
        return {"status": "healthy", "service": "customer-invoice"}
    except Exception as e:
        return {"status": "unhealthy", "service": "customer-invoice", "error": str(e)}, 503

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(category.router, tags=["category"])
app.include_router(brand.router, tags=["brand"])
app.include_router(customers.router, prefix="/customers", tags=["customers"])
app.include_router(vendors.router, prefix="/vendors", tags=["vendors"])
app.include_router(salesman.router, prefix="/salesman", tags=["salesman"])
app.include_router(stock.router, prefix="/stock", tags=["stock"])
app.include_router(expenses.router, tags=["expenses"])
app.include_router(customer_invoice.router, prefix="/customerinvoice", tags=["customer-invoice"])
app.include_router(refunds.router, prefix="/refunds", tags=["refunds"])
app.include_router(pos.router, prefix="/pos", tags=["pos"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(walkin_invoice.router, prefix="/walkininvoice", tags=["walkininvoice"])
app.include_router(walkin_refund.router, prefix="/walkinrefund", tags=["walkinrefund"])
app.include_router(expense_type.router, tags=["expensetype"])
app.include_router(sales_view.router, prefix="/salesview", tags=["salesview"])
app.include_router(duplicate_bill.router, prefix="/duplicatebill", tags=["duplicate-bill"])
app.include_router(customer_category.router, tags=["customer-category"])
app.include_router(ideal_price.router, tags=["ideal-pricing"])
app.include_router(warehouse_stock.router, tags=["warehouse-stock"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)