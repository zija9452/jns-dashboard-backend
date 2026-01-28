from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging
import traceback
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

async def http_error_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    logger.error(f"HTTP Error {exc.status_code}: {exc.detail}")

    error_response = {
        "error": {
            "type": "http_error",
            "message": str(exc.detail),
            "status_code": exc.status_code,
            "path": request.url.path,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }
    }

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )

async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.error(f"Validation Error: {exc.errors()}")

    error_details = []
    for error in exc.errors():
        error_details.append({
            "loc": error["loc"],
            "msg": error["msg"],
            "type": error["type"]
        })

    error_response = {
        "error": {
            "type": "validation_error",
            "message": "Request validation failed",
            "details": error_details,
            "status_code": 422,
            "path": request.url.path,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }
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
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }
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
            "message": "An unexpected error occurred",
            "status_code": 500,
            "path": request.url.path,
            "timestamp": __import__('datetime').datetime.utcnow().isoformat()
        }
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
    app.add_exception_handler(Exception, general_exception_handler)