# Gmail Autonomous Agent Skill

## Purpose

Autonomous email processing agent that monitors, analyzes, and responds to Gmail communications with professional tone and safety controls.

---

## Capabilities

### 1. Inbox Monitoring

- Monitor `Inbox` folder created by `gmail_watcher`
- Poll for new email tasks automatically
- Track processed emails to prevent duplicates
- Support real-time webhook notifications

### 2. Email Analysis

- Read new email tasks automatically
- Extract key information:
  - Sender identity and reputation
  - Subject and body content
  - Attachments and links
  - Thread context and history
- Summarize email content in 2-3 sentences

### 3. Intent Detection

Detect email intent using classification:

| Intent | Triggers | Response Type |
|--------|----------|---------------|
| `INQUIRY` | Questions, information requests | Informative reply |
| `ACTION_REQUIRED` | Requests, tasks, deadlines | Action confirmation |
| `MEETING` | Scheduling, calendar invites | Availability response |
| `FOLLOW_UP` | Reminder, checking status | Status update |
| `SPAM_PROMO` | Promotional, unsolicited | Archive/no reply |

### 4. Auto Reply Generation

- Generate replies using professional tone
- Adapt style based on sender relationship:
  - **Formal**: New contacts, business partners
  - **Professional**: Existing clients, vendors
  - **Casual**: Internal team, known contacts
- Include appropriate signatures and disclaimers
- Attach relevant documents when needed

### 5. Approval Request System

Create approval requests for sensitive emails:
- Finance-related content (invoices, payments, pricing)
- Legal matters (contracts, agreements, compliance)
- HR topics (hiring, termination, compensation)
- Strategic decisions (partnerships, investments)

### 6. Email Delivery

- Send replies using MCP Email Server
- Support HTML and plain text formats
- Handle attachments securely
- Track delivery status

---

## Workflow

```
┌─────────────┐
│   Email     │
│   Received  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Analysis  │ ← Summarize, classify, extract entities
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Plan     │ ← Create action plan, check approval needs
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Action    │ ← Reply, forward, archive, escalate
└──────┬──────┘
       │
       ▼
┌─────────────┐
│    Log      │ ← Record all actions and outcomes
└─────────────┘
```

---

## Safety Rules

### Finance Email Detection

**Require approval for emails containing:**

```
- Invoice, payment, wire transfer
- Bank account, routing number
- Credit card, billing, charge
- Budget, cost, price negotiation
- Refund, reimbursement, expense
- Contract value, financial commitment
```

**Action**: Create `Plans/APPROVAL_<timestamp>.md` and halt execution until approved.

### Unknown Sender Handling

**Flag senders as unknown when:**

- Domain not in trusted domains list
- No previous interaction history
- Sender address suspicious/spam-like
- Email fails SPF/DKIM verification

**Action**: Add `[UNVERIFIED SENDER]` notice to analysis, require confirmation before reply.

### Sensitive Content Detection

**Red flags requiring escalation:**

- Legal threats or disputes
- Confidentiality requests
- Data access requests (GDPR, CCPA)
- Security vulnerability reports
- Executive-level communications

---

## Input Schema

```json
{
  "email_id": "string",
  "thread_id": "string",
  "label_ids": ["string"],
  "from": {
    "name": "string",
    "email": "string",
    "domain": "string"
  },
  "to": [
    {
      "name": "string",
      "email": "string"
    }
  ],
  "cc": [],
  "subject": "string",
  "body": {
    "plain": "string",
    "html": "string"
  },
  "attachments": [
    {
      "filename": "string",
      "mime_type": "string",
      "size": "integer"
    }
  ],
  "timestamp": "ISO8601",
  "is_read": "boolean",
  "priority": "normal|important|urgent"
}
```

---

## Output Schema

```json
{
  "task_id": "string",
  "email_id": "string",
  "summary": "string",
  "classification": {
    "intent": "INQUIRY|ACTION_REQUIRED|MEETING|FOLLOW_UP|SPAM_PROMO",
    "confidence": "float",
    "requires_approval": "boolean",
    "approval_reason": "string|null"
  },
  "sender_status": {
    "is_known": "boolean",
    "is_trusted": "boolean",
    "flagged": "boolean",
    "flag_reason": "string|null"
  },
  "action": {
    "type": "reply|forward|archive|escalate|await_approval",
    "reply_content": "string|null",
    "reply_format": "html|plain",
    "attachments": ["string"],
    "status": "pending|completed|blocked|approved"
  },
  "plan_path": "Plans/PLAN_*.md|null",
  "reply_path": "Vault/Email/Replies/*.md|null",
  "logged": "boolean"
}
```

---

## Plan Template

