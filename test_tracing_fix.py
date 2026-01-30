"""
Test script to verify the OpenTelemetry tracing fix
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

# Test the corrected tracing module
try:
    from src.utils.tracing import setup_tracing, instrument_libraries, trace_function
    print("✅ Successfully imported tracing utilities")

    # Try to initialize a basic tracer
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.resources import Resource

    # Create a basic tracer provider
    tracer_provider = TracerProvider(
        resource=Resource.create({
            "service.name": "regal-pos-backend-test",
            "environment": "test",
            "version": "1.0.0"
        })
    )
    trace.set_tracer_provider(tracer_provider)
    print("✅ Successfully created tracer provider")

    # Test the trace_function decorator
    @trace_function("test_function")
    def test_func():
        return "test"

    result = test_func()
    print(f"✅ Successfully used trace_function decorator: {result}")

    print("\n🎉 All tracing imports and basic functionality working correctly!")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("This indicates the tracing module still has issues.")

except Exception as e:
    print(f"❌ Error during testing: {e}")
    print("There may still be issues with the tracing module.")