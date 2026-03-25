# Client Filter Configuration

## Overview

The AI Employee system now includes **client filtering** to ensure only messages from configured clients are processed. Random or unsolicited messages are automatically ignored and logged.

---

## Configuration File

**Location:** `Config/client_list.env`

This file contains the list of approved clients for each communication channel.

---

## Client Lists

### LinkedIn Clients

```env
LINKEDIN_CLIENTS=TechCorp Inc.,Acme Corporation,Global Solutions Ltd
```

- **Format:** Comma-separated list of names/company names
- **Matching:** Case-insensitive, substring matching supported
- **Example:** "TechCorp" will match "TechCorp Inc."

### WhatsApp Clients

```env
WHATSAPP_CLIENTS=+1234567890,+1987654321,+1122334455
```

- **Format:** Comma-separated list with country codes
- **Matching:** Exact or partial number matching
- **Note:** Include full number with `+` prefix

### Gmail Clients

```env
GMAIL_CLIENTS=client@company.com,boss@company.com,@clientdomain.com
```

- **Format:** Comma-separated list
- **Domain matching:** Prefix with `@` to match entire domain
- **Example:** `@clientdomain.com` matches all emails from that domain

---

## Filter Settings

```env
# Enable/disable client filtering (true/false)
CLIENT_FILTER_ENABLED=true

# Log ignored non-client messages (true/false)
LOG_IGNORED_MESSAGES=true
```

---

## How It Works

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    MESSAGE RECEIVED                             │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              CLIENT FILTER CHECK                                │
│  - LinkedIn: Check sender name against LINKEDIN_CLIENTS         │
│  - WhatsApp: Check number against WHATSAPP_CLIENTS              │
│  - Gmail: Check email/domain against GMAIL_CLIENTS              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
            ┌──────────────┴──────────────┐
            │                             │
            ▼                             ▼
    ┌───────────────┐            ┌───────────────┐
    │   IS CLIENT   │            │  NOT CLIENT   │
    └───────┬───────┘            └───────┬───────┘
            │                             │
            ▼                             ▼
    ┌───────────────┐            ┌───────────────┐
    │ PROCESS TASK  │            │  IGNORE +     │
    │               │            │  LOG          │
    │ → Inbox       │            │               │
    │ → Needs_Action│            │ No task created│
    │ → Execution   │            │ Message logged │
    └───────────────┘            └───────────────┘
```

### Updated Components

| Component | File | Change |
|-----------|------|--------|
| LinkedIn Watcher | `Watchers/linkedin_watcher.py` | Added `is_client()` method |
| WhatsApp Watcher | `Watchers/whatsapp_watcher.py` | Added `is_client()` method |
| Gmail Watcher | `Watchers/gmail_watcher.py` | Added `is_client()` method |
| Task Executor | `task_executor.py` | Added secondary client check |

---

## Logging

### Client Message Processed

```
2026-03-25 22:27:46 - LinkedInWatcher - INFO - [LINKEDIN] Client message processed: connection_request from TechCorp Inc.
```

### Non-Client Message Ignored

```
2026-03-25 22:27:46 - LinkedInWatcher - INFO - [LINKEDIN] Ignored non-client message from: Random Person
```

---

## Testing

### Test LinkedIn Filter

```bash
cd /mnt/d/Quarter_4/Hackathon_0/AI_Employee_Vault
python3 -c "
from Watchers.linkedin_watcher import LinkedInWatcher
from pathlib import Path

watcher = LinkedInWatcher(Path('notes/Inbox'), Path('Logs'))
print(f'Is TechCorp Inc. a client? {watcher.is_client(\"TechCorp Inc.\")}')
print(f'Is Random Person a client? {watcher.is_client(\"Random Person\")}')
"
```

### Test WhatsApp Filter

```bash
python3 -c "
from Watchers.whatsapp_watcher import WhatsAppTaskCreator
from pathlib import Path

creator = WhatsAppTaskCreator(Path('notes/Inbox'))
print(f'Is +1234567890 a client? {creator.is_client(\"whatsapp:+1234567890\")}')
print(f'Is +9999999999 a client? {creator.is_client(\"whatsapp:+9999999999\")}')
"
```

### Test Gmail Filter

```bash
python3 -c "
from Watchers.gmail_watcher import GmailWatcher
from pathlib import Path

watcher = GmailWatcher(Path('notes/Inbox'), Path('Logs'))
print(f'Is client@company.com a client? {watcher.is_client(\"client@company.com\")}')
print(f'Is random@gmail.com a client? {watcher.is_client(\"random@gmail.com\")}')
"
```

---

## Updating Client List

1. **Edit** `Config/client_list.env`
2. **Add** new clients to the appropriate list
3. **Save** the file
4. **Restart** the watchers to apply changes

### Example: Add New Client

```env
# Before
LINKEDIN_CLIENTS=TechCorp Inc.,Acme Corporation

# After
LINKEDIN_CLIENTS=TechCorp Inc.,Acme Corporation,New Client LLC
```

---

## Disabling Filter (Development)

For testing without filtering:

```env
CLIENT_FILTER_ENABLED=false
```

**Warning:** This will allow ALL messages to be processed.

---

## Troubleshooting

### Issue: All messages being ignored

**Solution:** Check if client list is empty or filter is misconfigured

```bash
# Check configuration
cat Config/client_list.env
```

### Issue: Client messages not being processed

**Solution:** Verify client name/number/email matches exactly

- LinkedIn: Check sender name matches (case-insensitive)
- WhatsApp: Include country code, check for `whatsapp:` prefix
- Gmail: Check full email or domain format

### Issue: Want to allow all messages temporarily

**Solution:** Set `CLIENT_FILTER_ENABLED=false` in `Config/client_list.env`

---

## Security Notes

- Keep `client_list.env` secure - contains client information
- Do not commit real client data to version control
- Use placeholder data in development environments
- Regularly review and update client lists

---

## Workflow Summary

### Before (Problem)

```
Random LinkedIn Message → Inbox → Needs_Action → Task Created ❌
Random WhatsApp Message → Inbox → Needs_Action → Task Created ❌
Random Email → Inbox → Needs_Action → Task Created ❌
```

### After (Fixed)

```
Client Message → Inbox → Needs_Action → Task Created ✅
Random Message → IGNORED + Logged ⚠️
```

---

## Files Modified

| File | Changes |
|------|---------|
| `Config/client_list.env` | **NEW** - Client configuration |
| `Watchers/linkedin_watcher.py` | Added client filtering |
| `Watchers/whatsapp_watcher.py` | Added client filtering |
| `Watchers/gmail_watcher.py` | Added client filtering |
| `task_executor.py` | Added secondary client check |

---

## Version

- **Added:** 2026-03-25
- **Version:** 1.0
- **Status:** Active
