from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from src.routers import auth, users, products, customers, vendors, salesman, stock, expenses, invoices, custom_orders, refunds, admin, pos
from src.utils.error_handlers import setup_error_handlers

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from src.app_startup import initialize_database
    await initialize_database()
    yield
    # Shutdown

app = FastAPI(
    title="Regal POS Backend",
    description="Backend API for Regal POS system with exact parity to admin dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# Setup error handlers
setup_error_handlers(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Regal POS Backend API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "regal-pos-backend"}

@app.get("/health/db")
def db_health():
    """Check database connectivity"""
    from sqlmodel import select
    from src.models.user import User

    try:
        # Attempt to connect to the database and perform a simple query
        from src.database.database import SessionLocal
        db = SessionLocal()
        db.exec(select(User).limit(1))
        db.close()
        return {"status": "healthy", "service": "database"}
    except Exception as e:
        return {"status": "unhealthy", "service": "database", "error": str(e)}, 503

@app.get("/health/ready")
def readiness_check():
    """Check if the service is ready to serve traffic"""
    # Add any additional readiness checks here
    # For example, checking if all required services are available
    return {"status": "ready", "service": "regal-pos-backend"}

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(customers.router, prefix="/customers", tags=["customers"])
app.include_router(vendors.router, prefix="/vendors", tags=["vendors"])
app.include_router(salesman.router, prefix="/salesman", tags=["salesman"])
app.include_router(stock.router, prefix="/stock", tags=["stock"])
app.include_router(expenses.router, prefix="/expenses", tags=["expenses"])
app.include_router(invoices.router, prefix="/invoices", tags=["invoices"])
app.include_router(custom_orders.router, prefix="/custom-orders", tags=["custom-orders"])
app.include_router(refunds.router, prefix="/refunds", tags=["refunds"])
app.include_router(pos.router, prefix="/pos", tags=["pos"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)