"""
Metrics collection for the Regal POS Backend
Integrates with Prometheus for application monitoring
"""

from prometheus_client import Counter, Histogram, Gauge, start_http_server, REGISTRY
from functools import wraps
import time
import logging
from typing import Callable, Any
from fastapi import Request, Response

# Define application metrics
REQUEST_COUNT = Counter(
    'app_requests_total',
    'Total requests by method, path, and status code',
    ['method', 'path', 'status_code']
)

REQUEST_DURATION = Histogram(
    'app_request_duration_seconds',
    'Request duration by method and path',
    ['method', 'path'],
    buckets=[0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0]
)

ACTIVE_USERS = Gauge(
    'app_active_users',
    'Number of active users'
)

DB_CONNECTIONS = Gauge(
    'app_db_connections',
    'Number of database connections in use'
)

API_RESPONSE_SIZE = Histogram(
    'app_response_size_bytes',
    'Response size in bytes by method and path',
    ['method', 'path']
)

ERROR_COUNT = Counter(
    'app_errors_total',
    'Total errors by type',
    ['error_type', 'path']
)


class MetricsMiddleware:
    """
    Middleware to collect metrics for each request
    """

    def __init__(self, app=None):  # Accept app parameter for compatibility
        self.app = app
        self.logger = logging.getLogger(__name__)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        request = Request(scope)
        start_time = time.time()

        # Capture response status code and headers
        response_status = None
        response_headers = {}

        async def send_wrapper(message):
            nonlocal response_status
            if message["type"] == "http.response.start":
                response_status = message["status"]
                response_headers.update(dict(message["headers"]))
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as e:
            # Increment error counter
            ERROR_COUNT.labels(
                error_type=type(e).__name__,
                path=request.url.path
            ).inc()
            raise
        finally:
            # Calculate duration
            duration = time.time() - start_time

            # Record metrics
            REQUEST_DURATION.labels(
                method=request.method,
                path=request.url.path
            ).observe(duration)

            REQUEST_COUNT.labels(
                method=request.method,
                path=request.url.path,
                status_code=response_status or 500
            ).inc()

            # Get content length from response headers
            content_length = None
            for header_name, header_value in response_headers.items():
                if header_name.decode('utf-8').lower() == 'content-length':
                    content_length = header_value.decode('utf-8')
                    break

            if content_length:
                API_RESPONSE_SIZE.labels(
                    method=request.method,
                    path=request.url.path
                ).observe(int(content_length))


def monitor_api_call(endpoint_name: str):
    """
    Decorator to monitor specific API calls
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time

                # Record the duration for this specific endpoint
                REQUEST_DURATION.labels(
                    method='INTERNAL',
                    path=endpoint_name
                ).observe(duration)

                return result
            except Exception as e:
                ERROR_COUNT.labels(
                    error_type=type(e).__name__,
                    path=endpoint_name
                ).inc()
                raise

        return wrapper
    return decorator


def start_metrics_server(port: int = 8001):
    """
    Start the Prometheus metrics server on the specified port
    """
    try:
        start_http_server(port)
        logging.info(f"Metrics server started on port {port}")
    except Exception as e:
        logging.error(f"Failed to start metrics server: {e}")


# Initialize the registry
def init_metrics():
    """
    Initialize metrics collection
    """
    # Add any startup metrics here
    pass