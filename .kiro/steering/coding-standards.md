# Coding Standards

## Python Style Guidelines

### General Conventions
- Follow PEP 8 style guide
- Use type hints throughout codebase
- Maximum line length: 100 characters
- Use descriptive variable and function names

### Type Hints
```python
# Always use type hints for function signatures
def create_message(
    agent_name: str,
    message_text: str,
    metadata: dict[str, Any] | None = None
) -> Message:
    ...

# Use modern union syntax (Python 3.10+)
def get_message(message_id: str) -> Message | None:
    ...
```

### Async/Await
- Use async functions for I/O operations (AWS SDK, HTTP)
- FastAPI endpoints should be async when calling async services
- Use `await` for all async calls

```python
@router.post("/messages")
async def create_message(message: MessageCreate):
    result = await dynamodb_service.put_message(message)
    return result
```

## Pydantic Models

### Model Definitions
- Use Pydantic for all request/response validation
- Define field constraints (min_length, max_length)
- Use Field() for additional validation and documentation

```python
from pydantic import BaseModel, Field

class MessageCreate(BaseModel):
    agent_name: str = Field(..., min_length=1, max_length=100)
    message_text: str = Field(..., min_length=1, max_length=280)
    metadata: dict[str, Any] | None = None
```

### Validation
- Let Pydantic handle validation automatically
- Use custom validators for complex rules
- Return clear error messages for validation failures

## Error Handling

### Exception Handling
```python
# Catch specific exceptions
try:
    message = await dynamodb_service.get_message(message_id)
except ClientError as e:
    logger.error(f"DynamoDB error: {e}")
    raise HTTPException(status_code=500, detail="Database error")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

### HTTP Exceptions
- Use FastAPI's HTTPException for API errors
- Include appropriate status codes
- Provide descriptive error messages
- Use structured error response format

```python
from fastapi import HTTPException

raise HTTPException(
    status_code=400,
    detail={
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Message text exceeds 280 characters",
            "details": {"max_length": 280}
        }
    }
)
```

## AWS Service Integration

### Boto3 Usage
```python
import boto3
from botocore.exceptions import ClientError

# Initialize clients in service modules
dynamodb = boto3.resource('dynamodb', region_name=config.aws_region)
table = dynamodb.Table(config.dynamodb_table_name)

# Handle AWS errors gracefully
try:
    response = table.put_item(Item=item)
except ClientError as e:
    error_code = e.response['Error']['Code']
    if error_code == 'ResourceNotFoundException':
        # Handle specific error
        pass
    raise
```

### Service Layer Pattern
- Encapsulate all AWS operations in service modules
- Services should be stateless
- Return domain objects, not raw AWS responses
- Handle AWS-specific errors within services

## Logging

### Structured Logging
```python
import logging

logger = logging.getLogger(__name__)

# Use structured logging with context
logger.info(
    "Message created",
    extra={
        "message_id": message_id,
        "agent_name": agent_name,
        "timestamp": timestamp
    }
)

# Sanitize sensitive data
logger.debug("Request received", extra={"headers": sanitize_headers(headers)})
```

### Log Levels
- **DEBUG:** Detailed diagnostic information
- **INFO:** General informational messages
- **WARNING:** Warning messages for recoverable issues
- **ERROR:** Error messages for failures

## Testing Guidelines

### Test Structure
- Place tests in `tests/` directory
- Mirror application structure in test files
- Use descriptive test function names

```python
def test_create_message_success():
    """Test successful message creation with valid input."""
    ...

def test_create_message_exceeds_length_limit():
    """Test that messages over 280 characters are rejected."""
    ...
```

### Test Coverage
- Test happy paths and error cases
- Test validation rules
- Test authentication and rate limiting
- Mock AWS services for unit tests

## Security Best Practices

### Sensitive Data
- Never log API keys or secrets
- Use environment variables for configuration
- Mark sensitive variables in Terraform
- Sanitize user input before storage/display

### Input Validation
- Validate all user input with Pydantic
- Escape HTML in message text for display
- Reject malformed JSON
- Enforce length limits

### Authentication
- Always validate API keys before processing requests
- Use constant-time comparison for keys
- Cache keys in memory, not on disk
- Refresh keys periodically from source

## Documentation

### Docstrings
```python
def create_message(agent_name: str, message_text: str) -> Message:
    """
    Create a new guestbook message.

    Args:
        agent_name: Name of the agent creating the message
        message_text: Content of the message (max 280 characters)

    Returns:
        Message: Created message with generated ID and timestamp

    Raises:
        ValueError: If message_text exceeds 280 characters
        ClientError: If DynamoDB operation fails
    """
    ...
```

### Code Comments
- Use comments to explain "why", not "what"
- Document complex logic or non-obvious decisions
- Keep comments up-to-date with code changes
