"""Structured JSON logging with OpenTelemetry trace correlation.

This module configures structlog for JSON-formatted logging that includes
trace context (trace_id, span_id) for correlation with AWS X-Ray traces.

Usage:
    # At application startup (after setup_tracing):
    from app.logging_config import configure_logging
    configure_logging()
"""

import logging
import os

import structlog
from opentelemetry import trace


def get_trace_context() -> dict:
    """Extract trace context from current OpenTelemetry span.
    
    Returns:
        dict: Contains trace_id (X-Ray format) and span_id, or None values if no valid span.
    """
    span = trace.get_current_span()
    ctx = span.get_span_context()

    if ctx.is_valid:
        # Format trace_id as X-Ray format: 1-{first 8 hex}-{remaining 24 hex}
        trace_id_hex = format(ctx.trace_id, "032x")
        xray_trace_id = f"1-{trace_id_hex[:8]}-{trace_id_hex[8:]}"
        return {
            "trace_id": xray_trace_id,
            "span_id": format(ctx.span_id, "016x"),
        }
    return {"trace_id": None, "span_id": None}


def add_trace_context(logger, method_name, event_dict):
    """Structlog processor to add OpenTelemetry trace context."""
    event_dict.update(get_trace_context())
    return event_dict


def add_service_context(logger, method_name, event_dict):
    """Structlog processor to add service metadata."""
    event_dict["service"] = os.getenv("OTEL_SERVICE_NAME", "guestbook")
    event_dict["environment"] = os.getenv("ENVIRONMENT", "unknown")
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog for JSON output with trace context.

    This replaces the default logging configuration with JSON output
    that includes OpenTelemetry trace context and service metadata.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert level string to logging level
    log_level = getattr(logging, level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            add_service_context,
            add_trace_context,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Suppress uvicorn access logs (we log requests ourselves via middleware)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # Reduce noise from verbose libraries
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("opentelemetry").setLevel(logging.WARNING)

    # Log that structured logging is configured
    logger = structlog.get_logger()
    logger.info("logging_configured", level=level)


def get_logger(name: str = None):
    """Get a structlog logger instance.
    
    Args:
        name: Optional logger name (not used by structlog but kept for compatibility)
        
    Returns:
        A structlog bound logger instance
    """
    return structlog.get_logger()


# Legacy alias for backward compatibility
setup_logging = configure_logging
