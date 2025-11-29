"""AWS DynamoDB service for message storage."""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import boto3
import structlog
from botocore.exceptions import ClientError

from app.config import config
from app.models import Message, MessageCreate

logger = structlog.get_logger()


class DynamoDBService:
    """Service for DynamoDB operations."""

    def __init__(self):
        """Initialize DynamoDB client and table."""
        self.dynamodb = boto3.resource("dynamodb", region_name=config.aws_region)
        self.table = self.dynamodb.Table(config.dynamodb_table_name)
        self.entity_type = "message"  # Constant for GSI partition key

    async def create_message(self, message_data: MessageCreate) -> Message:
        """
        Create a new message in DynamoDB.

        Args:
            message_data: Message creation data

        Returns:
            Message: Created message with generated ID and timestamp

        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Generate UUID and timestamp
            message_id = str(uuid.uuid4())
            timestamp = datetime.now(timezone.utc).isoformat()

            # Prepare item for DynamoDB
            item = {
                "message_id": message_id,
                "timestamp": timestamp,
                "entity_type": self.entity_type,  # For GSI
                "agent_name": message_data.agent_name,
                "message_text": message_data.message_text,
            }

            # Add metadata if provided
            if message_data.metadata:
                item["metadata"] = message_data.metadata

            # Store in DynamoDB
            logger.info("dynamodb_put_item", message_id=message_id)
            self.table.put_item(Item=item)

            # Return created message
            return Message(
                message_id=message_id,
                agent_name=message_data.agent_name,
                message_text=message_data.message_text,
                timestamp=timestamp,
                metadata=message_data.metadata,
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error(
                "dynamodb_error",
                operation="put_item",
                error_code=error_code,
                error_message=error_message,
            )
            raise

        except Exception as e:
            logger.error("unexpected_error", operation="create_message", error=str(e))
            raise

    async def get_message_by_id(self, message_id: str) -> Optional[Message]:
        """
        Get a specific message by ID.

        Since the table has a composite key (message_id + timestamp),
        we use Query to find the message by partition key only.

        Args:
            message_id: UUID of the message

        Returns:
            Message if found, None otherwise

        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            logger.info("dynamodb_query", message_id=message_id)

            # Query by partition key (message_id)
            response = self.table.query(
                KeyConditionExpression="message_id = :message_id",
                ExpressionAttributeValues={":message_id": message_id},
                Limit=1
            )

            items = response.get("Items", [])
            if not items:
                logger.info("dynamodb_item_not_found", message_id=message_id)
                return None

            item = items[0]

            # Convert DynamoDB item to Message model
            return Message(
                message_id=item["message_id"],
                agent_name=item["agent_name"],
                message_text=item["message_text"],
                timestamp=item["timestamp"],
                metadata=item.get("metadata"),
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error(
                "dynamodb_error",
                operation="query",
                error_code=error_code,
                error_message=error_message,
            )
            raise

        except Exception as e:
            logger.error("unexpected_error", operation="get_message", error=str(e))
            raise

    async def list_messages(
        self,
        limit: int = 50,
        start_key: Optional[str] = None
    ) -> tuple[List[Message], Optional[str]]:
        """
        List messages in reverse chronological order using GSI.

        Args:
            limit: Maximum number of messages to return (default: 50, max: 100)
            start_key: Pagination token from previous request

        Returns:
            Tuple of (list of messages, next pagination token)

        Raises:
            ClientError: If DynamoDB operation fails
        """
        try:
            # Ensure limit is within bounds
            limit = min(max(1, limit), 100)

            # Build query parameters
            query_params: Dict[str, Any] = {
                "IndexName": "timestamp-index",
                "KeyConditionExpression": "entity_type = :entity_type",
                "ExpressionAttributeValues": {":entity_type": self.entity_type},
                "ScanIndexForward": False,  # Reverse chronological order
                "Limit": limit,
            }

            # Add pagination token if provided
            if start_key:
                try:
                    # Parse the pagination token (base64 encoded JSON in production)
                    # For simplicity, we'll use the timestamp directly
                    query_params["ExclusiveStartKey"] = {
                        "entity_type": self.entity_type,
                        "timestamp": start_key,
                    }
                except Exception as e:
                    logger.warning("invalid_pagination_token", error=str(e))

            logger.info("dynamodb_query_index", limit=limit)
            response = self.table.query(**query_params)

            # Convert items to Message models
            messages = [
                Message(
                    message_id=item["message_id"],
                    agent_name=item["agent_name"],
                    message_text=item["message_text"],
                    timestamp=item["timestamp"],
                    metadata=item.get("metadata"),
                )
                for item in response.get("Items", [])
            ]

            # Get next pagination token
            next_key = None
            last_evaluated_key = response.get("LastEvaluatedKey")
            if last_evaluated_key:
                next_key = last_evaluated_key.get("timestamp")

            logger.info("dynamodb_query_complete", count=len(messages))
            return messages, next_key

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            logger.error(
                "dynamodb_error",
                operation="query_index",
                error_code=error_code,
                error_message=error_message,
            )
            raise

        except Exception as e:
            logger.error("unexpected_error", operation="list_messages", error=str(e))
            raise


# Global service instance
dynamodb_service = DynamoDBService()
