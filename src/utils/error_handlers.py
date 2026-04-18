from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import IntegrityError
import logging
import traceback
import re
from datetime import datetime
from typing import Dict, Any

# Set up logger
logger = logging.getLogger(__name__)

class AppError(Exception):
    """Base application error"""
    def __init__(self, message: str, status_code: int = 400, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}

async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Handle SQLAlchemy integrity errors (unique constraints, foreign keys)"""
    logger.error(f"Integrity Error: {str(exc)}")
    
    error_msg = str(exc.orig) if hasattr(exc, 'orig') else str(exc)
    detail = "A database integrity error occurred."
    
    # User-friendly messages for common scenarios
    if "unique constraint" in error_msg.lower() or "duplicate key" in error_msg.lower():
        # Try to extract the field name from asyncpg error message
        # Example: duplicate key value violates unique constraint "users_username_key"
        # DETAIL:  Key (username)=(admin) already exists.
        match = re.search(r'Key \((.+?)\)=\((.+?)\) already exists', error_msg)
        if match:
            field = match.group(1)
            value = match.group(2)
            detail = f"A record with {field} '{value}' already exists. Please use a unique value."
        else:
            # Fallback for other unique constraint formats
            match = re.search(r'constraint "(.+?)"', error_msg)
            if match:
                constraint_name = match.group(1)
                # Try to guess field name from constraint name (e.g., products_sku_key -> sku)
                parts = constraint_name.split('_')
                if len(parts) > 1:
                    field = parts[1]
                    detail = f"A record with this {field} already exists. Please use a unique value."
                else:
                    detail = f"Value violates unique constraint '{constraint_name}'. Please use a unique value."
            else:
                detail = "This record already exists. Please use unique values for all fields."
            
    elif "foreign key constraint" in error_msg.lower():
        if "is still referenced" in error_msg.lower() or "update or delete" in error_msg.lower():
             detail = "This record cannot be deleted or modified because it is being used by other records (e.g., invoices, stock entries, or related data). Please delete the related records first."
        else:
             detail = "Referenced record not found. Please ensure the related item (like Customer, Product, or Vendor) exists."
             
    elif "not-null constraint" in error_msg.lower():
        # Example: null value in column "name" violates not-null constraint
        match = re.search(r'column "(.+?)"', error_msg)
        if match:
            field = match.group(1)
            detail = f"The field '{field}' is required and cannot be empty."
        else:
            detail = "A required field is missing. Please fill in all mandatory fields."

    error_response = {
        "error": {
            "type": "integrity_error",
            "message": detail,
            "status_code": 400,
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat()
        },
        "detail": detail
    }

    return JSONResponse(
        status_code=400,
        content=error_response
    )

async def http_error_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP Error {exc.status_code}: {exc.detail}")

    error_response = {
        "error": {
            "type": "http_error",
            "message": str(exc.detail),
            "status_code": exc.status_code,
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat()
        },
        "detail": str(exc.detail)
    }

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )

async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.error(f"Validation Error: {exc.errors()}")

    error_details = []
    messages = []
    for error in exc.errors():
        # Get field name, ignoring 'body' or other prefix
        loc_parts = error["loc"]
        field_name = " -> ".join([str(p) for p in loc_parts[1:]]) if len(loc_parts) > 1 else str(loc_parts[0])
        
        msg = f"{field_name}: {error['msg']}"
        messages.append(msg)
        
        error_details.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })

    # Combine messages for a user-friendly detail string
    detail = "Validation failed: " + ", ".join(messages)

    error_response = {
        "error": {
            "type": "validation_error",
            "message": "Request validation failed",
            "details": error_details,
            "status_code": 422,
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat()
        },
        "detail": detail
    }

    return JSONResponse(
        status_code=422,
        content=error_response
    )

async def app_error_handler(request: Request, exc: AppError):
    """Handle custom application errors"""
    logger.error(f"App Error {exc.status_code}: {exc.message}")

    error_response = {
        "error": {
            "type": "app_error",
            "message": exc.message,
            "details": exc.details,
            "status_code": exc.status_code,
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat()
        },
        "detail": exc.message
    }

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    logger.error(f"Unexpected error: {str(exc)}")
    logger.error(traceback.format_exc())

    error_response = {
        "error": {
            "type": "internal_error",
            "message": "An unexpected error occurred. Please try again later.",
            "status_code": 500,
            "path": request.url.path,
            "timestamp": datetime.utcnow().isoformat()
        },
        "detail": "An unexpected error occurred. Please try again later."
    }

    return JSONResponse(
        status_code=500,
        content=error_response
    )

def setup_error_handlers(app):
    """Register error handlers with the FastAPI app"""
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)