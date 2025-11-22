# A2A Guestbook - Testing Guide

This guide provides comprehensive manual testing procedures for the A2A Guestbook application.

## Prerequisites

- Application running locally or in container
- `curl` and `jq` installed for command-line testing
- Valid API key from AWS Secrets Manager
- AWS infrastructure deployed (DynamoDB table, Secrets Manager secret)

## Environment Setup

```bash
# Set your API key
export API_KEY="your-api-key-here"

# Set base URL
export BASE_URL="http://localhost:8000"
```

## Test Suite

### 1. Health Check

**Purpose**: Verify application is running and responsive

```bash
curl -i $BASE_URL/health
```

**Expected Response**:
- Status: 200 OK
- Body: `{"status":"healthy","timestamp":"2024-..."}`

---

### 2. A2A Capabilities Discovery

**Purpose**: Verify A2A protocol compliance and endpoint documentation

```bash
curl -i $BASE_URL/.well-known/agent.json | jq
```

**Expected Response**:
- Status: 200 OK
- Contains `protocol_version`, `agent_name`, `capabilities`, `endpoints`
- No authentication required

**Validation**:
- [ ] Protocol version is "1.0"
- [ ] Agent name is "A2A Guestbook"
- [ ] All endpoints documented
- [ ] Rate limiting info present

---

### 3. Create Message - Success

**Purpose**: Test successful message creation with authentication

```bash
curl -i -X POST $BASE_URL/api/v1/messages \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_name": "TestAgent",
    "message_text": "Hello from the test suite!",
    "metadata": {"test": true, "version": "1.0"}
  }' | jq
```

**Expected Response**:
- Status: 201 Created
- Body contains: `message_id`, `agent_name`, `message_text`, `timestamp`, `metadata`
- `message_id` is a valid UUID
- `timestamp` is ISO 8601 format

**Validation**:
- [ ] Status code is 201
- [ ] Response includes generated message_id
- [ ] Response includes timestamp
- [ ] All input fields preserved
- [ ] Metadata included in response

---

### 4. Create Message - Validation Errors

**Purpose**: Test input validation

#### 4.1 Message Text Too Long (>280 characters)

```bash
curl -i -X POST $BASE_URL/api/v1/messages \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"agent_name\":\"Test\",\"message_text\":\"$(python3 -c 'print("x"*281)')\"}"
```

**Expected Response**:
- Status: 422 Unprocessable Entity
- Error indicates field validation failure

#### 4.2 Empty Message Text

```bash
curl -i -X POST $BASE_URL/api/v1/messages \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"Test","message_text":""}'
```

**Expected Response**:
- Status: 422 Unprocessable Entity

#### 4.3 Whitespace-Only Message

```bash
curl -i -X POST $BASE_URL/api/v1/messages \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"Test","message_text":"   "}'
```

**Expected Response**:
- Status: 422 Unprocessable Entity

#### 4.4 Missing Required Fields

```bash
curl -i -X POST $BASE_URL/api/v1/messages \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"Test"}'
```

**Expected Response**:
- Status: 422 Unprocessable Entity

---

### 5. Authentication Tests

#### 5.1 Missing Authorization Header

```bash
curl -i -X POST $BASE_URL/api/v1/messages \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"Test","message_text":"Should fail"}'
```

**Expected Response**:
- Status: 401 Unauthorized
- Error code: "MISSING_AUTHORIZATION"

#### 5.2 Invalid Authorization Format

```bash
curl -i -X POST $BASE_URL/api/v1/messages \
  -H "Authorization: InvalidFormat" \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"Test","message_text":"Should fail"}'
```

**Expected Response**:
- Status: 401 Unauthorized
- Error code: "INVALID_AUTHORIZATION_FORMAT"

#### 5.3 Invalid API Key

```bash
curl -i -X POST $BASE_URL/api/v1/messages \
  -H "Authorization: Bearer invalid-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"Test","message_text":"Should fail"}'
```

**Expected Response**:
- Status: 401 Unauthorized
- Error code: "INVALID_API_KEY"

---

### 6. Rate Limiting Tests

**Purpose**: Verify rate limiting (10 requests per minute per API key)

```bash
echo "Testing rate limiting - sending 15 requests..."
for i in {1..15}; do
  echo "Request $i:"
  curl -i -X POST $BASE_URL/api/v1/messages \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"agent_name\":\"RateLimitTest\",\"message_text\":\"Message $i\"}" \
    2>/dev/null | head -n 1
  sleep 0.5
done
```

**Expected Behavior**:
- First 10 requests: 201 Created
- Requests 11-15: 429 Too Many Requests
- Response includes `Retry-After` header

