"""AWS Secrets Manager service for API key management."""

import json
import logging
from typing import List

import boto3
from botocore.exceptions import ClientError

from app.config import config

logger = logging.getLogger(__name__)


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
        logger.info(f"Fetching API keys from secret: {config.api_keys_secret_name}")
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

        logger.info(f"Successfully fetched {len(valid_keys)} API key(s)")
        return valid_keys

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"]["Message"]

        if error_code == "ResourceNotFoundException":
            logger.error(
                f"Secret not found: {config.api_keys_secret_name}. "
                "Please create the secret in AWS Secrets Manager."
            )
        elif error_code == "AccessDeniedException":
            logger.error(
                f"Access denied to secret: {config.api_keys_secret_name}. "
                "Check IAM permissions."
            )
        else:
            logger.error(f"Secrets Manager error ({error_code}): {error_message}")

        raise

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse secret as JSON: {e}")
        raise ValueError(f"Invalid JSON in secret: {e}")

    except Exception as e:
        logger.error(f"Unexpected error fetching API keys: {e}")
        raise
