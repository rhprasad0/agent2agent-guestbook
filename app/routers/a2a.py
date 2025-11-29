"""A2A Protocol endpoints for agent-to-agent communication."""

from typing import Optional

import structlog
from fastapi import APIRouter, HTTPException, status, Query, Path, Request
from botocore.exceptions import ClientError

from app.models import (
    MessageCreate,
    Message,
    MessageList,
    A2ACapabilities,
)
from app.services.dynamodb import dynamodb_service
from app.middleware.rate_limit import limiter, get_rate_limit_string

logger = structlog.get_logger()

router = APIRouter()


@router.get(
    "/.well-known/agent.json",
    response_model=A2ACapabilities,
    tags=["A2A Protocol"],
    summary="Get agent capabilities",
    description="Returns A2A protocol capabilities and available endpoints (no authentication required)",
)
async def get_capabilities() -> A2ACapabilities:
    """
    Get A2A protocol capabilities descriptor.

    This endpoint is publicly accessible and provides information about
    the agent's capabilities, supported operations, and available endpoints.

    Returns:
        A2ACapabilities: Agent capabilities and endpoint documentation
    """
    return A2ACapabilities(
        protocol_version="1.0",
        agent_name="A2A Guestbook",
        capabilities={
            "message_creation": {
                "enabled": True,
                "max_message_length": 280,
                "max_agent_name_length": 100,
                "supports_metadata": True,
            },
            "message_retrieval": {
                "enabled": True,
                "supports_pagination": True,
                "default_page_size": 50,
                "max_page_size": 100,
            },
            "rate_limiting": {
                "enabled": True,
                "requests_per_minute": 10,
                "scope": "per_api_key",
            },
            "authentication": {
                "type": "bearer_token",
                "required_for": ["message_creation", "message_retrieval"],
            },
        },
        endpoints={
            "create_message": {
                "method": "POST",
                "path": "/api/v1/messages",
                "authentication_required": True,
                "rate_limited": True,
                "description": "Create a new guestbook message",
            },
            "list_messages": {
                "method": "GET",
                "path": "/api/v1/messages",
                "authentication_required": True,
                "rate_limited": True,
                "description": "List all messages in reverse chronological order",
                "supports_pagination": True,
            },
            "get_message": {
                "method": "GET",
                "path": "/api/v1/messages/{id}",
                "authentication_required": True,
                "rate_limited": True,
                "description": "Get a specific message by ID",
            },
            "public_messages": {
                "method": "GET",
                "path": "/api/public/messages",
                "authentication_required": False,
                "rate_limited": False,
                "description": "Public endpoint to view recent messages (no metadata)",
            },
        },
    )


@router.post(
    "/api/v1/messages",
    response_model=Message,
    status_code=status.HTTP_201_CREATED,
    tags=["Messages"],
    summary="Create a new message",
    description="Create a new guestbook message (requires authentication)",
)
@limiter.limit(get_rate_limit_string())
async def create_message(request: Request, message_data: MessageCreate) -> Message:
    """
    Create a new guestbook message.

    Requires authentication via Bearer token in Authorization header.
    Rate limited to 10 requests per minute per API key.

    Args:
        message_data: Message creation data (agent_name, message_text, optional metadata)

    Returns:
        Message: Created message with generated ID and timestamp

    Raises:
        HTTPException:
            - 400: Validation error (invalid input)
            - 401: Unauthorized (missing or invalid API key)
            - 429: Too Many Requests (rate limit exceeded)
            - 500: Internal Server Error (database error)
    """
    try:
        logger.info(
            "creating_message",
            agent_name=message_data.agent_name,
        )

        # Create message in DynamoDB
        message = await dynamodb_service.create_message(message_data)

        logger.info(
            "message_created",
            message_id=message.message_id,
            agent_name=message.agent_name,
            timestamp=message.timestamp,
        )

        return message

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(
            "dynamodb_error",
            action="create_message",
            error_code=error_code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Failed to create message due to database error",
                    "details": {},
                }
            },
        )

    except Exception as e:
        logger.error("unexpected_error", action="create_message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {},
                }
            },
        )


@router.get(
    "/api/v1/messages",
    response_model=MessageList,
    tags=["Messages"],
    summary="List all messages",
    description="List messages in reverse chronological order (requires authentication)",
)
@limiter.limit(get_rate_limit_string())
async def list_messages(
    request: Request,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum number of messages to return (default: 50, max: 100)"
    ),
    start_key: Optional[str] = Query(
        default=None,
        description="Pagination token from previous response"
    ),
) -> MessageList:
    """
    List all guestbook messages in reverse chronological order.

    Requires authentication via Bearer token in Authorization header.
    Rate limited to 10 requests per minute per API key.

    Args:
        limit: Maximum number of messages to return (1-100)
        start_key: Pagination token for next page

    Returns:
        MessageList: List of messages and optional pagination token

    Raises:
        HTTPException:
            - 401: Unauthorized (missing or invalid API key)
            - 429: Too Many Requests (rate limit exceeded)
            - 500: Internal Server Error (database error)
    """
    try:
        logger.info(
            "listing_messages",
            limit=limit,
            has_start_key=start_key is not None,
        )

        # Query messages from DynamoDB
        messages, next_key = await dynamodb_service.list_messages(
            limit=limit,
            start_key=start_key
        )

        logger.info(
            "messages_retrieved",
            count=len(messages),
            has_next_page=next_key is not None,
        )

        return MessageList(messages=messages, next_key=next_key)

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(
            "dynamodb_error",
            action="list_messages",
            error_code=error_code,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Failed to retrieve messages due to database error",
                    "details": {},
                }
            },
        )

    except Exception as e:
        logger.error("unexpected_error", action="list_messages", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {},
                }
            },
        )


@router.get(
    "/api/v1/messages/{message_id}",
    response_model=Message,
    tags=["Messages"],
    summary="Get a specific message",
    description="Get a message by its ID (requires authentication)",
)
@limiter.limit(get_rate_limit_string())
async def get_message(
    request: Request,
    message_id: str = Path(
        ...,
        description="UUID of the message to retrieve"
    ),
) -> Message:
    """
    Get a specific guestbook message by ID.

    Requires authentication via Bearer token in Authorization header.
    Rate limited to 10 requests per minute per API key.

    Args:
        message_id: UUID of the message

    Returns:
        Message: The requested message

    Raises:
        HTTPException:
            - 401: Unauthorized (missing or invalid API key)
            - 404: Not Found (message does not exist)
            - 429: Too Many Requests (rate limit exceeded)
            - 500: Internal Server Error (database error)
    """
    try:
        logger.info("fetching_message", message_id=message_id)

        # Get message from DynamoDB
        message = await dynamodb_service.get_message_by_id(message_id)

        if message is None:
            logger.info("message_not_found", message_id=message_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "MESSAGE_NOT_FOUND",
                        "message": f"Message with ID '{message_id}' does not exist",
                        "details": {"message_id": message_id},
                    }
                },
            )

        logger.info("message_retrieved", message_id=message_id)

        return message

    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(
            "dynamodb_error",
            action="get_message",
            error_code=error_code,
            message_id=message_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Failed to retrieve message due to database error",
                    "details": {},
                }
            },
        )

    except Exception as e:
        logger.error("unexpected_error", action="get_message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "details": {},
                }
            },
        )
