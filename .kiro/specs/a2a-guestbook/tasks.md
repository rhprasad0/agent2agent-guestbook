# A2A Guestbook - Implementation Tasks

## 1. Project Setup and Core Models

- [ ] 1.1 Initialize project structure and dependencies
  - Create app/ directory structure (routers/, services/, middleware/, static/)
  - Create requirements.txt with FastAPI, boto3, pydantic, slowapi, uvicorn
  - Create .env.example with all required environment variables
  - Create .gitignore for Python project
  - _Requirements: All functional requirements_

- [ ] 1.2 Implement configuration management
  - Create app/config.py with environment variable loading
  - Validate required configuration (AWS_REGION, DYNAMODB_TABLE_NAME, API_KEYS_SECRET_NAME)
  - Provide defaults for optional settings (RATE_LIMIT_PER_MINUTE=10, LOG_LEVEL=INFO, PORT=8000)
  - _Requirements: NFR4 (Maintainability), NFR5 (Deployment)_

- [ ] 1.3 Create Pydantic models for validation
  - Define MessageCreate model (agent_name: 1-100 chars, message_text: 1-280 chars, metadata: optional)
  - Define Message model (includes message_id, timestamp)
  - Define MessageList model for list responses
  - Define error response models
  - _Requirements: FR1 (AC1.2, AC1.3), FR7 (all ACs)_

## 2. AWS Service Integration

- [ ] 2.1 Implement Secrets Manager service
  - Create app/services/secrets.py
  - Implement async function to fetch API keys from Secrets Manager
  - Parse JSON secret format {"api_keys": [...]}
  - Handle ClientError exceptions gracefully
  - _Requirements: FR5 (AC5.1, AC5.2), NFR2 (Security)_

- [ ] 2.2 Implement DynamoDB service
  - Create app/services/dynamodb.py
  - Implement create_message() with PutItem (generates UUID and ISO timestamp)
  - Implement get_message_by_id() with GetItem
  - Implement list_messages() with Query on timestamp-index GSI
  - Support pagination with LastEvaluatedKey
  - Handle AWS errors and return appropriate exceptions
  - _Requirements: FR1 (AC1.4, AC1.5, AC1.6), FR2 (all ACs), NFR1 (Performance)_

## 3. Authentication and Rate Limiting

- [ ] 3.1 Implement authentication middleware
  - Create app/middleware/auth.py
  - Extract Bearer token from Authorization header
  - Validate against cached API keys (in-memory set)
  - Implement startup task to load initial keys from Secrets Manager
  - Implement background task to refresh keys every 5 minutes
  - Return 401 for invalid/missing tokens
  - _Requirements: FR5 (AC5.3, AC5.4, AC5.6), NFR2 (Security)_

- [ ] 3.2 Configure rate limiting
  - Create app/middleware/rate_limit.py
  - Configure slowapi with per-API-key limits (10 req/min)
  - Return 429 with Retry-After header when exceeded
  - Apply only to authenticated endpoints
  - _Requirements: FR6 (all ACs)_

## 4. API Endpoints - A2A Protocol

- [ ] 4.1 Implement A2A capabilities endpoint
  - Create app/routers/a2a.py
  - Implement GET /.well-known/agent.json (no auth required)
  - Return protocol version, capabilities, and endpoint documentation
  - _Requirements: FR3 (all ACs)_

- [ ] 4.2 Implement create message endpoint
  - Add POST /api/v1/messages to app/routers/a2a.py
  - Require authentication
  - Validate input with Pydantic MessageCreate model
  - Call DynamoDB service to store message
  - Return 201 with created message
  - Handle errors: 400 (validation), 401 (auth), 429 (rate limit), 500 (server)
  - _Requirements: FR1 (all ACs), FR7 (all ACs)_

- [ ] 4.3 Implement list messages endpoint
  - Add GET /api/v1/messages to app/routers/a2a.py
  - Require authentication
  - Support limit query parameter (default: 50, max: 100)
  - Support start_key for pagination
  - Return messages in reverse chronological order
  - _Requirements: FR2 (AC2.1, AC2.2, AC2.5)_

- [ ] 4.4 Implement get message by ID endpoint
  - Add GET /api/v1/messages/{id} to app/routers/a2a.py
  - Require authentication
  - Return 404 for non-existent IDs
  - _Requirements: FR2 (AC2.3, AC2.4, AC2.5)_

## 5. Public Endpoints and Web Interface

- [ ] 5.1 Implement public endpoints
  - Create app/routers/public.py
  - Implement GET /api/public/messages (no auth, up to 50 messages, exclude metadata)
  - Implement GET /health (returns status and timestamp)
  - _Requirements: FR4 (AC4.2), NFR3 (Reliability)_

- [ ] 5.2 Create web UI
  - Create app/static/index.html with clean, simple design
  - Display messages in cards/list format (agent_name, message_text, timestamp)
  - Implement auto-refresh every 30 seconds
  - Add manual refresh button
  - Handle empty state gracefully
  - Create app/static/style.css for responsive design
  - _Requirements: FR4 (all ACs)_

## 6. Application Assembly

- [ ] 6.1 Assemble FastAPI application
  - Create app/main.py as entry point
  - Initialize FastAPI app with metadata
  - Register all routers (a2a, public)
  - Configure middleware (auth, rate limiting, CORS)
  - Setup structured logging
  - Configure static file serving for web UI
  - Add startup event handler (load API keys)
  - Add shutdown event handler (cleanup)
  - Add global exception handlers
  - _Requirements: All functional requirements, NFR3 (Reliability), NFR4 (Maintainability)_

- [ ] 6.2 Create Dockerfile
  - Multi-stage build for minimal image size
  - Use Python 3.11+ base image
  - Run as non-root user
  - Configure health check endpoint
  - Optimize layer caching
  - _Requirements: NFR5 (Deployment), NFR2 (Security)_

## 7. Documentation and Testing

- [ ] 7.1 Create comprehensive documentation
  - Write README.md with setup instructions, architecture overview
  - Document all environment variables
  - Provide AWS setup instructions (DynamoDB table schema, Secrets Manager format)
  - Include Docker build and run instructions
  - Add example API calls with curl
  - _Requirements: NFR4 (Maintainability)_

- [ ]* 7.2 Manual testing and validation
  - Test all endpoints with curl/Postman
  - Verify authentication and rate limiting
  - Test error cases (invalid input, missing auth, rate limit exceeded)
  - Verify DynamoDB and Secrets Manager integration
  - Test web UI functionality
  - _Requirements: All functional requirements_
