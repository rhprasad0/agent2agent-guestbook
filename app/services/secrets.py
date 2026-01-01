"""API key management - reads from environment variable (injected via K8s Secret)."""

import json
from typing import List

import structlog

from app.config import config

logger = structlog.get_logger()


def get_api_keys() -> List[str]:
    """
    Get API keys from environment variable.

    The API_KEYS environment variable is injected from a Kubernetes Secret,
    which is synced from AWS Secrets Manager by External Secrets Operator.

    Returns:
        List[str]: List of valid API keys

    Raises:
        ValueError: If API_KEYS format is invalid
    """
    try:
        # Parse JSON array from environment variable
        api_keys = json.loads(config.api_keys)

        if not isinstance(api_keys, list):
            raise ValueError("API_KEYS must be a JSON array")

        # Filter out empty keys
        valid_keys = [key for key in api_keys if key and isinstance(key, str)]

        if not valid_keys:
            raise ValueError("No valid API keys found in API_KEYS")

        logger.info("api_keys_loaded", count=len(valid_keys))
        return valid_keys

    except json.JSONDecodeError as e:
        logger.error("api_keys_json_parse_error", error=str(e))
        raise ValueError(f"Invalid JSON in API_KEYS: {e}")

    except Exception as e:
        logger.error("unexpected_error", operation="get_api_keys", error=str(e))
        raise
