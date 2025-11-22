"""Rate limiting configuration for A2A Guestbook application."""

import logging
from typing import Callable

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import config

logger = logging.getLogger(__name__)


def get_api_key_identifier(request: Request) -> str:
    """
    Extract API key from request for rate limiting.

    Uses the API key as the identifier for rate limiting, allowing
    per-key limits. Falls back to IP address for unauthenticated requests.

    Args:
        request: Incoming HTTP request

    Returns:
        str: Identifier for rate limiting (API key or IP address)
    """
    # Extract Authorization header
    auth_header = request.headers.get("Authorization", "")

    # Parse Bearer token
    if auth_header.startswith("Bearer "):
        api_key = auth_header[7:]  # Remove "Bearer " prefix
        if api_key:
            # Use first 8 characters of API key for logging (sanitized)
            logger.debug(f"Rate limiting by API key: {api_key[:8]}...")
            return f"api_key:{api_key}"

    # Fall back to IP address for unauthenticated requests
    ip_address = get_remote_address(request)
    logger.debug(f"Rate limiting by IP address: {ip_address}")
    return f"ip:{ip_address}"


# Initialize rate limiter
limiter = Limiter(
    key_func=get_api_key_identifier,
    default_limits=[],  # No default limits, apply per-route
    storage_uri="memory://",  # In-memory storage (suitable for single instance)
)


def get_rate_limit_string() -> str:
    """
    Get rate limit string for authenticated endpoints.

    Returns:
        str: Rate limit in slowapi format (e.g., "10/minute")
    """
    return f"{config.rate_limit_per_minute}/minute"


def should_apply_rate_limit(request: Request) -> bool:
    """
    Determine if rate limiting should be applied to the request.

    Rate limiting is only applied to authenticated endpoints (those requiring API keys).

    Args:
        request: Incoming HTTP request

    Returns:
        bool: True if rate limiting should be applied
    """
    path = request.url.path

    # Apply rate limiting to authenticated API endpoints
    authenticated_prefixes = [
        "/api/v1/",
    ]

    return any(path.startswith(prefix) for prefix in authenticated_prefixes)
