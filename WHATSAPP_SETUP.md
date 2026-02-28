# WhatsApp Integration Setup Guide

**Version:** 1.0  
**Date:** 2026-02-25  
**Tier:** Gold

---

## Overview

This guide covers setting up the fully autonomous WhatsApp Agent with Twilio integration for the AI Employee system.

---

## Architecture

```
User WhatsApp Message
        ↓
Twilio WhatsApp API
        ↓
Webhook (Flask Server :5000)
        ↓
WhatsApp Watcher
        ↓
Inbox Task (whatsapp_task_*.md)
        ↓
Filesystem Watcher → Needs_Action
        ↓
Planner Agent → Analysis
        ↓
Manager Agent → Skill Routing
        ↓
Task Execution
        ↓
Done Folder
        ↓
WhatsApp Agent
        ↓
Twilio API → Auto Reply to User
```

---

## Quick Start (Demo Mode)

For testing without Twilio credentials:

### Step 1: Install Dependencies

```bash
cd /mnt/d/Quarter_4/Hackathon_0/AI_Employee_Vault
source venv/bin/activate  # or create venv if needed
pip install -r requirements.txt
```

### Step 2: Start WhatsApp Watcher

```bash
python Watchers/whatsapp_watcher.py
```

The watcher will:
- Start webhook server on `http://127.0.0.1:5000/whatsapp/webhook`
- Generate demo messages every 60 seconds
- Create tasks in `Inbox/` folder

### Step 3: Start WhatsApp Agent

```bash
python Agents/whatsapp_agent.py
```

The agent will:
- Monitor `Done/` folder for completed WhatsApp tasks
- Format and log replies (demo mode - no actual sending)
- Handle retry logic for failed replies

---

## Production Setup (With Twilio)

### Step 1: Create Twilio Account

