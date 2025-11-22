# Architecture Guidelines

## Application Architecture

### Technology Stack
- **Framework:** FastAPI (async web framework)
- **Server:** Uvicorn (ASGI server)
- **Runtime:** Python 3.11+
- **AWS SDK:** boto3
- **Validation:** Pydantic models
- **Rate Limiting:** slowapi

### Component Structure

```
FastAPI Application
├── Middleware Layer
│   ├── Rate Limiter (slowapi)
│   └── Authentication (custom)
├── Router Layer
│   ├── A2A Protocol Endpoints (/api/v1/*)
│   ├── Public Endpoints (/api/public/*)
│   └── Static File Server (/)
└── Service Layer
    ├── DynamoDB Service
    └── Secrets Manager Service
```

## Project Organization

```
app/
├── main.py              # FastAPI app entry, middleware setup
├── config.py            # Environment variable management
├── models.py            # Pydantic request/response models
├── middleware/
│   ├── auth.py          # Authentication middleware
│   └── rate_limit.py    # Rate limiting configuration
├── routers/
│   ├── a2a.py           # A2A protocol endpoints
│   └── public.py        # Public and health endpoints
├── services/
│   ├── dynamodb.py      # DynamoDB operations
│   └── secrets.py       # Secrets Manager operations
└── static/
    ├── index.html       # Web UI
    └── style.css        # Styling
```

## Design Principles

### Separation of Concerns
- **Routers:** Handle HTTP request/response, validation
- **Services:** Encapsulate AWS SDK operations, business logic
- **Middleware:** Cross-cutting concerns (auth, rate limiting)
- **Models:** Data validation and serialization

### Stateless Design
- No in-memory session storage
- API keys cached but refreshed from source
- Horizontal scaling friendly
- Each request is independent

### Error Handling
- Structured error responses with error codes
- Appropriate HTTP status codes
- Sanitize sensitive data from logs
- Include request tracing for debugging

## AWS Integration

### DynamoDB Access Pattern
- **Table:** Single table design
- **Primary Key:** `message_id` (partition), `timestamp` (sort)
- **GSI:** `timestamp-index` for chronological queries
  - Partition: `entity_type` (constant: "message")
  - Sort: `timestamp`
- **Operations:** PutItem, GetItem, Query
- **Pagination:** Use `LastEvaluatedKey` for large result sets

### Secrets Manager Pattern
- Fetch on application startup
- Cache in memory (Python set)
- Background refresh every 5 minutes
- Graceful handling of fetch failures

### IAM Permissions Required
```
secretsmanager:GetSecretValue (for API keys secret)
dynamodb:PutItem, GetItem, Query (for messages table and indexes)
```

## Configuration Management

### Environment Variables
All configuration via environment variables:
- `AWS_REGION`: AWS region (default: us-east-1)
- `DYNAMODB_TABLE_NAME`: DynamoDB table name
- `API_KEYS_SECRET_NAME`: Secrets Manager secret name
- `RATE_LIMIT_PER_MINUTE`: Rate limit (default: 10)
- `LOG_LEVEL`: Logging level (default: INFO)
- `PORT`: Application port (default: 8000)
- `KEY_REFRESH_INTERVAL_SECONDS`: Key refresh interval (default: 300)

### Configuration Validation
- Required variables must be present at startup
- Application fails fast if configuration is invalid
- Use `.env` file for local development (gitignored)

## Deployment Considerations

### Docker Container
- Multi-stage build for minimal image size
- Non-root user for security
- Health check endpoint configured
- Graceful shutdown handling

### Container Probes
- **Liveness:** `/health` endpoint
- **Readiness:** `/health` endpoint (checks AWS connectivity)
- **Startup:** `/health` endpoint (allows time for secrets fetch)

### Logging
- Structured JSON logging
- Include request IDs for tracing
- Sanitize API keys from logs
- Log levels: DEBUG, INFO, WARNING, ERROR

## Performance Considerations

### Optimization Strategies
- Use DynamoDB GSI for timestamp queries
- Consistent reads only when necessary
- Pagination for large result sets
- Static files served with cache headers

### Scalability
- Stateless application design
- Horizontal scaling via container replication
- Rate limiting per instance (acceptable for demo)
- DynamoDB auto-scaling with pay-per-request billing
