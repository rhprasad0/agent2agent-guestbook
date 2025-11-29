"""Structured JSON logging with OpenTelemetry trace correlation.

This module configures logging to output JSON-formatted logs that include
trace context (trace_id, span_id) for correlation with AWS X-Ray traces.

Usage:
    # At application startup (after setup_tracing):
    from app.logging_config import setup_logging
    setup_logging()
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict

from opentelemetry import trace


class TraceContextFilter(logging.Filter):
    """
    Logging filter that injects OpenTelemetry trace context into log records.

    Adds the following attributes to each log record:
    - trace_id: AWS X-Ray formatted trace ID
    - span_id: Current span ID
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add trace context to the log record."""
        span = trace.get_current_span()

        if span is not None:
            span_context = span.get_span_context()
            if span_context.is_valid:
                # Convert to X-Ray format: 1-{timestamp}-{random}
                trace_id_hex = format(span_context.trace_id, "032x")
                record.trace_id = f"1-{trace_id_hex[:8]}-{trace_id_hex[8:]}"
                record.span_id = format(span_context.span_id, "016x")
            else:
                record.trace_id = None
                record.span_id = None
        else:
            record.trace_id = None
            record.span_id = None

        return True


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for CloudWatch Logs Insights compatibility.

    Outputs logs in JSON format with consistent field names for easy
    querying in CloudWatch Logs Insights.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as JSON."""
        # Build the log entry
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add trace context if available
        trace_id = getattr(record, "trace_id", None)
        span_id = getattr(record, "span_id", None)

        if trace_id:
            log_entry["trace_id"] = trace_id
        if span_id:
            log_entry["span_id"] = span_id

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields from the record
        # These come from logger.info("msg", extra={"key": "value"})
        standard_attrs = {
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "pathname", "process", "processName", "relativeCreated",
            "stack_info", "exc_info", "exc_text", "thread", "threadName",
            "trace_id", "span_id", "message", "taskName"
        }

        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                try:
                    # Ensure the value is JSON serializable
                    json.dumps(value)
                    log_entry[key] = value
                except (TypeError, ValueError):
                    log_entry[key] = str(value)

        return json.dumps(log_entry)


def setup_logging(level: str = "INFO") -> None:
    """
    Configure structured JSON logging with trace correlation.

    This replaces the default logging configuration with JSON output
    that includes OpenTelemetry trace context.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Get the root logger
    root_logger = logging.getLogger()

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create JSON handler for stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    handler.addFilter(TraceContextFilter())

    # Configure root logger
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Reduce noise from verbose libraries
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("opentelemetry").setLevel(logging.WARNING)

    logging.info("Structured JSON logging configured with trace correlation")

