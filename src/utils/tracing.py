"""
Distributed tracing utilities for the Regal POS Backend
Implements OpenTelemetry tracing for request flows
"""
import os
import logging
from functools import wraps
from typing import Callable, Any

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.propagate import set_global_textmap
from opentelemetry.baggage.propagation import W3CBaggagePropagator
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)

# Initialize tracer provider
tracer_provider = TracerProvider(
    resource=Resource.create({
        "service.name": "regal-pos-backend",
        "environment": os.getenv("ENVIRONMENT", "development"),
        "version": "1.0.0"
    })
)

# Set the global tracer provider
trace.set_tracer_provider(tracer_provider)

# Set global propagators
from opentelemetry.propagators.composite import CompositePropagator
propagator = CompositePropagator([W3CBaggagePropagator(), TraceContextTextMapPropagator()])
set_global_textmap(propagator)

# Configure exporter (OTLP collector)
try:
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318/v1/traces")  # Using HTTP endpoint
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
except Exception as e:
    logger.warning(f"Failed to initialize OTLP exporter: {e}. Tracing may not work.")

# Global tracer
tracer = trace.get_tracer(__name__)


def instrument_libraries():
    """
    Instrument common libraries for distributed tracing
    """
    try:
        # Instrument SQLAlchemy
        SQLAlchemyInstrumentor().instrument()

        # Instrument Redis
        RedisInstrumentor().instrument()

        # Instrument requests
        RequestsInstrumentor().instrument()

        logger.info("Successfully instrumented libraries for distributed tracing")
    except Exception as e:
        logger.error(f"Failed to instrument libraries for tracing: {e}")


def trace_function(span_name: str = None):
    """
    Decorator to add tracing to specific functions
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            name = span_name or f"{func.__module__}.{func.__name__}"

            with tracer.start_as_current_span(name) as span:
                # Add function parameters as attributes
                for i, arg in enumerate(args):
                    span.set_attribute(f"arg.{i}", str(arg)[:100])  # Limit length

                for key, value in kwargs.items():
                    span.set_attribute(f"kwarg.{key}", str(value)[:100])  # Limit length

                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("result.success", True)
                    return result
                except Exception as e:
                    span.set_attribute("result.success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e)[:200])
                    raise

        return wrapper
    return decorator


def add_span_attributes(**attributes):
    """
    Add attributes to the current span
    """
    current_span = trace.get_current_span()
    for key, value in attributes.items():
        current_span.set_attribute(key, str(value))


def add_event_to_span(name: str, attributes: dict = None):
    """
    Add an event to the current span
    """
    current_span = trace.get_current_span()
    current_span.add_event(name, attributes or {})


def get_trace_context():
    """
    Get the current trace context
    """
    current_span = trace.get_current_span()
    span_context = current_span.get_span_context()

    return {
        "trace_id": format(span_context.trace_id, "032x"),
        "span_id": format(span_context.span_id, "016x"),
        "trace_flags": span_context.trace_flags,
        "is_valid": span_context.is_valid
    }


def setup_tracing(app):
    """
    Set up tracing for the FastAPI application
    """
    try:
        # Instrument libraries
        instrument_libraries()

        # Instrument the app
        FastAPIInstrumentor.instrument_app(app)

        logger.info("Tracing setup completed successfully")
        return app  # Return the app directly
    except Exception as e:
        logger.error(f"Failed to setup tracing: {e}")
        return app