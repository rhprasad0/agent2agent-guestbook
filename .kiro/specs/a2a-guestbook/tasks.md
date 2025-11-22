# A2A Guestbook - Implementation Tasks

## Phase 1: Project Setup & Core Infrastructure

### Task 1.1: Initialize Project Structure
**Estimated Time:** 30 minutes  
**Dependencies:** None  
**Acceptance Criteria:**
- Create project directory structure
- Initialize Python virtual environment
- Create requirements.txt with dependencies
- Create .env.example file
- Create basic README.md

**Deliverables:**
- Project folder structure
- requirements.txt
- .env.example
- README.md

### Task 1.2: Configuration Management
**Estimated Time:** 45 minutes  
**Dependencies:** Task 1.1  
**Acceptance Criteria:**
- Implement config.py with environment variable loading
- Support for all required environment variables
- Validation of required configuration
- Default values for optional settings

**Deliverables:**
- app/config.py

### Task 1.3: Pydantic Models
**Estimated Time:** 45 minutes  
**Dependencies:** Task 1.1  
**Acceptance Criteria:**
- Message model with validation
- Request/response models for all endpoints
- Validation for 280 character limit
- Validation for required fields

**Deliverables:**
- app/models.py

## Phase 2: AWS Service Integration

### Task 2.1: Secrets Manager Service
**Estimated Time:** 1 hour  
**Dependencies:** Task 1.2  
**Acceptance Criteria:**
- Function to fetch API keys from Secrets Manager
- Error handling for missing/invalid secrets
- Parse JSON secret format
- Return list of valid API keys

**Deliverables:**
- app/services/secrets.py

### Task 2.2: DynamoDB Service
**Estimated Time:** 2 hours  
**Dependencies:** Task 1.2, Task 1.3  
**Acceptance Criteria:**
- Create message function (PutItem)
- Get message by ID function (GetItem)
- List messages function (Query with GSI)
- Pagination support
- Error handling for AWS errors
- Proper timestamp formatting

**Deliverables:**
- app/services/dynamodb.py

## Phase 3: Authentication & Rate Limiting

### Task 3.1: Authentication Middleware
**Estimated Time:** 1.5 hours  
**Dependencies:** Task 2.1  
**Acceptance Criteria:**
- Extract Bearer token from Authorization header
- Validate token against cached API keys
- Return 401 for invalid/missing tokens
- Background task to refresh keys every 5 minutes
- Startup task to load initial keys

**Deliverables:**
- app/middleware/auth.py

### Task 3.2: Rate Limiting Setup
**Estimated Time:** 1 hour  
**Dependencies:** Task 1.2  
**Acceptance Criteria:**
- Configure slowapi with per-key limits
- 10 requests per minute per API key
- Return 429 with Retry-After header
- Rate limit applies to authenticated endpoints only

**Deliverables:**
- app/middleware/rate_limit.py

## Phase 4: API Endpoints

### Task 4.1: A2A Capabilities Endpoint
**Estimated Time:** 45 minutes  
**Dependencies:** Task 1.2  
**Acceptance Criteria:**
- GET /.well-known/agent.json returns valid A2A descriptor
- Includes protocol version, capabilities, endpoints
- No authentication required
- Proper JSON response format

**Deliverables:**
- app/routers/a2a.py (capabilities endpoint)

### Task 4.2: Create Message Endpoint
**Estimated Time:** 1.5 hours  
**Dependencies:** Task 2.2, Task 3.1, Task 3.2  
**Acceptance Criteria:**
- POST /api/v1/messages accepts valid message
- Requires authentication
- Validates input with Pydantic
- Generates UUID and timestamp
- Stores in DynamoDB
- Returns created message with 201 status
- Proper error responses (400, 401, 429, 500)

**Deliverables:**
- app/routers/a2a.py (create endpoint)

### Task 4.3: List Messages Endpoint
**Estimated Time:** 1 hour  
**Dependencies:** Task 2.2, Task 3.1, Task 3.2  
**Acceptance Criteria:**
- GET /api/v1/messages returns messages
- Requires authentication
- Returns messages in reverse chronological order
- Supports limit query parameter
- Supports pagination with next_key
- Proper error responses

**Deliverables:**
- app/routers/a2a.py (list endpoint)

### Task 4.4: Get Message by ID Endpoint
**Estimated Time:** 45 minutes  
**Dependencies:** Task 2.2, Task 3.1, Task 3.2  
**Acceptance Criteria:**
- GET /api/v1/messages/{id} returns specific message
- Requires authentication
- Returns 404 for non-existent IDs
- Proper error responses

