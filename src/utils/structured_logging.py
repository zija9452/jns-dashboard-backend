"""
Structured logging utilities for the Regal POS Backend
Provides JSON-formatted logs suitable for log aggregation systems
"""
import json
import logging
import sys
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4
import traceback
from contextvars import ContextVar

# Context variable to store request ID for correlation
request_id_var: ContextVar[str] = ContextVar('request_id', default=None)


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs logs in JSON format
    """

    def format(self, record):
        # Build the log entry dictionary
        log_entry = {
            'timestamp': datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }

        # Add request ID if available
        request_id = request_id_var.get()
        if request_id:
            log_entry['request_id'] = request_id

        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }

        # Add any extra fields
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                               'filename', 'module', 'lineno', 'funcName', 'created',
                               'msecs', 'relativeCreated', 'thread', 'threadName',
                               'processName', 'process', 'getMessage', 'exc_info',
                               'exc_text', 'stack_info']:
                    log_entry[key] = value

        return json.dumps(log_entry, ensure_ascii=False)


class CorrelationIdMiddleware:
    """
    Middleware to add correlation IDs to requests for tracing
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        # Generate or extract request ID
        request_id = None

        # Try to extract from headers
        for name, value in scope['headers']:
            if name == b'x-request-id':
                request_id = value.decode('utf-8')
                break

        # Generate if not found
        if not request_id:
            request_id = str(uuid4())

        # Set the request ID in context
        request_id_var.set(request_id)

        # Add request ID to response headers
        async def send_wrapper(message):
            if message['type'] == 'http.response.start':
                headers = message.get('headers', [])
                headers.append([b'x-request-id', request_id.encode('utf-8')])
                message['headers'] = headers
            await send(message)

        await self.app(scope, receive, send_wrapper)


def setup_structured_logging(level: str = "INFO", format_type: str = "json"):
    """
    Set up structured logging for the application
    """
    # Create root logger
    root_logger = logging.getLogger()

    # Remove default handlers
    root_logger.handlers.clear()

    # Set level
    root_logger.setLevel(getattr(logging, level.upper()))

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Set formatter based on type
    if format_type.lower() == "json":
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Set levels for specific loggers
    logging.getLogger('uvicorn').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name
    """
    return logging.getLogger(name)


def log_api_request(method: str, path: str, status_code: int, duration: float, user_id: Optional[str] = None):
    """
    Log an API request with structured format
    """
    logger = get_logger('api')

    extra = {
        'event_type': 'api_request',
        'method': method,
        'path': path,
        'status_code': status_code,
        'duration_ms': duration * 1000,  # Convert to milliseconds
    }

    if user_id:
        extra['user_id'] = user_id

    logger.info(
        f"{method} {path} {status_code} in {duration * 1000:.2f}ms",
        extra=extra
    )


def log_business_event(event_type: str, user_id: str, entity: str, action: str, details: Dict[str, Any] = None):
    """
    Log a business event with structured format
    """
    logger = get_logger('business')

    extra = {
        'event_type': 'business_event',
        'business_event_type': event_type,
        'user_id': user_id,
        'entity': entity,
        'action': action,
        'details': details or {}
    }

    logger.info(
        f"Business event: {event_type} - {action} {entity} by user {user_id}",
        extra=extra
    )


def log_error(error_msg: str, error_type: str, context: Dict[str, Any] = None, user_id: Optional[str] = None):
    """
    Log an error with structured format
    """
    logger = get_logger('errors')

    extra = {
        'event_type': 'error',
        'error_type': error_type,
        'context': context or {},
    }

    if user_id:
        extra['user_id'] = user_id

    logger.error(error_msg, extra=extra)


def get_correlation_id() -> Optional[str]:
    """
    Get the current correlation ID
    """
    return request_id_var.get()


def set_correlation_id(request_id: str):
    """
    Set the correlation ID in the current context
    """
    request_id_var.set(request_id)