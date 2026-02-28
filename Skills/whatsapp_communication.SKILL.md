# Skill: WhatsApp Communication

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `whatsapp_communication` |
| **Tier** | Gold |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Communication |
| **Integration** | Twilio WhatsApp API |

---

## Purpose

External communication with users via WhatsApp. Sends formatted responses using Twilio WhatsApp API after task execution completes.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  WhatsApp       │ ──→ │  WhatsApp        │ ──→ │  Twilio         │
│  Agent          │     │  Watcher         │     │  WhatsApp API   │
│  (Reply Logic)  │     │  (Webhook)       │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
       │                        │
       │                        │
       ▼                        ▼
  Reads execution         Receives incoming
  result from Done        messages → Inbox
```

---

## Flow

### Inbound (Message → Task)

```
User sends WhatsApp message
        ↓
Twilio receives message
        ↓
Twilio POST to webhook (port 5000)
        ↓
WhatsApp Watcher parses message
        ↓
Creates task in /Inbox
        ↓
Filesystem Watcher moves to Needs_Action
        ↓
Planner Agent analyzes task
        ↓
Manager Agent routes to skill
        ↓
Task executed
```

### Outbound (Result → Reply)

```
Task completed → moved to /Done
        ↓
WhatsApp Agent scans Done folder
        ↓
Extracts sender number from task
        ↓
Reads execution result
        ↓
Formats reply message
        ↓
Sends via Twilio WhatsApp API
        ↓
User receives reply
```

---

## Accepted Inputs

| Input Type | Description | Examples |
|------------|-------------|----------|
| **Incoming Message** | WhatsApp message from user | Questions, requests, commands |
| **Execution Result** | Task completion status | Success, failure, summary |
| **Reply Trigger** | Auto-reply on completion | Configurable per result type |

---

## Twilio Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | `ACxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | Twilio Auth Token | `your_auth_token` |
| `TWILIO_WHATSAPP_NUMBER` | WhatsApp sender number | `+14155238886` |

### Config File

Location: `Config/twilio_config.json`

```json
{
  "account_sid": "${TWILIO_ACCOUNT_SID}",
  "auth_token": "${TWILIO_AUTH_TOKEN}",
  "whatsapp_number": "${TWILIO_WHATSAPP_NUMBER}",
  "webhook": {
    "host": "127.0.0.1",
    "port": 5000,
    "endpoint": "/whatsapp/webhook"
  },
  "settings": {
    "auto_reply": true,
    "reply_on_complete": true,
    "reply_on_failure": true,
    "max_retries": 3,
    "retry_delay_seconds": 30
  }
}
```

---

## Execution Steps

### Step 1: Receive Webhook

```
Twilio POST request
        ↓
Parse form data:
  - From: sender number
  - Body: message text
  - MessageSid: unique ID
  - Timestamp: message time
        ↓
Validate request
```

### Step 2: Create Task

```
Extract sender info
        ↓
Determine priority (high/medium/standard)
        ↓
Extract action items from message
        ↓
Generate markdown task
        ↓
Save to /Inbox folder
```

### Step 3: Monitor Completion

```
Scan /Done folder
        ↓
Find WhatsApp tasks with execution results
        ↓
Parse task frontmatter for sender
        ↓
Extract execution result
```

### Step 4: Send Reply

```
Format reply based on result:
  - Success: ✅ Task Completed + summary
  - Failure: ⚠️ Task Failed + retry notice
        ↓
Send via Twilio API
        ↓
Log reply to activity log
```

---

## Message Formats

### Task Creation Format

```markdown
---
title: WhatsApp: <message preview>
status: New
priority: <high|medium|standard>
created: <timestamp>
skill: task_processor
source: WhatsApp
sender: <phone number>
message_sid: <Twilio message SID>
approval: Not Required
---

# WhatsApp Message Task

**From:** <sender>

**Received:** <timestamp>

**Source:** WhatsApp

**Priority:** <priority>

---

## Message Content

<message body>

---

## Action Items

- [ ] <extracted action item 1>
- [ ] <extracted action item 2>
```

