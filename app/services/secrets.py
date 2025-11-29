"""AWS Secrets Manager service for API key management."""

import json
from typing import List

import boto3
import structlog
from botocore.exceptions import ClientError

from app.config import config

logger = structlog.get_logger()


async def fetch_api_keys() -> List[str]:
    """
    Fetch API keys from AWS Secrets Manager.

    Returns:
        List[str]: List of valid API keys

    Raises:
        ClientError: If Secrets Manager operation fails
        ValueError: If secret format is invalid
    """
    try:
        # Create Secrets Manager client
        client = boto3.client(
            "secretsmanager",
            region_name=config.aws_region
        )

        # Fetch secret value
        logger.info("fetching_secret", secret_name=config.api_keys_secret_name)
        response = client.get_secret_value(SecretId=config.api_keys_secret_name)

        # Parse secret string
        secret_string = response.get("SecretString")
        if not secret_string:
            raise ValueError("Secret value is empty")

        secret_data = json.loads(secret_string)

        # Extract API keys
        api_keys = secret_data.get("api_keys")
        if not api_keys:
            raise ValueError("Secret does not contain 'api_keys' field")

        if not isinstance(api_keys, list):
            raise ValueError("'api_keys' field must be a list")

        # Filter out empty keys
        valid_keys = [key for key in api_keys if key and isinstance(key, str)]

        if not valid_keys:
            raise ValueError("No valid API keys found in secret")

        logger.info("secret_fetched", count=len(valid_keys))
        return valid_keys

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]

        if error_code == "ResourceNotFoundException":
            logger.error(
                "secret_not_found",
                secret_name=config.api_keys_secret_name,
            )
        elif error_code == "AccessDeniedException":
            logger.error(
                "secret_access_denied",
                secret_name=config.api_keys_secret_name,
            )
        else:
            logger.error(
                "secrets_manager_error",
                error_code=error_code,
                error_message=error_message,
            )

        raise

    except json.JSONDecodeError as e:
        logger.error("secret_json_parse_error", error=str(e))
        raise ValueError(f"Invalid JSON in secret: {e}")

    except Exception as e:
        logger.error("unexpected_error", operation="fetch_api_keys", error=str(e))
        raise
