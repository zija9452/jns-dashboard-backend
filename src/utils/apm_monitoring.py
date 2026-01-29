"""
Application Performance Monitoring (APM) utilities for the Regal POS Backend
Integrates with Sentry for error tracking and performance monitoring
"""
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging
import os
from typing import Optional, Dict, Any
from contextlib import contextmanager
import time
import functools
from fastapi import Request
from ..config.settings import settings


class APMManager:
    """
    Manager class for Application Performance Monitoring
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.is_initialized = False
        self.performance_monitoring_enabled = settings.prometheus_enabled

    def initialize_apm(self):
        """
        Initialize APM with Sentry
        """
        if not settings.sentry_dsn:
            self.logger.warning("Sentry DSN not configured, APM disabled")
            return False

        try:
            # Initialize Sentry with appropriate integrations
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                integrations=[
                    FastApiIntegration(transaction_style="endpoint"),
                    SqlalchemyIntegration(),
                    RedisIntegration(),
                    LoggingIntegration(
                        level=logging.INFO,
                        event_level=logging.ERROR
                    ),
                ],
                traces_sample_rate=0.2,  # Sample 20% of transactions for performance monitoring
                profiles_sample_rate=0.2,  # Sample 20% of transactions for profiling
                environment=os.getenv("ENVIRONMENT", "development"),
                release=os.getenv("APP_VERSION", "1.0.0"),
                server_name=os.getenv("SERVER_NAME", "regal-pos-backend"),
            )

            self.is_initialized = True
            self.logger.info("APM monitoring initialized successfully with Sentry")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize APM monitoring: {e}")
            return False

    def capture_exception(self, exception: Exception, extra: Optional[Dict[str, Any]] = None):
        """
        Capture an exception with Sentry
        """
        if not self.is_initialized:
            return

        try:
            sentry_sdk.set_extra("additional_data", extra or {})
            sentry_sdk.capture_exception(exception)
        except Exception as e:
            self.logger.error(f"Failed to capture exception in Sentry: {e}")

    def capture_message(self, message: str, level: str = "info"):
        """
        Capture a message with Sentry
        """
        if not self.is_initialized:
            return

        try:
            sentry_sdk.capture_message(message, level=level)
        except Exception as e:
            self.logger.error(f"Failed to capture message in Sentry: {e}")

    @contextmanager
    def monitor_transaction(self, transaction_name: str, op: str = "function"):
        """
        Context manager to monitor a transaction
        """
        if not self.is_initialized:
            yield
            return

        with sentry_sdk.start_transaction(op=op, name=transaction_name):
            yield

    def add_breadcrumb(self, message: str, category: str = "custom", level: str = "info"):
        """
        Add a breadcrumb to the current transaction
        """
        if not self.is_initialized:
            return

        sentry_sdk.add_breadcrumb(
            message=message,
            category=category,
            level=level
        )

    def set_user_context(self, user_id: str, email: Optional[str] = None, username: Optional[str] = None):
        """
        Set user context for Sentry
        """
        if not self.is_initialized:
            return

        sentry_sdk.set_user({
            "id": user_id,
            "email": email,
            "username": username
        })

    def set_tag(self, key: str, value: str):
        """
        Set a tag for the current transaction
        """
        if not self.is_initialized:
            return

        sentry_sdk.set_tag(key, value)

    def set_extra_context(self, key: str, value: Any):
        """
        Set extra context for the current transaction
        """
        if not self.is_initialized:
            return

        sentry_sdk.set_extra(key, value)


# Global APM manager instance
apm_manager = APMManager()


def measure_performance(func):
    """
    Decorator to measure performance of functions
    """
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        if apm_manager.is_initialized:
            with apm_manager.monitor_transaction(f"{func.__module__}.{func.__name__}"):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    duration = time.time() - start_time
                    apm_manager.set_extra_context("execution_time", duration)
                    return result
                except Exception as e:
                    apm_manager.capture_exception(e)
                    raise
        else:
            # If APM is not initialized, just run the function normally
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                return result
            except Exception as e:
                logging.getLogger(__name__).error(f"Error in {func.__name__}: {e}")
                raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        if apm_manager.is_initialized:
            with apm_manager.monitor_transaction(f"{func.__module__}.{func.__name__}"):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    apm_manager.set_extra_context("execution_time", duration)
                    return result
                except Exception as e:
                    apm_manager.capture_exception(e)
                    raise
        else:
            # If APM is not initialized, just run the function normally
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                return result
            except Exception as e:
                logging.getLogger(__name__).error(f"Error in {func.__name__}: {e}")
                raise

    # Return appropriate wrapper based on whether the function is async
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def add_performance_middleware(app):
    """
    Add performance monitoring middleware to FastAPI app
    """
    @app.middleware("http")
    async def performance_monitoring_middleware(request: Request, call_next):
        if apm_manager.is_initialized:
            # Set transaction name based on the endpoint
            transaction_name = f"{request.method} {request.url.path}"

            with sentry_sdk.start_transaction(op="http.server", name=transaction_name):
                # Add request context
                apm_manager.set_extra_context("request_method", request.method)
                apm_manager.set_extra_context("request_path", request.url.path)

                if request.headers.get("user-agent"):
                    apm_manager.set_extra_context("user_agent", request.headers.get("user-agent"))

                start_time = time.time()
                try:
                    response = await call_next(request)
                    duration = time.time() - start_time

                    # Add performance data
                    apm_manager.set_extra_context("response_status", response.status_code)
                    apm_manager.set_extra_context("response_time", duration)

                    return response
                except Exception as e:
                    # Capture the exception with additional context
                    apm_manager.capture_exception(
                        e,
                        extra={
                            "request_method": request.method,
                            "request_path": request.url.path,
                            "response_time": time.time() - start_time
                        }
                    )
                    raise
        else:
            # If APM not initialized, just proceed normally
            response = await call_next(request)
            return response


def log_performance_metric(metric_name: str, value: float, tags: Optional[Dict[str, str]] = None):
    """
    Log a performance metric
    """
    if apm_manager.is_initialized:
        apm_manager.set_tag("metric_name", metric_name)
        if tags:
            for key, val in tags.items():
                apm_manager.set_tag(key, val)

        apm_manager.set_extra_context(metric_name, value)

        # Add breadcrumb for the metric
        apm_manager.add_breadcrumb(
            message=f"{metric_name}: {value}",
            category="performance",
            level="info"
        )


def start_performance_transaction(name: str, op: str = "custom"):
    """
    Start a performance monitoring transaction
    """
    if apm_manager.is_initialized:
        return sentry_sdk.start_transaction(op=op, name=name)
    else:
        # Return a dummy context manager if APM is not initialized
        from contextlib import contextmanager

        @contextmanager
        def dummy_context():
            yield

        return dummy_context()


# Initialize APM when module is loaded
def setup_apm():
    """
    Setup APM monitoring
    """
    if settings.sentry_dsn:
        apm_manager.initialize_apm()
    else:
        logging.getLogger(__name__).warning("Sentry DSN not configured, APM monitoring disabled")


# Call setup function
setup_apm()


# Example usage functions
def example_usage():
    """
    Example of how to use APM monitoring
    """

    # Example 1: Manual exception capture
    try:
        result = 1 / 0
    except ZeroDivisionError as e:
        apm_manager.capture_exception(e, extra={"operation": "division", "value": 0})

    # Example 2: Using the performance decorator
    @measure_performance
    async def example_async_function():
        import asyncio
        await asyncio.sleep(1)  # Simulate work
        return "completed"

    # Example 3: Manual performance measurement
    start_time = time.time()
    # ... do some work ...
    duration = time.time() - start_time
    log_performance_metric("example_operation_time", duration, {"operation": "example"})