"""
Retry mechanisms for database connections and other transient operations
"""
import asyncio
import logging
import random
from functools import wraps
from typing import Callable, Type, Any, Optional
from sqlalchemy.exc import DisconnectionError, OperationalError
from sqlmodel import Session
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log
)

logger = logging.getLogger(__name__)


class RetryConfig:
    """
    Configuration class for retry mechanisms
    """
    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2,
        jitter: bool = True,
        multiplier: float = 1.0
    ):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.multiplier = multiplier


def retry_with_config(
    config: RetryConfig,
    retryable_exceptions: tuple = (DisconnectionError, OperationalError)
):
    """
    Decorator to add retry logic with custom configuration
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        @retry(
            stop=stop_after_attempt(config.max_attempts),
            wait=wait_exponential(
                multiplier=config.multiplier,
                min=config.initial_delay,
                max=config.max_delay
            ),
            retry=retry_if_exception_type(retryable_exceptions),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            after=after_log(logger, logging.INFO)
        )
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper
    return decorator


def database_retry(
    max_attempts: int = 3,
    initial_delay: float = 0.5,
    max_delay: float = 10.0
):
    """
    Specific retry decorator for database operations
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        max_delay=max_delay
    )

    return retry_with_config(
        config,
        retryable_exceptions=(DisconnectionError, OperationalError)
    )


@database_retry(max_attempts=3, initial_delay=0.5)
def execute_db_operation(session: Session, operation_func: Callable, *args, **kwargs):
    """
    Execute a database operation with retry logic

    Args:
        session: Database session
        operation_func: Function to execute with session
        *args, **kwargs: Arguments to pass to operation_func

    Returns:
        Result of the operation
    """
    try:
        result = operation_func(session, *args, **kwargs)
        session.commit()
        return result
    except Exception as e:
        session.rollback()
        logger.error(f"Database operation failed: {str(e)}")
        raise


class DatabaseRetryManager:
    """
    Manager class for handling database retries
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    async def execute_with_retry_async(self, operation_func: Callable, *args, **kwargs):
        """
        Execute an async database operation with retry logic
        """
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                return await operation_func(*args, **kwargs)
            except (DisconnectionError, OperationalError) as e:
                last_exception = e
                if attempt < self.config.max_attempts - 1:  # Not the last attempt
                    delay = min(
                        self.config.initial_delay * (self.config.exponential_base ** attempt),
                        self.config.max_delay
                    )

                    if self.config.jitter:
                        delay += random.uniform(0, 0.1 * delay)  # Add jitter

                    logger.warning(
                        f"Database operation failed (attempt {attempt + 1}/{self.config.max_attempts}): {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Database operation failed after {self.config.max_attempts} attempts: {str(e)}")

        raise last_exception

    def execute_with_retry(self, operation_func: Callable, *args, **kwargs):
        """
        Execute a sync database operation with retry logic
        """
        last_exception = None

        for attempt in range(self.config.max_attempts):
            try:
                return operation_func(*args, **kwargs)
            except (DisconnectionError, OperationalError) as e:
                last_exception = e
                if attempt < self.config.max_attempts - 1:  # Not the last attempt
                    delay = min(
                        self.config.initial_delay * (self.config.exponential_base ** attempt),
                        self.config.max_delay
                    )

                    if self.config.jitter:
                        delay += random.uniform(0, 0.1 * delay)  # Add jitter

                    logger.warning(
                        f"Database operation failed (attempt {attempt + 1}/{self.config.max_attempts}): {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Database operation failed after {self.config.max_attempts} attempts: {str(e)}")

        raise last_exception


# Global retry manager instance
db_retry_manager = DatabaseRetryManager()


def retry_connection(func: Callable) -> Callable:
    """
    Decorator to add retry logic to connection functions
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return db_retry_manager.execute_with_retry(func, *args, **kwargs)
    return wrapper


