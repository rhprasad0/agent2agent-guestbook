"""Request logging middleware for structured security-relevant logging."""

import hashlib
import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


logger = structlog.get_logger()


def hash_api_key(api_key: str) -> str:
    """Create a short hash of API key for logging (don't log full key).
    
    Args:
        api_key: The full API key string
        
    Returns:
        str: Hashed identifier like "api-key-hash:a1b2c3d4" or "anonymous"
    """
    if not api_key:
        return "anonymous"
    return f"api-key-hash:{hashlib.sha256(api_key.encode()).hexdigest()[:8]}"


def determine_action(method: str, path: str) -> str:
    """Map HTTP method and path to a business action name.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        path: Request URL path
        
    Returns:
        str: Business action name in snake_case
    """
    # A2A API v1 endpoints
    if path == "/api/v1/messages":
        if method == "GET":
            return "list_messages"
        elif method == "POST":
            return "create_message"
    elif path.startswith("/api/v1/messages/"):
        if method == "GET":
            return "get_message"
        elif method == "DELETE":
            return "delete_message"
    
    # Public endpoints
    elif path == "/api/public/messages":
        return "list_public_messages"
    
    # System endpoints
    elif path == "/health":
        return "health_check"
    elif path == "/metrics":
        return "metrics"
    elif path == "/.well-known/agent.json":
        return "get_capabilities"
    
    # Default: derive from method and path
    sanitized_path = path.replace("/", "_").strip("_")
    return f"{method.lower()}_{sanitized_path}"


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request, handling X-Forwarded-For from ALB.
    
    Args:
        request: The incoming HTTP request
        
    Returns:
        str: Client IP address
    """
    # X-Forwarded-For header from ALB/proxy
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For may contain multiple IPs; take the first (original client)
        return forwarded_for.split(",")[0].strip()
    
    # Fall back to direct client IP
    if request.client:
        return request.client.host
    
    return "unknown"


def extract_user_identifier(request: Request) -> str:
    """Extract user identifier from request headers.
    
    Supports both X-API-Key header and Authorization Bearer token.
    
    Args:
        request: The incoming HTTP request
        
    Returns:
        str: Hashed user identifier or "anonymous"
    """
    # Check X-API-Key header first
    api_key = request.headers.get("X-API-Key", "")
    if api_key:
        return hash_api_key(api_key)
    
    # Check Authorization Bearer token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        if token:
            return hash_api_key(token)
    
    return "anonymous"


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests with security context.
    
    Logs structured JSON entries for each request with:
    - User identifier (hashed API key)
    - Business action name
    - Request path and method
    - Response status code
    - Request duration
    - Client IP address
    
    Health checks and metrics endpoints are excluded to reduce noise.
    """

    # Endpoints to exclude from logging (high-frequency, low-value)
    EXCLUDED_PATHS = {"/health", "/metrics"}

    async def dispatch(self, request: Request, call_next) -> Response:
        """Process request and log with security context.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response from next handler
        """
        start_time = time.perf_counter()

        # Extract security context before processing
        user = extract_user_identifier(request)
        client_ip = get_client_ip(request)
        path = request.url.path
        method = request.method

        # Process the request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Determine business action
        action = determine_action(method, path)

        # Log the request (skip excluded paths to reduce noise)
        if path not in self.EXCLUDED_PATHS:
            logger.info(
                "api_request",
                user=user,
                action=action,
                path=path,
                method=method,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                client_ip=client_ip,
            )

        return response


