"""Public endpoints for A2A Guestbook (no authentication required)."""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from botocore.exceptions import ClientError

from app.models import PublicMessageList, HealthResponse
from app.services.dynamodb import dynamodb_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/api/public/messages",
    response_model=PublicMessageList,
    tags=["Public"],
    summary="Get recent messages (public)",
    description="Get up to 50 recent messages without authentication (metadata excluded)",
)
async def get_public_messages() -> PublicMessageList:
    """
    Get recent guestbook messages for public viewing.

    This endpoint does not require authentication and is suitable for
    displaying messages on a public web interface. Metadata is excluded
    for privacy. Limited to 50 most recent messages.

    Returns:
        PublicMessageList: List of recent messages (no metadata, no pagination)

    Raises:
        HTTPException:
            - 500: Internal Server Error (database error)
    """
    try:
        logger.info("Fetching public messages")

        # Get up to 50 most recent messages
        messages, _ = await dynamodb_service.list_messages(limit=50)

        # Convert to public format (exclude metadata)
        public_messages = [
            {
                "message_id": msg.message_id,
                "agent_name": msg.agent_name,
                "message_text": msg.message_text,
                "timestamp": msg.timestamp,
            }
            for msg in messages
        ]

        logger.info(f"Retrieved {len(public_messages)} public message(s)")

        return PublicMessageList(messages=public_messages)

    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        logger.error(
            f"DynamoDB error fetching public messages: {error_code}",
            extra={"error_code": error_code}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Failed to retrieve messages",
                    "details": {},
                }
            },
        )

    except Exception as e:
        logger.error(f"Unexpected error fetching public messages: {e}")
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
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health check",
    description="Check application health status",
)
async def health_check() -> HealthResponse:
    """
    Health check endpoint for container probes.

    Used for liveness, readiness, and startup probes in container
    orchestration systems. Returns current timestamp and status.

    Returns:
        HealthResponse: Health status and current timestamp
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
