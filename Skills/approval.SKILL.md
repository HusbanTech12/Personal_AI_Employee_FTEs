# Skill: Approval

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `approval` |
| **Tier** | Silver |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Governance & Control |

---

## Purpose

Manage human approval workflow for sensitive actions before execution. This skill:

1. **Identifies** tasks requiring approval
2. **Moves** tasks to Needs_Approval folder
3. **Generates** approval_request.md with risk assessment
4. **Waits** for human decision (APPROVED: YES/NO)
5. **Routes** approved tasks back for execution
6. **Archives** rejected tasks with reason

---

## Accepted Inputs

| Input Type | Description | Examples |
|------------|-------------|----------|
| **Email Send** | Outbound email requiring approval | Mass email, customer communication |
| **Social Post** | Social media publishing | LinkedIn, Twitter posts |
| **Payment** | Financial transactions | Invoices, transfers, purchases |
| **Database Change** | Schema or data modifications | Migrations, deletes, updates |
| **Production Deploy** | Live environment changes | Releases, deployments |
| **API Key Access** | Credential/token operations | Key generation, secret access |
| **Data Export** | Data extraction operations | Backups, exports, dumps |

**Task Format:**
```markdown
---
title: Send Customer Email
status: needs_action
priority: standard
skill: approval
action_type: email
---

## Details

**To:** customers@example.com
**Subject:** Product Update

## Content

Email body here...
```

---

## Execution Steps

### Step 1: Detect Sensitive Action

```
Read task content
↓
Scan for sensitive keywords
↓
Classify action type
↓
Assess risk level
```

### Step 2: Generate Approval Request

```
Create approval_request.md
↓
Include task summary
↓
Add risk assessment
↓
Provide approval instructions
```

### Step 3: Move to Approval Folder

```
Copy task to Needs_Approval/
↓
Copy approval request beside it
↓
Log the movement
↓
Wait for human decision
```

### Step 4: Monitor for Decision

```
Poll approval files
↓
Detect APPROVED: YES/NO
↓
Extract approver info
↓
Process decision
```

### Step 5: Process Decision

**If Approved:**
```
Move task back to Needs_Action
↓
Add approval metadata
↓
Trigger next skill for execution
```

**If Rejected:**
```
Add rejection note to task
↓
Move to Done folder
↓
Log rejection reason
```

---

## Sensitive Action Detection

### Keyword Mapping

| Action Type | Trigger Keywords |
|-------------|------------------|
| **Email** | `send email`, `skill: email`, `newsletter`, `smtp`, `mailchimp` |
| **Social Post** | `linkedin`, `twitter`, `publish`, `skill: linkedin`, `post to` |
| **Payment** | `payment`, `invoice`, `transfer`, `purchase`, `$`, `USD`, `billing` |
| **Database** | `database`, `sql`, `migrate`, `schema`, `drop`, `delete from` |
| **Deploy** | `deploy`, `production`, `prod`, `live`, `release`, `push` |
| **API Key** | `api key`, `secret`, `credential`, `token`, `password` |
| **Data Export** | `export`, `dump`, `backup`, `extract`, `download data` |

### Risk Levels

| Level | Action Types | Approval Required |
|-------|--------------|-------------------|
| **CRITICAL** | Production deploy, database drop | Senior approval |
| **HIGH** | Payments, API keys, schema changes | Manager approval |
| **MEDIUM** | Email, data export | Team lead approval |
| **LOW** | Social posts | Any approver |

---

## Output Format

### Approval Request Structure

```markdown
---
title: Approval Request: Task Name
original_task: task.md
request_type: email
risk_level: MEDIUM
status: pending_approval
created: YYYY-MM-DD HH:MM:SS
---

# Approval Request

**Action Type:** Email

**Risk Level:** MEDIUM

---

## Task Summary

[Task details extracted from original]

---

## Risk Assessment

| Factor | Assessment |
|--------|------------|
| Action Type | Email |
| Risk Level | MEDIUM |
| Reversible | Yes |
| Impact Scope | External |

---

## Approval Instructions

Add your decision:

```
APPROVED: YES

Approved by: [Name]
Date: [Date]
Notes: [Optional]
```

Or reject:

```
APPROVED: NO

Rejected by: [Name]
Date: [Date]
Reason: [Reason]
```
```

---

## Completion Rules

An approval task is **complete** when:

- [ ] **Decision received** - APPROVED: YES or NO detected
- [ ] **Action taken** - Task moved appropriately
- [ ] **Logged** - Decision recorded in approval_log.md
- [ ] **State updated** - Scheduler state reflects decision

---

## Error Handling

| Error | Handling |
|-------|----------|
| No decision after timeout | Auto-reject, log reason |
| Invalid decision format | Flag for manual review |
| File access error | Retry, then alert |
| Missing original task | Create error record, skip |

---

## Integration with Other Skills

| Scenario | Handoff To | Information Passed |
|----------|------------|-------------------|
| Task approved | Original skill (email, linkedin, etc.) | Task file with approval metadata |
| Task rejected | None | Rejection logged |
| Needs more info | Requester | Info request noted |

---

## Approval Log Format

```markdown
| Timestamp | Request | Decision | Details |
|-----------|---------|----------|---------|
| 2026-02-23 10:00:00 | approval_email.md | APPROVED | John Manager |
| 2026-02-23 11:00:00 | approval_payment.md | REJECTED | Budget exceeded |
```

---

## Examples

### Example 1: Email Approval

**Input Task:**
```markdown
---
title: Send Newsletter
skill: email
to: customers@example.com
---

Send monthly newsletter to all customers.
```

**Approval Request Generated:**
```markdown
---
title: Approval Request: Send Newsletter
request_type: email
risk_level: MEDIUM
---

## Decision

APPROVED: YES

Approved by: Sarah Manager
Date: 2026-02-23
Notes: Approved for sending
```

**Result:** Task moved back to Needs_Action for email_agent execution.

### Example 2: Payment Rejected

**Input Task:**
```markdown
---
title: Vendor Payment
skill: payment
amount: $5000
---

Pay vendor invoice #12345.
```

**Result:** Rejected → Moved to Done with reason.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Approval not detected | Check APPROVED: format exactly |
| Task stuck in approval | Check file permissions |
| Multiple decisions | Use latest decision timestamp |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-23 | Initial implementation |
