"""OpenTelemetry tracing configuration for AWS X-Ray integration.

This module configures distributed tracing using OpenTelemetry with AWS X-Ray
as the backend. Traces are exported via OTLP to the CloudWatch Agent.

Usage:
    # At the very start of your application (before other imports):
    from app.tracing import setup_tracing
    setup_tracing()

    # After creating FastAPI app:
    from app.tracing import instrument_fastapi
    instrument_fastapi(app)
"""

import logging
import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.extension.aws.trace import AwsXRayIdGenerator
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.aws import AwsXRayPropagator

logger = logging.getLogger(__name__)

# Global flag to prevent double initialization
_tracing_initialized = False


def setup_tracing() -> None:
    """
    Initialize OpenTelemetry tracing with AWS X-Ray configuration.

    This function should be called once at application startup, before
    any other code that might create spans or use boto3.

    Environment variables used:
        - OTEL_SERVICE_NAME: Service name for traces (default: "guestbook")
        - OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint URL
        - ENVIRONMENT: Deployment environment (default: "dev")
    """
    global _tracing_initialized

    if _tracing_initialized:
        logger.debug("Tracing already initialized, skipping")
        return

    # Get configuration from environment
    service_name = os.getenv("OTEL_SERVICE_NAME", "guestbook")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    environment = os.getenv("ENVIRONMENT", "dev")

    if not otlp_endpoint:
        logger.warning(
            "OTEL_EXPORTER_OTLP_ENDPOINT not set, tracing will be disabled. "
            "Set this to enable X-Ray tracing (e.g., http://cloudwatch-agent.amazon-cloudwatch:4317)"
        )
        _tracing_initialized = True
        return

    try:
        # Create resource with service metadata
        resource = Resource.create({
            SERVICE_NAME: service_name,
            "deployment.environment": environment,
            "service.namespace": "guestbook",
        })

        # Create tracer provider with AWS X-Ray ID generator
        # X-Ray requires specific trace ID format (starts with timestamp)
        provider = TracerProvider(
            resource=resource,
            id_generator=AwsXRayIdGenerator(),
        )

        # Configure OTLP exporter to send traces to CloudWatch Agent
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            insecure=True,  # CloudWatch Agent uses HTTP within cluster
        )

        # Use batch processor for efficient trace export
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        # Set as global tracer provider
        trace.set_tracer_provider(provider)

        # Set AWS X-Ray propagator for distributed tracing
        set_global_textmap(AwsXRayPropagator())

        # Instrument boto3/botocore for AWS SDK tracing
        _instrument_boto()

        _tracing_initialized = True
        logger.info(
            f"OpenTelemetry tracing initialized: service={service_name}, "
            f"endpoint={otlp_endpoint}, environment={environment}"
        )

    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}", exc_info=True)
        _tracing_initialized = True  # Prevent retry loops


def _instrument_boto() -> None:
    """Instrument boto3 and botocore for automatic AWS SDK tracing."""
    try:
        from opentelemetry.instrumentation.botocore import BotocoreInstrumentor

        BotocoreInstrumentor().instrument()
        logger.debug("Botocore instrumentation enabled")

    except Exception as e:
        logger.warning(f"Failed to instrument botocore: {e}")


def instrument_fastapi(app) -> None:
    """
    Instrument a FastAPI application for automatic HTTP tracing.

    This adds automatic span creation for all HTTP requests, including:
    - Request method and path
    - Response status code
    - Request/response headers (configurable)

    Args:
        app: FastAPI application instance
    """
    if not _tracing_initialized:
        logger.warning("Tracing not initialized, call setup_tracing() first")
        return

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumentation enabled")

    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}", exc_info=True)


def get_current_trace_id() -> Optional[str]:
    """
    Get the current trace ID in AWS X-Ray format.

    Returns:
        X-Ray formatted trace ID (e.g., "1-6cc26f91-65fdeff175a58f4ed6f36ef5")
        or None if no active span.
    """
    span = trace.get_current_span()
    if span is None:
        return None

    span_context = span.get_span_context()
    if not span_context.is_valid:
        return None

    # Convert OpenTelemetry trace ID to X-Ray format
    # X-Ray format: 1-{8 hex digits timestamp}-{24 hex digits random}
    trace_id_hex = format(span_context.trace_id, "032x")

    # X-Ray trace IDs start with version (1), then timestamp, then random
    return f"1-{trace_id_hex[:8]}-{trace_id_hex[8:]}"


def get_current_span_id() -> Optional[str]:
    """
    Get the current span ID.

    Returns:
        Span ID as hex string or None if no active span.
    """
    span = trace.get_current_span()
    if span is None:
        return None

    span_context = span.get_span_context()
    if not span_context.is_valid:
        return None

    return format(span_context.span_id, "016x")


def get_tracer(name: str = __name__):
    """
    Get a tracer instance for creating custom spans.

    Args:
        name: Tracer name (typically __name__ of the calling module)

    Returns:
        OpenTelemetry Tracer instance

    Example:
        tracer = get_tracer(__name__)
        with tracer.start_as_current_span("my-operation") as span:
            span.set_attribute("key", "value")
            # ... do work ...
    """
    return trace.get_tracer(name)

