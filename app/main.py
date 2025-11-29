"""FastAPI application entry point for A2A Guestbook."""

# Initialize tracing FIRST - before any other imports that might use boto3
# This ensures all AWS SDK calls are automatically instrumented
from app.tracing import setup_tracing, instrument_fastapi, get_current_trace_id
setup_tracing()

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import config
from app.logging_config import setup_logging
from app.middleware import (
    AuthMiddleware,
    load_api_keys,
    start_key_refresh_task,
    stop_key_refresh_task,
    limiter,
)
from app.routers import a2a_router, public_router

# Configure structured JSON logging with trace correlation
setup_logging(level=config.log_level)

logger = logging.getLogger(__name__)


class TraceIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add X-Amzn-Trace-Id header to responses.

    This allows clients to correlate their requests with X-Ray traces
    for debugging and monitoring purposes.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add trace ID to response headers if available
        trace_id = get_current_trace_id()
        if trace_id:
            response.headers["X-Amzn-Trace-Id"] = f"Root={trace_id}"

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.

    Handles:
    - Loading API keys from Secrets Manager on startup
    - Starting background task for periodic key refresh
    - Cleanup on shutdown
    """
    # Startup
    logger.info("Starting A2A Guestbook application")
    logger.info(
        "Configuration loaded",
        extra={
            "region": config.aws_region,
            "table": config.dynamodb_table_name,
            "rate_limit": config.rate_limit_per_minute,
        }
    )

    try:
        # Load API keys from Secrets Manager
        await load_api_keys()
        logger.info("API keys loaded successfully")

        # Start background task for periodic key refresh
        start_key_refresh_task()
        logger.info("Background key refresh task started")

    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down A2A Guestbook application")
    stop_key_refresh_task()
    logger.info("Application shutdown complete")


# Initialize FastAPI application
app = FastAPI(
    title="A2A Guestbook",
    description="Agent-to-Agent protocol guestbook for AI agent communication",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Instrument FastAPI with OpenTelemetry for automatic HTTP tracing
instrument_fastapi(app)

# Add rate limiter state to app
app.state.limiter = limiter

# Register rate limit exceeded handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Handle all unhandled exceptions with structured error response.

    Args:
        request: The request that caused the exception
        exc: The exception that was raised

    Returns:
        JSONResponse with error details including trace ID for debugging
    """
    trace_id = get_current_trace_id()

    logger.error(
        f"Unhandled exception: {exc}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
            "trace_id": trace_id,
        },
        exc_info=True
    )

    # Include trace ID in error response for debugging
    error_details = {}
    if trace_id:
        error_details["trace_id"] = trace_id

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "details": error_details,
            }
        },
    )


# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for public guestbook
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trace ID response header middleware
app.add_middleware(TraceIdMiddleware)

# Add authentication middleware
app.add_middleware(AuthMiddleware)

# Register routers
app.include_router(a2a_router)
app.include_router(public_router)

# Instrument app with Prometheus
Instrumentator().instrument(app).expose(app)

# Mount static files for web UI (must be last to avoid route conflicts)
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")


# Application entry point
if __name__ == "__main__":
    import uvicorn

    logger.info(f"Starting server on port {config.port}")
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.port,
        log_level=config.log_level.lower(),
    )
