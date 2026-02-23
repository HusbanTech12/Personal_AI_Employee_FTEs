# Skill: Email

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `email` |
| **Tier** | Silver |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Communication |
| **MCP Server** | `email_mcp_server.py` |

---

## Purpose

Send emails on behalf of the AI Employee system. All email operations are routed through the **Email MCP Server** for security and centralized management.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Email Agent   │ ──→ │  Email MCP       │ ──→ │   SMTP Server   │
│   (AI Agent)    │     │  Server          │     │   (Gmail/etc)   │
│                 │     │  (HTTP API)      │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
       │                        │
       │                        │
       ▼                        ▼
  Reads task              Handles actual
  from Needs_Action       email sending
```

---

## Accepted Inputs

| Input Type | Description | Examples |
|------------|-------------|----------|
| **Send Request** | Send an email | Reply to inquiry, send report, notify stakeholder |
| **Batch Send** | Send multiple emails | Newsletter, status updates |
| **Scheduled** | Queue for later sending | Reminder, follow-up |

**Task Format:**
```markdown
---
title: Send Email
status: needs_action
priority: standard
skill: email
---

## Email Details

**To:** recipient@example.com
**Subject:** Project Update
**Priority:** normal

## Content

Please send the following email...
```

---

## MCP Server API

### Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `EMAIL_MCP_HOST` | Server bind address | `127.0.0.1` |
| `EMAIL_MCP_PORT` | Server port | `8765` |
| `SMTP_SERVER` | SMTP server | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP port | `587` |
| `SMTP_USER` | SMTP username | - |
| `SMTP_PASSWORD` | SMTP password | - |
| `FROM_EMAIL` | Sender email | - |

### Endpoints

#### POST /send

Send an email.

**Request:**
```json
{
  "to": "recipient@example.com",
  "subject": "Email Subject",
  "body": "Email body content",
  "html": false,
  "cc": "cc@example.com",
  "bcc": "bcc@example.com",
  "priority": "normal",
  "agent_id": "email_agent"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Email sent successfully",
  "to": "recipient@example.com",
  "subject": "Email Subject",
  "timestamp": "2026-02-23T15:30:00",
  "agent_id": "email_agent"
}
```

**Response (Failure):**
```json
{
  "success": false,
  "error": "Missing required field: to",
  "required_fields": ["to", "subject", "body"]
}
```

#### GET /status

Get server status.

**Response:**
```json
{
  "status": "running",
  "host": "127.0.0.1",
  "port": 8765,
  "smtp_configured": true,
  "demo_mode": false,
  "queued_emails": 0,
  "from_email": "sender@example.com",
  "timestamp": "2026-02-23T15:30:00"
}
```

#### GET /queue

View queued emails (for offline sending).

**Response:**
```json
{
  "queued_emails": [
    {
      "to": "user@example.com",
      "subject": "Test",
      "body": "Hello",
      "queued_at": "2026-02-23T15:00:00",
      "status": "queued"
    }
  ],
  "count": 1
}
```

#### POST /flush

Send all queued emails.

**Response:**
```json
{
  "flushed": 2,
  "results": [
    {"success": true, "to": "user1@example.com"},
    {"success": true, "to": "user2@example.com"}
  ]
}
```

#### POST /queue/add

Add email to queue without sending immediately.

**Request:**
```json
{
  "to": "recipient@example.com",
  "subject": "Scheduled Email",
  "body": "This will be sent later"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Email queued",
  "queue_size": 1
}
```

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy"
}
```

---

## Execution Steps

### Step 1: Parse Email Request

```
Read task file
↓
Extract recipient, subject, body
↓
Validate required fields
↓
Identify CC/BCC if present
```

### Step 2: Connect to MCP Server

```
Build HTTP request
↓
POST to http://localhost:8765/send
↓
Include email data as JSON
↓
Wait for response
```

### Step 3: Handle Response

```
Check success field
↓
If success: Log and mark complete
↓
If failure: Retry or flag error
↓
Update task status
```

### Step 4: Log Activity

```
Record email sent
↓
Update activity log
↓
Update Dashboard metrics
```

---

## Output Format

### Success Response

```markdown
## Email Sent

**To:** recipient@example.com
**Subject:** Email Subject
**Sent:** 2026-02-23 15:30:00
**Status:** Delivered

### Content Preview

Email body content (first 200 characters)...
```

### Failure Response

```markdown
## Email Failed

**To:** recipient@example.com
**Subject:** Email Subject
**Error:** [Error message]

### Retry Options

- Check SMTP configuration
- Verify recipient email address
- Retry in 5 minutes
```

---

## Completion Rules

An email task is **complete** when:

- [ ] **MCP server responded** - HTTP 200 received
- [ ] **Success confirmed** - `success: true` in response
- [ ] **Logged** - Activity log updated
- [ ] **Task updated** - Frontmatter status changed to done

---

## Error Handling

| Error | Handling |
|-------|----------|
| MCP server not running | Start server, retry |
| SMTP not configured | Log warning, use demo mode |
| Invalid recipient | Return error, don't retry |
| Network error | Retry up to 3 times |
| Authentication failed | Log error, require config update |

---

## Security

### Credential Management

- SMTP credentials stored in **environment variables only**
- Never exposed to agents directly
- MCP server runs on localhost (127.0.0.1)
- No external network access required

### Demo Mode

If SMTP is not configured, server runs in **demo mode**:
- Emails are logged but not sent
- Response includes `"demo": true`
- Safe for testing without credentials

---

## Examples

### Example 1: Simple Email

**Task:**
```markdown
---
title: Send Meeting Confirmation
skill: email
---

Send email to team@example.com

Subject: Meeting Confirmed for Tomorrow

Body: Hi team, just confirming our meeting tomorrow at 10 AM.
```

**Agent sends:**
```json
{
  "to": "team@example.com",
  "subject": "Meeting Confirmed for Tomorrow",
  "body": "Hi team, just confirming our meeting tomorrow at 10 AM.",
  "agent_id": "email_agent"
}
```

### Example 2: HTML Email

**Request:**
```json
{
  "to": "client@example.com",
  "subject": "Monthly Report",
  "body": "<h1>Monthly Report</h1><p>See attached summary...</p>",
  "html": true
}
```

### Example 3: Email with CC

**Request:**
```json
{
  "to": "direct@example.com",
  "cc": "manager@example.com, boss@example.com",
  "subject": "Project Update",
  "body": "Here's the weekly update..."
}
```

---

## Integration with Other Skills

| Scenario | Handoff To | Information Passed |
|----------|------------|-------------------|
| Email needs content | `documentation` | Draft email content |
| Email is notification | `planner` | Event details |
| Email requires research | `research` | Information to include |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Server won't start | Check port 8765 is available |
| Emails not sending | Verify SMTP credentials |
| Connection refused | Ensure MCP server is running |
| Authentication error | Use App Password for Gmail |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-23 | Initial implementation with MCP server |