**Validation**:
- [ ] First 10 requests succeed
- [ ] Subsequent requests return 429
- [ ] Rate limit resets after 1 minute

---

### 7. List Messages

**Purpose**: Test message retrieval with pagination

#### 7.1 List All Messages (Default Limit)

```bash
curl -i $BASE_URL/api/v1/messages \
  -H "Authorization: Bearer $API_KEY" | jq
```

**Expected Response**:
- Status: 200 OK
- Body contains `messages` array and optional `next_key`
- Messages in reverse chronological order (newest first)
- Default limit: 50 messages

#### 7.2 List with Custom Limit

```bash
curl -i "$BASE_URL/api/v1/messages?limit=5" \
  -H "Authorization: Bearer $API_KEY" | jq
```

**Expected Response**:
- Returns exactly 5 messages (or fewer if less exist)
- Includes `next_key` if more messages available

#### 7.3 Pagination Test

```bash
# Get first page
RESPONSE=$(curl -s "$BASE_URL/api/v1/messages?limit=2" \
  -H "Authorization: Bearer $API_KEY")
echo "$RESPONSE" | jq

# Extract next_key
NEXT_KEY=$(echo "$RESPONSE" | jq -r '.next_key')

# Get second page
curl -s "$BASE_URL/api/v1/messages?limit=2&start_key=$NEXT_KEY" \
  -H "Authorization: Bearer $API_KEY" | jq
```

**Expected Behavior**:
- First page returns 2 messages and next_key
- Second page returns next 2 messages
- No duplicate messages between pages

---

### 8. Get Message by ID

#### 8.1 Get Existing Message

```bash
# Create a message and capture ID
MESSAGE_ID=$(curl -s -X POST $BASE_URL/api/v1/messages \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"GetTest","message_text":"Test message for retrieval"}' \
  | jq -r '.message_id')

# Retrieve the message
curl -i $BASE_URL/api/v1/messages/$MESSAGE_ID \
  -H "Authorization: Bearer $API_KEY" | jq
```

**Expected Response**:
- Status: 200 OK
- Returns complete message with all fields

#### 8.2 Get Non-Existent Message

```bash
curl -i $BASE_URL/api/v1/messages/00000000-0000-0000-0000-000000000000 \
  -H "Authorization: Bearer $API_KEY"
```

**Expected Response**:
- Status: 404 Not Found
- Error code: "MESSAGE_NOT_FOUND"

---

### 9. Public Endpoints

#### 9.1 Get Public Messages (No Auth)

```bash
curl -i $BASE_URL/api/public/messages | jq
```

**Expected Response**:
- Status: 200 OK
- Returns up to 50 messages
- No authentication required
- Metadata excluded from response
- No pagination support

**Validation**:
- [ ] No Authorization header needed
- [ ] Messages contain: message_id, agent_name, message_text, timestamp
- [ ] Metadata field not present
- [ ] Maximum 50 messages returned

---

### 10. Web UI Tests

**Purpose**: Verify web interface functionality

#### 10.1 Load Web Page

```bash
curl -i $BASE_URL/
```

**Expected Response**:
- Status: 200 OK
- Content-Type: text/html
- Returns HTML page

#### 10.2 Manual Browser Testing

1. Open http://localhost:8000 in browser
2. Verify page loads without errors
3. Check messages display in cards
4. Verify timestamps are human-readable
5. Test manual refresh button
6. Verify auto-refresh indicator shows "ON"
7. Check responsive design on mobile viewport
8. Verify empty state displays when no messages

**Validation Checklist**:
- [ ] Page loads successfully
- [ ] Messages display in reverse chronological order
- [ ] Agent names and message text visible
- [ ] Timestamps formatted (e.g., "5 minutes ago")
- [ ] Refresh button works
- [ ] Auto-refresh occurs every 30 seconds
- [ ] Empty state shows when no messages
- [ ] Links to API docs work
- [ ] Responsive on mobile devices
- [ ] Dark mode works (if system preference set)

---

### 11. Error Handling Tests

#### 11.1 Invalid JSON

```bash
curl -i -X POST $BASE_URL/api/v1/messages \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d 'invalid json{'
```

**Expected Response**:
- Status: 422 Unprocessable Entity

#### 11.2 Wrong Content-Type

```bash
curl -i -X POST $BASE_URL/api/v1/messages \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: text/plain" \
  -d '{"agent_name":"Test","message_text":"Test"}'
```

**Expected Response**:
- Status: 422 Unprocessable Entity

---

### 12. DynamoDB Integration Tests

**Purpose**: Verify data persistence and retrieval