```markdown
# Email Action Plan: <PLAN_ID>

## Generated
<Timestamp>

## Email Summary
- **From**: <sender_name> (<sender_email>)
- **Subject**: <subject>
- **Received**: <timestamp>
- **Summary**: <2-3 sentence summary>

## Classification
- **Intent**: <intent>
- **Confidence**: <confidence>%
- **Sender Status**: <known|unknown|trusted|flagged>

## Safety Check
- **Finance Related**: <yes|no>
- **Legal Related**: <yes|no>
- **Approval Required**: <yes|no>
- **Reason**: <if approval required>

## Proposed Action
- **Type**: <reply|forward|archive|escalate>
- **Response Draft**:
  <draft reply content>

## Attachments
- <list attachments or "none">

## Routing
- **Send Via**: MCP Email Server
- **Priority**: <priority>

---
*Auto-generated by Gmail Autonomous Agent*
```

---

## Approval Request Template

```markdown
# Approval Request: <APPROVAL_ID>

## Generated
<Timestamp>

## Email Details
- **From**: <sender_email>
- **Subject**: <subject>
- **Intent**: <intent>

## Why Approval Required
<reason for approval request>

## Proposed Response
<draft response>

## Risk Assessment
- **Financial Impact**: <low|medium|high>
- **Legal Implications**: <none|low|medium|high>
- **Recommendation**: <approve|modify|reject>

## Status
- [ ] Pending Approval
- [ ] Approved
- [ ] Rejected
- [ ] Modified

## Approved By
- **Name**: _______________
- **Date**: _______________
- **Notes**: _______________

---
*Requires human approval before execution*
```

---

## Reply Storage Format

All replies stored in `Vault/Email/Replies/`:

```markdown
# Email Reply: <REPLY_ID>

## Original Email
- **From**: <sender_email>
- **Subject**: <subject>
- **Date**: <original_date>

## Reply Sent
- **To**: <recipient_email>
- **Date**: <reply_date>
- **Format**: <html|plain>

## Content
<reply content>

## Attachments
<list of attachments sent>

## Delivery Status
- **Status**: <sent|delivered|failed>
- **Message ID**: <email_message_id>

---
*Stored by Gmail Autonomous Agent*
```

---

## Audit Log Format

All actions logged to `Logs/email_agent.log`:

```
[TIMESTAMP] | EMAIL_ID | FROM | INTENT | ACTION | STATUS | APPROVAL | NOTES
```

Example:
```
[2026-02-28T11:30:00Z] | msg_abc123 | john @example.com | INQUIRY | reply | sent | none | Auto-replied
[2026-02-28T11:32:15Z] | msg_def456 | billing @vendor.com | ACTION_REQUIRED | await_approval | blocked | finance | Invoice received
[2026-02-28T11:35:22Z] | msg_ghi789 | unknown @random.net | SPAM_PROMO | archive | completed | none | Unknown sender flagged
```

---

## Professional Tone Guidelines

### Formal Tone (New Contacts)
```
Dear [Name],

Thank you for reaching out. [Response content].

Please do not hesitate to contact us should you require further assistance.

Best regards,
[Signature]
```

### Professional Tone (Existing Contacts)
```
Hi [Name],

Thanks for your email. [Response content].

Let me know if you have any questions.

Best,
[Signature]
```

### Casual Tone (Internal Team)
```
Hey [Name],

[Response content].

Thanks!
[Name]
```

---

## Integration Points

### Required Connections

| System | Purpose | Method |
|--------|---------|--------|
| gmail_watcher | Email ingestion | File system watch on Inbox |
| MCP Email Server | Send replies | MCP protocol |
| Social Intelligence | Intent classification | Skill API call |
| Plan Executor | Action execution | Plan file generation |

### File Locations

```
Skills/gmail_autonomous_agent.SKILL.md  ← This file
Inbox/                                   ← gmail_watcher output
Vault/Email/Replies/                     ← Sent replies storage
Plans/PLAN_*.md                          ← Action plans
Plans/APPROVAL_*.md                      ← Approval requests
Logs/email_agent.log                     ← Agent audit trail
```

---

## Error Handling

| Error Type | Response |
|------------|----------|
| Gmail API failure | Retry with exponential backoff |
| MCP Email Server unavailable | Queue reply, retry in 5 min |
| Classification low confidence | Flag for human review |
| Attachment processing error | Skip attachment, log warning |
| Approval timeout (>24h) | Escalate to admin |

---

## Performance Metrics

- **Email Processing Time**: Target <10 seconds per email
- **Classification Accuracy**: Target ≥92%
- **Auto-Reply Rate**: Target ≥70% (non-sensitive emails)
- **False Positive (Approval)**: Target <5%
- **Delivery Success Rate**: Target ≥99%

---

## Trusted Domains Configuration

Maintain list in `config/trusted_domains.txt`:

```
# Trusted domains for auto-reply
company.com
partner-domain.com
vendor.net
```

---

## Configuration

```json
{
  "polling_interval_seconds": 30,
  "max_retries": 3,
  "approval_timeout_hours": 24,
  "auto_reply_enabled": true,
  "unknown_sender_flag": true,
  "finance_approval_required": true,
  "reply_storage_path": "Vault/Email/Replies",
  "log_path": "Logs/email_agent.log"
}
```

---

*Skill Version: 1.0.0*  
*Last Updated: 2026-02-28*  
*Tier: GOLD*
