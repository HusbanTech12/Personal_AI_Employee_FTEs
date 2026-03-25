# Official Accounts Only - Configuration Guide

## ✅ IMPLEMENTED: Official Accounts Filtering

Your AI Employee system now **ONLY** processes messages from official accounts you define in `.env`.

**All random/demo notifications are DISABLED.**

---

## Configuration in `.env`

Edit these settings in your `.env` file:

```env
# =============================================================================
# OFFICIAL ACCOUNTS - ONLY THESE SENDERS ARE ACCEPTED
# =============================================================================

# LinkedIn Official Accounts (sender names/company names)
# Set to "NONE" to disable all LinkedIn messages
LINKEDIN_OFFICIAL_ACCOUNTS=Husban Tech

# WhatsApp Official Numbers (with country code)
# Set to "NONE" to disable all WhatsApp messages
WHATSAPP_OFFICIAL_NUMBERS=+923100118238

# Gmail Official Addresses (email or domain)
# Set to "NONE" to disable all Gmail messages
GMAIL_OFFICIAL_ACCOUNTS=husbantech08@gmail.com

# Instagram Official Accounts (usernames)
INSTAGRAM_OFFICIAL_ACCOUNTS=NONE

# Facebook Official Accounts (page names)
FACEBOOK_OFFICIAL_ACCOUNTS=NONE

# =============================================================================
# FILTER SETTINGS
# =============================================================================
# Enable official accounts filtering (MUST be true for production)
OFFICIAL_ACCOUNTS_FILTER_ENABLED=true

# Log ignored non-official messages
LOG_IGNORED_MESSAGES=true

# Reject mode: true = reject completely, false = allow but flag
REJECT_NON_OFFICIAL=true
```

---

## How It Works

### Filter Flow

```
Message Received (Any Source)
        ↓
┌─────────────────────────────┐
│  OFFICIAL ACCOUNTS CHECK    │
│  - LinkedIn: "Husban Tech"  │
│  - WhatsApp: +923100118238  │
│  - Gmail: husbantech08@...  │
└─────────────┬───────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
  YES                 NO
    │                   │
    ↓                   ↓
┌─────────┐      ┌──────────────┐
│PROCESS  │      │ IGNORE +     │
│TASK     │      │ LOG          │
│         │      │              │
│→ Inbox  │      │ ✗ REJECTED   │
│→ Execute│      │ Non-official │
│→ Done   │      │ sender: X    │
└─────────┘      └──────────────┘
```

---

## What Gets Blocked

### ❌ BLOCKED (Examples)

| Sender | Source | Reason |
|--------|--------|--------|
| Michael Chen | LinkedIn | Not in official accounts |
| Sarah Johnson | LinkedIn | Not in official accounts |
| Jennifer Lee | LinkedIn | Not in official accounts |
| Recruiter Pro | LinkedIn | Not in official accounts |
| +1234567890 | WhatsApp | Not in official numbers |
| random@gmail.com | Gmail | Not in official accounts |
| Demo/Test users | Any | Demo mode DISABLED |

### ✅ ALLOWED (Examples)

| Sender | Source | Reason |
|--------|--------|--------|
| Husban Tech | LinkedIn | In LINKEDIN_OFFICIAL_ACCOUNTS |
| +923100118238 | WhatsApp | In WHATSAPP_OFFICIAL_NUMBERS |
| husbantech08@gmail.com | Gmail | In GMAIL_OFFICIAL_ACCOUNTS |

---

## Log Output

### Non-Official Message (IGNORED)

```
2026-03-25 23:41:22 - INFO - TASK DETECTED: linkedin_message_sarah_johnson.md
2026-03-25 23:41:22 - INFO - [OFFICIAL_FILTER] ⚠️  IGNORED non-official LinkedIn: sarah johnson
2026-03-25 23:41:22 - INFO - [OFFICIAL_FILTER]   Official: ['husban tech']
2026-03-25 23:41:22 - INFO - [OFFICIAL_FILTER] ✗ REJECTED non-official account task: linkedin_message_sarah_johnson.md
```

### Official Message (PROCESSED)

```
2026-03-25 23:41:22 - INFO - TASK DETECTED: linkedin_message_husban_tech.md
2026-03-25 23:41:22 - INFO - [OFFICIAL_FILTER] ✓ Official account verified: husban tech
2026-03-25 23:41:22 - INFO - STEP 1/7: Moving to In_Progress/task_executor/
...
2026-03-25 23:41:22 - INFO - EXECUTION COMPLETED
```