1. Go to [Twilio Console](https://console.twilio.com/)
2. Sign up for an account
3. Enable WhatsApp sandbox (for testing) or production number

### Step 2: Get Credentials

From Twilio Console:
- **Account SID**: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- **Auth Token**: Found in Settings → General
- **WhatsApp Number**: Sandbox number or your production number

### Step 3: Configure Environment Variables

**Option A: Environment Variables (Recommended)**

```bash
export TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
export TWILIO_AUTH_TOKEN="your_auth_token_here"
export TWILIO_WHATSAPP_NUMBER="+14155238886"
```

**Option B: Update Config File**

Edit `Config/twilio_config.json`:

```json
{
  "account_sid": "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "auth_token": "your_auth_token_here",
  "whatsapp_number": "+14155238886"
}
```

⚠️ **Security Warning**: Never commit real credentials to version control!

### Step 4: Setup Webhook (Local Testing with ngrok)

```bash
# Install ngrok if not installed
# Download from: https://ngrok.com/

# Start ngrok tunnel
ngrok http 5000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
```

### Step 5: Configure Twilio Webhook

1. Go to Twilio Console → Messaging → Try it out → Send a WhatsApp message
2. Click on "Sandbox Settings"
3. Set **Webhook URL** to: `https://YOUR_NGROK_URL.ngrok.io/whatsapp/webhook`
4. Set **HTTP Method** to: `HTTP POST`
5. Save configuration

### Step 6: Start System

```bash
# Start watchers (includes WhatsApp watcher)
bash run_watchers.sh

# In another terminal, start agents (includes WhatsApp agent)
bash run_agents.sh
```

### Step 7: Test

1. Send a WhatsApp message to the Twilio sandbox number
2. Check `Inbox/` folder for new task file
3. Wait for AI Employee to process the task
4. Check `Done/` folder for completed task
5. Receive WhatsApp reply automatically

---

## File Structure

```
AI_Employee_Vault/
├── Agents/
│   └── whatsapp_agent.py          # Auto-reply agent
├── Watchers/
│   └── whatsapp_watcher.py        # Webhook server + task creator
├── Skills/
│   └── whatsapp_communication.SKILL.md  # Skill definition
├── Config/
│   └── twilio_config.json         # Twilio configuration
├── Inbox/
│   └── whatsapp_task_*.md         # Created from WhatsApp messages
├── Logs/
│   ├── whatsapp_watcher_*.log     # Watcher logs
│   ├── whatsapp_agent_*.log       # Agent logs
│   └── whatsapp_replies_*.md      # Reply activity log
├── webhook_server.py              # Standalone webhook server
├── run_watchers.sh                # Startup script (watchers)
├── run_agents.sh                  # Startup script (agents)
└── requirements.txt               # Python dependencies
```

---

## Configuration Options

### Twilio Config (`Config/twilio_config.json`)

| Field | Description | Default |
|-------|-------------|---------|
| `account_sid` | Twilio Account SID | - |
| `auth_token` | Twilio Auth Token | - |
| `whatsapp_number` | WhatsApp sender number | - |
| `webhook.host` | Webhook bind address | `127.0.0.1` |
| `webhook.port` | Webhook port | `5000` |
| `webhook.endpoint` | Webhook path | `/whatsapp/webhook` |
| `settings.auto_reply` | Enable auto-replies | `true` |
| `settings.reply_on_complete` | Reply on success | `true` |
| `settings.reply_on_failure` | Reply on failure | `true` |
| `settings.max_retries` | Max retry attempts | `3` |
| `settings.retry_delay_seconds` | Delay between retries | `30` |

---

## Task Format

### Incoming Task (Inbox)

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

- [ ] <extracted action items>
```

### Auto-Reply Format

**Success:**
```
✅ Task Completed

Result:
<execution summary>

Your AI Employee has processed your request.
```

**Failure:**
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

## Monitoring

### Check Watcher Status

```bash
curl http://localhost:5000/health
curl http://localhost:5000/status
```

### View Logs

```bash
# Watcher logs
tail -f Logs/whatsapp_watcher_*.log

# Agent logs
tail -f Logs/whatsapp_agent_*.log

# Reply activity log
cat Logs/whatsapp_replies_*.md
```

### Check Tasks

```bash
# Pending tasks
ls -la Inbox/whatsapp_task_*.md

# Completed tasks
ls -la Done/whatsapp_task_*.md
```

---

## Troubleshooting

### Webhook Not Receiving Messages

1. Check ngrok tunnel is running
2. Verify Twilio webhook URL matches ngrok URL
3. Ensure webhook server is running on port 5000
4. Check firewall settings

### Messages Not Creating Tasks

1. Verify `Inbox/` folder exists and is writable
2. Check watcher logs for errors
3. Ensure Flask is installed: `pip install flask`

### Replies Not Sending

1. Verify Twilio credentials are set
2. Check agent logs for API errors
3. Ensure WhatsApp number format is correct (`+1234567890`)
4. Verify Twilio account has WhatsApp enabled

### Demo Mode Only

If seeing "Demo mode" messages:
1. Set `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` environment variables
2. Restart WhatsApp agent
3. Check logs for "Twilio client initialized successfully"

---

## Production Deployment

### Deploy Webhook Server

For production, deploy the standalone webhook server:

```bash
# Using Gunicorn (production WSGI server)
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 webhook_server:app
```

### HTTPS/SSL

Use a reverse proxy (nginx, Apache) for HTTPS:

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location /whatsapp/webhook {
        proxy_pass http://127.0.0.1:5000/whatsapp/webhook;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Process Management

Use systemd or supervisor:

```ini
# /etc/systemd/system/whatsapp-watcher.service
[Unit]
Description=WhatsApp Watcher
After=network.target

[Service]
Type=simple
User=ai-employee
WorkingDirectory=/path/to/AI_Employee_Vault
ExecStart=/path/to/venv/bin/python Watchers/whatsapp_watcher.py
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Security Best Practices

1. **Never commit credentials** - Use environment variables
2. **Validate Twilio signatures** - Implement request signing verification
3. **Use HTTPS** - Always use HTTPS for production webhooks
4. **Restrict access** - Bind to localhost, use reverse proxy
5. **Monitor logs** - Regularly review logs for suspicious activity
6. **Rate limiting** - Implement rate limiting for webhook endpoint

---

## API Reference

### Webhook Endpoint

**POST** `/whatsapp/webhook`

Receives Twilio WhatsApp messages.

**Request Body (Form Data):**
- `From`: Sender's WhatsApp number
- `To`: Receiver's WhatsApp number
- `Body`: Message text
- `MessageSid`: Unique message ID
- `Timestamp`: Message timestamp

**Response:** TwiML response (empty for acknowledgment)

### Health Check

**GET** `/health`

```json
{
  "status": "healthy",
  "service": "WhatsApp Webhook Server",
  "timestamp": "2026-02-25T10:30:00"
}
```

### Status

**GET** `/status`

```json
{
  "host": "127.0.0.1",
  "port": 5000,
  "endpoint": "/whatsapp/webhook",
  "inbox_dir": "/path/to/Inbox"
}
```

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [Skills/whatsapp_communication.SKILL.md](Skills/whatsapp_communication.SKILL.md) - Skill definition
- [Twilio WhatsApp API Docs](https://www.twilio.com/docs/whatsapp)

---

## Support

For issues or questions:
1. Check logs in `Logs/` folder
2. Review this setup guide
3. Consult Twilio documentation
4. Check AI Employee documentation