def retry_connection_async(func: Callable) -> Callable:
    """
    Async version of the retry decorator
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        return await db_retry_manager.execute_with_retry_async(func, *args, **kwargs)
    return async_wrapper


# Circuit Breaker Pattern Implementation
class CircuitBreakerState:
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker pattern implementation
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.logger = logging.getLogger(__name__)

    def call(self, func: Callable, *args, **kwargs):
        """
        Call a function with circuit breaker protection
        """
        if self.state == CircuitBreakerState.OPEN:
            # Check if timeout has passed
            import time
            if (time.time() - self.last_failure_time) >= self.timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self.logger.info("Circuit breaker transitioning to HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)

            if self.state == CircuitBreakerState.HALF_OPEN:
                self.logger.info("Circuit breaker transitioning to CLOSED state after successful call")

            # Reset on success
            self.failure_count = 0
            self.state = CircuitBreakerState.CLOSED
            return result

        except Exception as e:
            self.on_failure()
            raise e

    def on_failure(self):
        """
        Handle failure and update circuit breaker state
        """
        self.failure_count += 1
        import time
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold and self.state != CircuitBreakerState.OPEN:
            self.state = CircuitBreakerState.OPEN
            self.logger.warning(f"Circuit breaker transitioning to OPEN state after {self.failure_count} failures")


# Global circuit breaker instance for database operations
db_circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)

# Global circuit breaker for API calls
api_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=30)

# Global circuit breaker for external services
external_service_circuit_breaker = CircuitBreaker(failure_threshold=3, timeout=120)


def circuit_breaker_protect(func: Callable) -> Callable:
    """
    Decorator to protect function calls with circuit breaker
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return db_circuit_breaker.call(func, *args, **kwargs)
    return wrapper


def api_circuit_breaker_protect(func: Callable) -> Callable:
    """
    Decorator to protect API calls with circuit breaker
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return api_circuit_breaker.call(func, *args, **kwargs)
    return wrapper


def external_service_circuit_breaker_protect(func: Callable) -> Callable:
    """
    Decorator to protect external service calls with circuit breaker
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        return external_service_circuit_breaker.call(func, *args, **kwargs)
    return wrapper


def get_circuit_breaker_state(service_name: str = "default"):
    """
    Get the state of a specific circuit breaker
    """
    if service_name == "db":
        cb = db_circuit_breaker
    elif service_name == "api":
        cb = api_circuit_breaker
    elif service_name == "external":
        cb = external_service_circuit_breaker
    else:
        cb = db_circuit_breaker  # default

    return {
        "state": cb.state,
        "failure_count": cb.failure_count,
        "failure_threshold": cb.failure_threshold,
        "timeout": cb.timeout,
        "last_failure_time": cb.last_failure_time
    }


def reset_circuit_breaker(service_name: str = "default"):
    """
    Manually reset a circuit breaker (use with caution in production)
    """
    if service_name == "db":
        cb = db_circuit_breaker
    elif service_name == "api":
        cb = api_circuit_breaker
    elif service_name == "external":
        cb = external_service_circuit_breaker
    else:
        cb = db_circuit_breaker  # default

    cb.state = CircuitBreakerState.CLOSED
    cb.failure_count = 0
    cb.last_failure_time = None


# Example usage functions
async def example_usage():
    """
    Example of how to use the retry mechanisms
    """

    # Example 1: Using the decorator
    @retry_connection_async
    async def get_user_from_db_async(user_id: int):
        # Simulate database operation
        pass

    # Example 2: Using the manager directly
    async def get_user_alternative(user_id: int):
        async def operation():
            # Your database operation here
            pass

        return await db_retry_manager.execute_with_retry_async(operation)

    # Example 3: Using circuit breaker
    @circuit_breaker_protect
    def get_user_with_circuit_breaker(user_id: int):
        # Database operation with circuit breaker protection
        pass

    # Example 4: Using API circuit breaker
    @api_circuit_breaker_protect
    async def call_external_api():
        # External API call with circuit breaker protection
        pass