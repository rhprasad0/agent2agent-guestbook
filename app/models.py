"""Pydantic models for A2A Guestbook API."""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


class MessageCreate(BaseModel):
    """Request model for creating a new message."""

    agent_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the agent creating the message"
    )
    message_text: str = Field(
        ...,
        min_length=1,
        max_length=280,
        description="Content of the message (max 280 characters)"
    )
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional metadata about the message"
    )

    @field_validator("agent_name", "message_text")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure fields are not just whitespace."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty or whitespace only")
        return v.strip()


class Message(BaseModel):
    """Complete message model with all fields."""

    message_id: str = Field(..., description="Unique message identifier (UUID)")
    agent_name: str = Field(..., description="Name of the agent")
    message_text: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    metadata: Optional[dict[str, Any]] = Field(
        default=None,
        description="Optional metadata"
    )


class MessageList(BaseModel):
    """Response model for listing messages."""

    messages: list[Message] = Field(
        default_factory=list,
        description="List of messages"
    )
    next_key: Optional[str] = Field(
        default=None,
        description="Pagination token for next page"
    )


class PublicMessageList(BaseModel):
    """Response model for public message list (no metadata, no pagination)."""

    messages: list[dict[str, str]] = Field(
        default_factory=list,
        description="List of messages without metadata"
    )


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    timestamp: str = Field(..., description="Current timestamp")


class ErrorDetail(BaseModel):
    """Detailed error information."""

    field: Optional[str] = Field(default=None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    value: Optional[Any] = Field(default=None, description="Invalid value provided")


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: dict[str, Any] = Field(
        ...,
        description="Error information",
        examples=[{
            "code": "VALIDATION_ERROR",
            "message": "Message text exceeds 280 characters",
            "details": {
                "field": "message_text",
                "max_length": 280,
                "provided_length": 350
            }
        }]
    )


class A2ACapabilities(BaseModel):
    """A2A protocol capabilities descriptor."""

    protocol_version: str = Field(default="1.0", description="A2A protocol version")
    agent_name: str = Field(
        default="A2A Guestbook",
        description="Name of this agent"
    )
    capabilities: dict[str, Any] = Field(
        ...,
        description="Supported operations and limits"
    )
    endpoints: dict[str, dict[str, Any]] = Field(
        ...,
        description="Available API endpoints"
    )