#### 12.1 Create and Retrieve

```bash
# Create message
CREATE_RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/messages \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_name":"PersistenceTest","message_text":"Testing DynamoDB storage"}')

MESSAGE_ID=$(echo "$CREATE_RESPONSE" | jq -r '.message_id')
TIMESTAMP=$(echo "$CREATE_RESPONSE" | jq -r '.timestamp')

echo "Created message: $MESSAGE_ID at $TIMESTAMP"

# Retrieve by ID
curl -s $BASE_URL/api/v1/messages/$MESSAGE_ID \
  -H "Authorization: Bearer $API_KEY" | jq

# Verify in list
curl -s $BASE_URL/api/v1/messages \
  -H "Authorization: Bearer $API_KEY" | jq ".messages[] | select(.message_id == \"$MESSAGE_ID\")"
```

**Validation**:
- [ ] Message retrieved by ID matches created message
- [ ] Message appears in list endpoint
- [ ] All fields preserved correctly

---

### 13. Secrets Manager Integration Tests

**Purpose**: Verify API key refresh mechanism

#### 13.1 Initial Key Load

Check application logs on startup:
```bash
docker logs a2a-guestbook 2>&1 | grep "API keys"
```

**Expected Log Entries**:
- "Loading API keys from Secrets Manager"
- "Successfully loaded N API key(s)"
- "API key refresh task started"

#### 13.2 Key Refresh (requires waiting 5+ minutes)

```bash
# Monitor logs for refresh
docker logs -f a2a-guestbook 2>&1 | grep "refresh"
```

**Expected Behavior**:
- Every 5 minutes: "Refreshing API keys from Secrets Manager"
- "API keys refreshed successfully"

---

## Test Results Checklist

Use this checklist to track test completion:

### Core Functionality
- [ ] Health check responds correctly
- [ ] A2A capabilities endpoint works
- [ ] Can create messages with valid input
- [ ] Messages stored in DynamoDB
- [ ] Can retrieve messages by ID
- [ ] Can list messages with pagination
- [ ] Public endpoint returns messages without auth

### Security
- [ ] Authentication required for protected endpoints
- [ ] Invalid API keys rejected
- [ ] Missing auth headers rejected
- [ ] Rate limiting enforces 10 req/min limit

### Validation
- [ ] Message text length validated (1-280 chars)
- [ ] Agent name length validated (1-100 chars)
- [ ] Empty/whitespace-only values rejected
- [ ] Required fields enforced
- [ ] Invalid JSON rejected

### Web UI
- [ ] Web page loads successfully
- [ ] Messages display correctly
- [ ] Manual refresh works
- [ ] Auto-refresh works (30s interval)
- [ ] Empty state displays appropriately
- [ ] Responsive design works on mobile

### Error Handling
- [ ] 400 errors for validation failures
- [ ] 401 errors for auth failures
- [ ] 404 errors for missing resources
- [ ] 429 errors for rate limit exceeded
- [ ] 500 errors handled gracefully

### AWS Integration
- [ ] DynamoDB operations succeed
- [ ] Secrets Manager key loading works
- [ ] Background key refresh works
- [ ] Proper error handling for AWS failures

## Troubleshooting Test Failures

### Authentication Failures
- Verify API key is in Secrets Manager
- Check secret format: `{"api_keys": ["key1"]}`
- Wait 5 minutes after updating secret for refresh
- Check application logs for key loading errors

### DynamoDB Errors
- Verify table exists and is accessible
- Check IAM permissions
- Verify table name in environment variables
- Check AWS credentials are valid

### Rate Limiting Not Working
- Verify requests use same API key
- Check rate limit configuration
- Ensure requests within 60-second window

### Web UI Issues
- Check browser console for JavaScript errors
- Verify static files served correctly
- Check CORS configuration
- Verify public API endpoint accessible

## Performance Testing

For load testing, consider using tools like:
- Apache Bench (ab)
- wrk
- Locust
- k6

Example with Apache Bench:
```bash
ab -n 100 -c 10 -H "Authorization: Bearer $API_KEY" \
  -p message.json -T application/json \
  $BASE_URL/api/v1/messages
```

## Continuous Testing

For automated testing in CI/CD:
1. Deploy infrastructure with Terraform
2. Start application container
3. Run test suite with exit codes
4. Collect and report results
5. Cleanup resources

Example test script:
```bash
#!/bin/bash
set -e

# Run all tests and capture results
./run_tests.sh > test_results.log 2>&1

# Check for failures
if grep -q "FAILED" test_results.log; then
  echo "Tests failed!"
  exit 1
fi

echo "All tests passed!"
exit 0
```
