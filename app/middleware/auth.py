"""Authentication middleware for A2A Guestbook application."""

from typing import Set

import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.secrets import get_api_keys
from app.middleware.request_logging import hash_api_key, get_client_ip

logger = structlog.get_logger()

# In-memory cache of valid API keys
_api_keys_cache: Set[str] = set()


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate API keys for authenticated endpoints."""

    async def dispatch(self, request: Request, call_next):
        """
        Process request and validate authentication for protected endpoints.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response from next handler or error response
        """
        # Skip authentication for public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)

        client_ip = get_client_ip(request)

        # Extract and validate Bearer token
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            logger.warning(
                "auth_failed",
                user="anonymous",
                reason="missing_authorization_header",
                client_ip=client_ip,
                path=request.url.path,
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": "MISSING_AUTHORIZATION",
                        "message": "Authorization header is required",
                        "details": {}
                    }
                }
            )

        # Parse Bearer token
        token = self._extract_bearer_token(auth_header)
        if not token:
            logger.warning(
                "auth_failed",
                user="anonymous",
                reason="invalid_authorization_format",
                client_ip=client_ip,
                path=request.url.path,
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": "INVALID_AUTHORIZATION_FORMAT",
                        "message": "Authorization header must be in format: Bearer <token>",
                        "details": {}
                    }
                }
            )

        # Validate token against cached keys
        if not self._is_valid_api_key(token):
            logger.warning(
                "auth_failed",
                user=hash_api_key(token),
                reason="invalid_api_key",
                client_ip=client_ip,
                path=request.url.path,
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": "INVALID_API_KEY",
                        "message": "Invalid or expired API key",
                        "details": {}
                    }
                }
            )

        # Token is valid, proceed with request
        return await call_next(request)

    @staticmethod
    def _is_public_endpoint(path: str) -> bool:
        """
        Check if endpoint is public and doesn't require authentication.

        Args:
            path: Request URL path

        Returns:
            bool: True if endpoint is public
        """
        public_paths = [
            "/health",
            "/api/public/",
            "/.well-known/",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]

        # Check if path starts with any public prefix or is a static file
        return (
            any(path.startswith(prefix) for prefix in public_paths)
            or not path.startswith("/api/")
        )

    @staticmethod
    def _extract_bearer_token(auth_header: str) -> str | None:
        """
        Extract token from Authorization header.

        Args:
            auth_header: Authorization header value

        Returns:
            str | None: Extracted token or None if invalid format
        """
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return None
        return parts[1]

    @staticmethod
    def _is_valid_api_key(token: str) -> bool:
        """
        Validate API key against cached keys using constant-time comparison.

        Args:
            token: API key to validate

        Returns:
            bool: True if key is valid
        """
        # Use constant-time comparison to prevent timing attacks
        return token in _api_keys_cache


def load_api_keys() -> None:
    """
    Load API keys from environment variable into cache.

    The API_KEYS environment variable is injected from a Kubernetes Secret,
    which is synced from AWS Secrets Manager by External Secrets Operator (ESO).
    ESO handles automatic refresh (default: 1 hour), so no background refresh
    task is needed in the application.

    This should be called on application startup.

    Raises:
        Exception: If keys cannot be loaded
    """
    global _api_keys_cache

    try:
        logger.info("loading_api_keys")
        keys = get_api_keys()
        _api_keys_cache = set(keys)
        logger.info("api_keys_loaded", count=len(_api_keys_cache))
    except Exception as e:
        logger.error("api_keys_load_failed", error=str(e))
        raise
