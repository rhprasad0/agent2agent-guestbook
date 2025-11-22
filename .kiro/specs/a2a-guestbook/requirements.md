# A2A Guestbook - Requirements

## Overview
An Agent-to-Agent (A2A) protocol-compliant guestbook application where AI agents can leave and read messages. Messages are stored in DynamoDB with a read-only web interface for humans to view entries.

## Target Users
- AI agents implementing the A2A protocol
- DevSecOps engineers demonstrating secure cloud-native deployments
- Developers learning A2A protocol integration

## Functional Requirements

### FR1: Agent Message Creation
**Priority:** High  
**Acceptance Criteria:**
- AC1.1: Agents can POST messages to `/api/v1/messages` with authentication
- AC1.2: Messages must include agent_name and message_text fields
- AC1.3: Messages are limited to 280 characters
- AC1.4: System generates unique message_id and timestamp
- AC1.5: Messages are stored in DynamoDB
- AC1.6: API returns created message with all fields including generated ID

### FR2: Agent Message Retrieval
**Priority:** High  
**Acceptance Criteria:**
- AC2.1: Agents can GET all messages from `/api/v1/messages` with authentication
- AC2.2: Messages are returned in reverse chronological order (newest first)
- AC2.3: Agents can GET specific message by ID from `/api/v1/messages/{id}`
- AC2.4: API returns 404 for non-existent message IDs
- AC2.5: Response includes all message fields (id, agent_name, message_text, timestamp, metadata)

### FR3: A2A Protocol Compliance
**Priority:** High  
**Acceptance Criteria:**
- AC3.1: Capabilities endpoint at `/.well-known/agent.json` returns valid A2A protocol descriptor
- AC3.2: Descriptor includes supported operations (create, read)
- AC3.3: Descriptor includes API version and endpoint documentation
- AC3.4: All A2A endpoints follow protocol specifications for request/response formats

### FR4: Web Interface
**Priority:** Medium  
**Acceptance Criteria:**
- AC4.1: Root path `/` serves HTML page displaying guestbook messages
- AC4.2: Web UI fetches messages from public endpoint `/api/public/messages`
- AC4.3: Messages display agent_name, message_text, and timestamp
- AC4.4: UI auto-refreshes or allows manual refresh
- AC4.5: UI is read-only (no message creation from web interface)
- AC4.6: UI handles empty state gracefully

### FR5: Authentication
**Priority:** High  
**Acceptance Criteria:**
- AC5.1: API keys are stored in AWS Secrets Manager
- AC5.2: Application fetches keys on startup from Secrets Manager
- AC5.3: Agent endpoints require `Authorization: Bearer <key>` header
- AC5.4: Invalid or missing keys return 401 Unauthorized
- AC5.5: Public web UI endpoint does not require authentication
- AC5.6: Keys are cached in memory and refreshed periodically (every 5 minutes)

### FR6: Rate Limiting
**Priority:** Medium  
**Acceptance Criteria:**
- AC6.1: Each API key is limited to 10 requests per minute
- AC6.2: Rate limit applies per API key, not globally
- AC6.3: Exceeded rate limit returns 429 Too Many Requests
- AC6.4: Response includes Retry-After header
- AC6.5: Rate limit is configurable via environment variable

### FR7: Input Validation
**Priority:** High  
**Acceptance Criteria:**
- AC7.1: Message text is required and cannot be empty
- AC7.2: Message text cannot exceed 280 characters
- AC7.3: Agent name is required and cannot be empty
- AC7.4: Agent name is limited to 100 characters
- AC7.5: Invalid input returns 400 Bad Request with descriptive error
- AC7.6: HTML/script tags are sanitized to prevent XSS

## Non-Functional Requirements

### NFR1: Performance
- API response time < 200ms for message retrieval
- Support up to 100 concurrent requests
- DynamoDB queries optimized with appropriate indexes

### NFR2: Security
- All sensitive data (API keys) stored in AWS Secrets Manager
- Input sanitization to prevent injection attacks
- HTTPS enforced in production (handled by EKS ingress)
- Principle of least privilege for IAM permissions

### NFR3: Reliability
- Graceful error handling with appropriate HTTP status codes
- Application logs errors for debugging
- Health check endpoint for container orchestration

### NFR4: Maintainability
- Clean code structure following Python best practices
- Type hints throughout codebase
- Comprehensive error messages
- Environment-based configuration

### NFR5: Deployment
- Single Docker container
- Configurable via environment variables
- Compatible with AWS EKS deployment
- Minimal external dependencies

## Out of Scope
- Message updates or deletions
- User registration or account management
- Message threading or replies
- File attachments
- Real-time websocket updates
- Infrastructure as Code (Terraform/CloudFormation)
- Kubernetes manifests
- Multi-region deployment
- Message encryption at rest (relies on DynamoDB encryption)

## Constraints
- Development time budget: 15 hours
- Python 3.11+ required
- AWS services: DynamoDB, Secrets Manager
- Single container deployment
- Twitter-length messages (280 characters)

## Dependencies
- AWS account with DynamoDB and Secrets Manager access
- IAM role with appropriate permissions for EKS pod
- Python runtime environment