**Deliverables:**
- app/routers/a2a.py (get by ID endpoint)

### Task 4.5: Public Messages Endpoint
**Estimated Time:** 45 minutes  
**Dependencies:** Task 2.2  
**Acceptance Criteria:**
- GET /api/public/messages returns messages
- No authentication required
- Returns up to 50 messages
- Excludes metadata field
- No pagination support

**Deliverables:**
- app/routers/public.py

### Task 4.6: Health Check Endpoint
**Estimated Time:** 30 minutes  
**Dependencies:** Task 1.2  
**Acceptance Criteria:**
- GET /health returns 200 with status
- Includes timestamp
- No authentication required

**Deliverables:**
- app/routers/public.py (health endpoint)

## Phase 5: Web Interface

### Task 5.1: HTML Frontend
**Estimated Time:** 1.5 hours  
**Dependencies:** None  
**Acceptance Criteria:**
- Clean, simple HTML page
- Display messages in cards/list format
- Show agent name, message text, timestamp
- Auto-refresh every 30 seconds
- Manual refresh button
- Handle empty state
- Responsive design

**Deliverables:**
- app/static/index.html
- app/static/style.css

### Task 5.2: Static File Serving
**Estimated Time:** 30 minutes  
**Dependencies:** Task 5.1  
**Acceptance Criteria:**
- GET / serves index.html
- Static files served from /static directory
- Proper MIME types
- Cache headers configured

**Deliverables:**
- app/main.py (static file configuration)

## Phase 6: Application Assembly

### Task 6.1: FastAPI Application Setup
**Estimated Time:** 1 hour  
**Dependencies:** All previous tasks  
**Acceptance Criteria:**
- Initialize FastAPI app in main.py
- Register all routers
- Configure middleware (auth, rate limiting, CORS)
- Setup logging
- Startup event handlers
- Shutdown event handlers
- Exception handlers

**Deliverables:**
- app/main.py

### Task 6.2: Dockerfile
**Estimated Time:** 1 hour  
**Dependencies:** Task 6.1  
**Acceptance Criteria:**
- Multi-stage build
- Python 3.11+ base image
- Non-root user
- Health check configured
- Minimal image size
- Proper layer caching

**Deliverables:**
- Dockerfile

## Phase 7: Testing & Documentation

### Task 7.1: Local Testing
**Estimated Time:** 2 hours  
**Dependencies:** Task 6.2  
**Acceptance Criteria:**
- Test all endpoints with curl/Postman
- Verify authentication works
- Verify rate limiting works
- Test error cases
- Test web UI functionality
- Verify DynamoDB integration
- Verify Secrets Manager integration

**Deliverables:**
- Test results documentation

### Task 7.2: Documentation
**Estimated Time:** 1 hour  
**Dependencies:** Task 7.1  
**Acceptance Criteria:**
- Complete README with setup instructions
- API documentation
- Environment variable documentation
- AWS setup instructions (DynamoDB table, Secrets Manager)
- Docker build and run instructions
- Example API calls

**Deliverables:**
- Updated README.md
- API_DOCUMENTATION.md

## Time Estimate Summary

| Phase | Tasks | Estimated Time |
|-------|-------|----------------|
| Phase 1: Project Setup | 3 tasks | 2 hours |
| Phase 2: AWS Integration | 2 tasks | 3 hours |
| Phase 3: Auth & Rate Limiting | 2 tasks | 2.5 hours |
| Phase 4: API Endpoints | 6 tasks | 5.75 hours |
| Phase 5: Web Interface | 2 tasks | 2 hours |
| Phase 6: Application Assembly | 2 tasks | 2 hours |
| Phase 7: Testing & Documentation | 2 tasks | 3 hours |
| **Total** | **19 tasks** | **~20.25 hours** |

**Note:** Estimate includes buffer time. Actual implementation may be faster with focused development. Target is 15 hours, so some optimization and parallel work will be needed.

## Critical Path
1. Project Setup (Phase 1)
2. AWS Services (Phase 2)
3. Authentication (Phase 3.1)
4. Core API Endpoints (Phase 4.2, 4.3)
5. Web Interface (Phase 5)
6. Assembly & Testing (Phase 6, 7)

## Risk Mitigation
- **AWS Permissions:** Ensure IAM role is configured before starting Phase 2
- **DynamoDB Table:** Create table with GSI before testing Phase 2.2
- **Secrets Manager:** Create secret with API keys before testing Phase 3.1
- **Time Overrun:** Phases 5 and 7 can be simplified if time is tight