### Success Reply Format

```
✅ Task Completed

Result:
<execution summary>

Your AI Employee has processed your request.
```

### Failure Reply Format

```
⚠️ Task Failed

<error summary>

AI Employee is retrying your request.
Please stand by.
```

---

## Priority Detection

| Priority | Keywords |
|----------|----------|
| **High** | urgent, asap, emergency, critical, important, call me, immediate, deadline, help |
| **Medium** | meeting, tomorrow, today, reminder, please, can you, could you, question |
| **Standard** | All other messages |

---

## Output Format

### Activity Log Entry

```markdown
---

## Reply Log

**Timestamp:** 2026-02-25 10:30:00
**Task:** whatsapp_task_20260225_103000_1234567890
**Sender:** whatsapp:+1234567890
**Original Message:** Can you send me the report...
**Result:** Success
**Reply Sent:** ✅ Yes

```

---

## Completion Rules

A WhatsApp communication task is **complete** when:

- [ ] **Reply formatted** - Success or failure message prepared
- [ ] **Twilio API called** - Message sent via API
- [ ] **Response confirmed** - API returned success
- [ ] **Logged** - Activity log updated
- [ ] **Task marked** - Task ID added to processed set

---

## Error Handling

| Error | Handling |
|-------|----------|
| Twilio credentials missing | Run in demo mode, log messages |
| Invalid sender number | Skip reply, log warning |
| API rate limit | Retry after delay |
| Network error | Add to retry queue |
| Max retries exceeded | Log failure, stop retrying |

### Retry Logic

```
Reply fails
        ↓
Add to retry queue
        ↓
Wait retry_delay_seconds (30s default)
        ↓
Retry (up to max_retries times)
        ↓
If still failing: log and give up
```

---

## Security

### Credential Management

- Credentials loaded from **environment variables**
- Config file uses `${VAR}` placeholder syntax
- Never commit real credentials to version control
- Twilio Auth Token treated as secret

### Webhook Security

- Validate Twilio signatures (production)
- Run on localhost by default
- Use ngrok or reverse proxy for public access
- Implement request signing verification

---

## Demo Mode

When Twilio credentials are not configured:

- Webhook server still runs locally
- Messages logged but not sent
- Demo messages generated every 60 seconds
- Safe for development and testing

---

## Integration with Other Skills

| Scenario | Handoff To | Information Passed |
|----------|------------|-------------------|
| Task needs processing | `task_processor` | Full task context |
| Task needs approval | `approval` | Task details + sender |
| Task requires email | `email` | Email content + recipient |
| Task is informational | `documentation` | Content to document |

---

## Testing

### Local Testing with ngrok

```bash
# 1. Start ngrok tunnel
ngrok http 5000

# 2. Copy the HTTPS URL
# e.g., https://abc123.ngrok.io

# 3. Configure Twilio webhook
# In Twilio Console:
# WhatsApp Sandbox Settings → Webhook URL
# Set to: https://abc123.ngrok.io/whatsapp/webhook

# 4. Start WhatsApp Watcher
python Watchers/whatsapp_watcher.py

# 5. Send WhatsApp message to sandbox number
```

### Twilio Sandbox Setup

1. Go to Twilio Console → Messaging → Try it out → Send a WhatsApp message
2. Follow instructions to join sandbox
3. Send messages to test webhook

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Webhook not receiving messages | Check ngrok tunnel, verify Twilio webhook URL |
| Messages not creating tasks | Check Inbox folder permissions, verify watcher running |
| Replies not sending | Verify Twilio credentials, check WhatsApp number format |
| Demo mode only | Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN env vars |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial implementation with Twilio integration |

---

## Related Files

| File | Purpose |
|------|---------|
| `Agents/whatsapp_agent.py` | Reply logic and Twilio integration |
| `Watchers/whatsapp_watcher.py` | Webhook server and task creation |
| `Config/twilio_config.json` | Twilio configuration |
| `Skills/whatsapp_communication.SKILL.md` | This file |