---

## Demo Mode - DISABLED

All demo/random notification generation is now **DISABLED**:

| Watcher | Demo Mode |
|---------|-----------|
| LinkedIn | ❌ DISABLED |
| WhatsApp | ❌ DISABLED |
| Gmail | ❌ DISABLED |

**No more random messages from:**
- Sarah Johnson
- Michael Chen
- Jennifer Lee
- Recruiter Pro
- TechCorp Inc.
- Random numbers

---

## Updating Official Accounts

### Add New Official Account

Edit `.env`:

```env
# Before
LINKEDIN_OFFICIAL_ACCOUNTS=Husban Tech

# After - Add more accounts (comma-separated)
LINKEDIN_OFFICIAL_ACCOUNTS=Husban Tech,Your Company Name,Partner Company
```

### Disable a Channel Completely

```env
# Disable all LinkedIn messages
LINKEDIN_OFFICIAL_ACCOUNTS=NONE

# Disable all WhatsApp messages
WHATSAPP_OFFICIAL_NUMBERS=NONE

# Disable all Gmail messages
GMAIL_OFFICIAL_ACCOUNTS=NONE
```

### Allow Domain-Wide (Gmail)

```env
# Allow all emails from your domain
GMAIL_OFFICIAL_ACCOUNTS=@husbantech.com,ceo@husbantech.com
```

---

## Testing

### Test Official Accounts Filter

```bash
cd /mnt/d/Quarter_4/Hackathon_0/AI_Employee_Vault
python3 task_executor.py
```

**Expected Output:**
```
OFFICIAL ACCOUNTS FILTER:
  Status: ENABLED
  LinkedIn: ['husban tech']
  WhatsApp: ['+923100118238']
  Gmail: ['husbantech08@gmail.com']

⚠️  ONLY messages from official accounts will be processed.
⚠️  All other messages will be IGNORED and logged.
```

### Test with Official Account

Create a test task from an official account:

```bash
cat > notes/Needs_Action/test_official_linkedin.md << 'EOF'
---
title: LinkedIn: Message from Husban Tech
status: needs_action
priority: high
created: 2026-03-25 23:45:00
skill: task_processor
source: LinkedIn
sender: Husban Tech
notification_type: message
---

# Test Official Account

**From:** Husban Tech
**Content:** This is a test message from an official account.
EOF
```

This task **WILL** be processed.

### Test with Non-Official Account

```bash
cat > notes/Needs_Action/test_random_linkedin.md << 'EOF'
---
title: LinkedIn: Message from Random Person
status: needs_action
priority: high
created: 2026-03-25 23:45:00
skill: task_processor
source: LinkedIn
sender: Random Person
notification_type: message
---

# Test Non-Official Account

**From:** Random Person
**Content:** This is a test message from a random person.
EOF
```

This task **WILL NOT** be processed.

---

## Troubleshooting

### Issue: All messages being rejected

**Solution:** Check official accounts configuration

```bash
# Check .env settings
cat .env | grep OFFICIAL_ACCOUNTS
```

Ensure at least one official account is configured.

### Issue: Want to allow all temporarily (testing)

**Solution:** Disable filter temporarily

```env
OFFICIAL_ACCOUNTS_FILTER_ENABLED=false
```

**Warning:** This allows ALL messages. Re-enable after testing.

### Issue: Official account still rejected

**Solution:** Check exact match

- LinkedIn: Sender name must match (case-insensitive)
- WhatsApp: Include full number with country code
- Gmail: Check full email or use domain match (@domain.com)

---

## Files Modified

| File | Change |
|------|--------|
| `.env` | Added official accounts configuration |
| `Watchers/linkedin_watcher.py` | Official accounts filter + demo disabled |
| `Watchers/whatsapp_watcher.py` | Official accounts filter + demo disabled |
| `Watchers/gmail_watcher.py` | Official accounts filter + demo disabled |
| `task_executor.py` | Official accounts filter (primary) |

---

## Summary

| Feature | Status |
|---------|--------|
| Official Accounts Filter | ✅ ENABLED |
| Demo Mode | ❌ DISABLED |
| Random Notifications | ❌ BLOCKED |
| Non-Official Messages | ❌ REJECTED |
| Logging | ✅ ACTIVE |

**ONLY your official accounts will generate tasks now.**

---

## Version

- **Updated:** 2026-03-25
- **Version:** 3.0 (Official Accounts Only)
- **Status:** ✅ Production Ready
