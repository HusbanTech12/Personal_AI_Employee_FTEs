# Cloud Runtime Architecture - PLATINUM Tier

**Version:** PLATINUM  
**Created:** 2026-03-02  
**Updated:** 2026-03-02 (Work-Zone Specialization + Delegation)  
**Tier:** Cloud-Enabled Always-On Processing

---

## Executive Summary

The PLATINUM Tier introduces **Cloud Runtime Architecture** - an always-on processing layer that extends the AI Employee system with continuous cloud-based draft generation, email triage, social media drafting, and accounting action preparation.

### Core Principle

> **Cloud NEVER sends messages directly.**  
> Cloud only creates drafts and writes approval requests for human review.

---

## Work-Zone Specialization

The system enforces strict **Work-Zone Specialization** with clear ownership boundaries:

### Zone Ownership Matrix

| Capability | Cloud Zone | Local Zone | Enforced |
|------------|------------|------------|----------|
| Gmail Reading | ✅ | ❌ | HARD |
| Email Draft Replies | ✅ | ❌ | HARD |
| LinkedIn Post Drafts | ✅ | ❌ | HARD |
| Accounting Draft Invoices | ✅ | ❌ | HARD |
| WhatsApp Sessions | ❌ | ✅ | HARD |
| Payments | ❌ | ✅ | HARD |
| Approvals | ❌ | ✅ | HARD |
| Final Send/Post Actions | ❌ | ✅ | HARD |

### Cloud Zone (CLOUD OWNS)
- **Gmail reading** - Read and triage incoming emails
- **Email draft replies** - Generate reply drafts
- **LinkedIn post drafts** - Create social media content
- **Accounting draft invoices** - Prepare invoice entries

### Local Zone (LOCAL OWNS)
- **WhatsApp sessions** - Manage WhatsApp connections
- **Payments** - Execute financial transactions
- **Approvals** - Review and approve/reject drafts
- **Final send/post actions** - Execute approved actions

**See:** [ZONE_POLICY.md](ZONE_POLICY.md) for complete policy documentation.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         PLATINUM Tier - Cloud Runtime                           │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │  External APIs  │
                              │  - Email        │
                              │  - Social       │
                              │  - Accounting   │
                              └────────┬────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│  ┌───────────────────────────────────────────────────────────────────────────┐ │
│  │                    Cloud Orchestrator                                     │ │
│  │  (orchestrator_cloud.py)                                                  │ │
│  │                                                                           │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │ │
│  │  │ Email Triage │  │ Social Media │  │ Accounting   │  │ LinkedIn     │ │ │
│  │  │ & Draft      │  │ Draft        │  │ Draft        │  │ Draft        │ │ │
│  │  │ Replies      │  │ Generation   │  │ Actions      │  │ Messages     │ │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │ │
│  └─────────┼─────────────────┼─────────────────┼─────────────────┼─────────┘ │
│            │                 │                 │                 │            │
│            └─────────────────┴────────┬────────┴─────────────────┘            │
│                                       │                                       │
│                                       ▼                                       │
│                            ┌───────────────────┐                              │
│                            │  Draft Generator  │                              │
│                            │  (Creates drafts  │                              │
│                            │   only - no send) │                              │
│                            └─────────┬─────────┘                              │
│                                      │                                        │
│                                      ▼                                        │
│                            ┌───────────────────┐                              │
│                            │  Approval Request │                              │
│                            │  Manager          │                              │
│                            │  (Writes requests │                              │
│                            │   for review)     │                              │
│                            └─────────┬─────────┘                              │
└──────────────────────────────────────┼────────────────────────────────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
         ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
         │  /Drafts/       │ │ /Approval_      │ │  Cloud Runtime  │
         │  (Draft files)  │ │ Requests/       │ │  State & Logs   │
         │                 │ │ (Review queue)  │ │                 │
         └─────────────────┘ └─────────────────┘ └─────────────────┘
                    │                  │
                    └────────┬─────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  Sync Manager       │
                  │  (sync_manager.py)  │
                  │  - Data consistency │
                  │  - Conflict detect  │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  Health Monitor     │
                  │  (health_monitor.py)│
                  │  - Status tracking  │
                  │  - Alerting         │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  Local AI Employee  │
                  │  (Gold Tier System) │
                  └─────────────────────┘
```

---

## Component Details

### 1. Cloud Orchestrator (`orchestrator_cloud.py`)

**Purpose:** Central coordination engine for all cloud-based draft generation.

**Responsibilities:**
- Receive tasks from external sources (email, social APIs, accounting systems)
- Route tasks to appropriate draft generators
- Create approval requests for all generated drafts
- Manage worker threads for parallel processing
- Track processing statistics

**Draft Types Supported:**
| Type | Description | Approval Required |
|------|-------------|-------------------|
| `EMAIL_REPLY` | Email triage and reply drafts | Yes |
| `SOCIAL_MEDIA_POST` | Social media content drafts | Yes |
| `ACCOUNTING_ACTION` | Accounting entry drafts | Yes |
| `LINKEDIN_MESSAGE` | LinkedIn outreach drafts | Yes |

**Key Classes:**
```
CloudOrchestrator
├── ZonePolicyValidator      # Zone enforcement (HARD)
├── DraftGenerator
│   ├── generate_email_reply()
│   ├── generate_social_media_post()
│   ├── generate_accounting_action()
│   └── generate_linkedin_message()
└── ApprovalRequestManager
    └── create_approval_request()
```

**Zone Enforcement:**
- `ZonePolicyValidator` initialized with HARD enforcement
- All actions validated before execution
- Violations logged and blocked immediately
- Statistics tracked: `zone_violations_blocked`

**Cloud Rule Enforcement:**
- All outputs are drafts only
- Every draft requires an approval request
- No direct API calls to send/publish endpoints
- Zone violations raise `ZoneViolationError`

---

### 2. Health Monitor (`health_monitor.py`)

**Purpose:** Continuous monitoring of cloud runtime health and performance.

**Responsibilities:**
- Monitor orchestrator process status
- Track draft generation rates
- Monitor approval request queue depth
- Check storage utilization
- Generate alerts for anomalies
- Produce health reports

**Health Status Levels:**
| Status | Condition | Action |
|--------|-----------|--------|
| `HEALTHY` | All components normal | Continue monitoring |
| `WARNING` | Elevated metrics | Log and notify |
| `CRITICAL` | Component failure | Alert immediately |

**Monitored Components:**
```
ComponentType
├── ORCHESTRATOR - Process running, queue depth
├── DRAFT_GENERATOR - Generation rate, total drafts
├── APPROVAL_MANAGER - Pending approvals count
└── STORAGE - Disk usage percentage
```

**Alert Thresholds:**
- Draft generation > 100/hour → WARNING
- Pending approvals > 50 → WARNING
- Disk usage > 75% → WARNING
- Disk usage > 90% → CRITICAL

---

### 4. Zone Policy Validator (`zone_policy_validator.py`)

**Purpose:** Enforce work-zone specialization at runtime.

**Responsibilities:**
- Validate actions against zone policy
- Block prohibited cross-zone actions
- Log zone violations
- Generate violation reports
- Enforce directory access control

**Zone Policy:**
```
CLOUD ZONE (orchestrator_cloud.py):
  ✅ CAN: generate_email_reply, generate_social_media_post,
          generate_accounting_action, generate_linkedin_message,
          create_approval_request, read_gmail, triage_email
  ❌ CANNOT: send_email, publish_post, execute_payment,
             approve_action, access_whatsapp

LOCAL ZONE (local agents):
  ✅ CAN: approve_action, send_email, publish_post,
          execute_payment, access_whatsapp
  ❌ CANNOT: bypass_approval, execute_without_approval,
             read_gmail_direct
```

**Enforcement Levels:**
| Level | Behavior |
|-------|----------|
| `HARD` | Block action, raise exception, log violation |
| `SOFT` | Log warning, allow with audit |
| `DISABLED` | No enforcement |

**Violation Handling:**
- Violations saved to `/CloudRuntime/violations/`
- Each violation gets unique ID
- Markdown report generated per violation
- Summary reports available on demand

---

### 5. Sync Manager (`sync_manager.py`)

**Purpose:** Maintain data consistency between cloud runtime and local systems.

**Responsibilities:**
- Sync draft files between cloud and local storage
- Sync approval request status
- Detect and handle conflicts
- Archive approved items to Done folder
- Maintain sync state across restarts

**Sync Directions:**
| Direction | Use Case |
|-----------|----------|
| `CLOUD_TO_LOCAL` | Download new drafts |
| `LOCAL_TO_CLOUD` | Upload local changes |
| `BIDIRECTIONAL` | Full synchronization |

**Conflict Resolution:**
```
Conflict Detected
       │
       ▼
┌──────────────────┐
│ Backup both      │
│ versions         │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Create conflict  │
│ resolution file  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Wait for manual  │
│ resolution       │
└──────────────────┘
```

**Sync State Persistence:**
- Entity hashes tracked
- Last sync timestamp saved
- Conflict count maintained
- Survives system restarts

---

### 6. Delegation Manager (`delegation_manager.py`)

**Purpose:** Implement Synced Vault Delegation System with claim-by-move ownership.

**Responsibilities:**
- Manage task claims via file movement
- Track agent ownership of tasks
- Write updates to isolated /Updates/ folder
- Enforce single-writer rule for Dashboard

**Folder Structure:**
```
notes/
├── Needs_Action/<domain>/     # Unclaimed tasks by domain
├── Plans/<domain>/            # Task plans by domain
├── Pending_Approval/<domain>/ # Tasks awaiting approval
├── In_Progress/<agent>/       # Tasks claimed by agents
├── Updates/                   # Cloud-written status updates
└── Done/                      # Completed tasks
```

**Delegation Rules:**
| Rule | Description |
|------|-------------|
| 1. Claim-by-move | Agent moves file: Needs_Action → In_Progress/<agent> |
| 2. Ownership | Other agents ignore claimed tasks |
| 3. Cloud writes | Cloud writes updates only to /Updates/ |
| 4. Single writer | Local merges updates into Dashboard.md |

**Claim Registry:**
- Stored in `/CloudRuntime/delegation_state/claim_registry.json`
- Tracks: task_id, claimed_by, claimed_at, source_domain, status
- Prevents race conditions in task claiming
- Supports claim release on completion

**Update Flow:**
```
Cloud Agent                    Local Merger
    │                              │
    │  Write to /Updates/          │
    ├─────────────────────────────>│
    │  update_task123.md           │
    │                              │ Parse update
    │                              │ Merge into Dashboard
    │                              │ Move to processed/
    │                              │
```

**Key Classes:**
```
DelegationManager
├── ClaimRegistry
│   ├── register_claim()
│   ├── release_claim()
│   ├── is_claimed()
│   └── get_claims_by_agent()
├── claim_task()           # Move + register
├── release_task()         # Move + release
├── write_update()         # Write to /Updates/
└── get_dashboard_updates() # Get pending updates
```

---

## Data Flow

### Draft Generation Flow

```
1. External Trigger (Email/API/Webhook)
         │
         ▼
2. Cloud Orchestrator receives task
         │
         ▼
3. DraftGenerator creates draft
         │
         ▼
4. Draft saved to /Drafts/
         │
         ▼
5. ApprovalRequestManager creates request
         │
         ▼
6. Request saved to /Approval_Requests/
         │
         ▼
7. Human reviews and responds
         │
         ▼
8. If APPROVED → Move to /Done/
   If REJECTED → Archive with reason
```

### Approval Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Approval Request Format                       │
├─────────────────────────────────────────────────────────────────┤
│ ---                                                             │
│ request_id: approval_001_20260302120000                          │
│ draft_id: email_draft_001_20260302120000                         │
│ priority: normal                                                │
│ status: pending                                                 │
│ created_at: 2026-03-02T12:00:00                                 │
│ ---                                                             │
│                                                                 │
│ # Approval Request                                              │
│                                                                 │
│ ## Suggested Action                                             │
│ Send email reply                                                │
│                                                                 │
│ ## Draft Content                                                │
│ [Draft content here...]                                         │
│                                                                 │
│ ---                                                             │
│ ## Response Required                                            │
│ Please review and respond with: APPROVE or REJECT               │
│                                                                 │
│ Response: [PENDING]                                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
AI_Employee_Vault/
├── CloudRuntime/                    # PLATINUM Tier components
│   ├── orchestrator_cloud.py        # Main orchestration engine
│   ├── health_monitor.py            # Health monitoring
│   ├── sync_manager.py              # Sync management
│   ├── cloud_config.json            # Cloud configuration
│   ├── sync_state/                  # Sync state persistence
│   │   └── sync_state.json
│   ├── health_reports/              # Generated health reports
│   └── sync_conflicts/              # Conflict resolution files
│
├── notes/                           # Obsidian vault
│   ├── Drafts/                      # Generated drafts
│   │   ├── email_draft_*.md
│   │   ├── social_draft_*.md
│   │   ├── acct_draft_*.md
│   │   └── linkedin_draft_*.md
│   │
│   ├── Approval_Requests/           # Pending approvals
│   │   └── approval_*.md
│   │
│   ├── Inbox/                       # Incoming tasks
│   ├── Needs_Action/                # Active processing
│   └── Done/                        # Completed items
│       ├── Drafts/                  # Approved drafts
│       └── Approval_Requests/       # Processed approvals
│
└── Logs/                            # System logs
    ├── cloud_orchestrator_*.log
    ├── cloud_health_*.log
    └── cloud_sync_*.log
```

---

## Startup & Management

### Starting Cloud Runtime

```bash
# Start all cloud components
cd /mnt/d/Quarter_4/Hackathon_0/AI_Employee_Vault

# Option 1: Start individually
python CloudRuntime/orchestrator_cloud.py &
python CloudRuntime/health_monitor.py &
python CloudRuntime/sync_manager.py &

# Option 2: Use startup script (create run_cloud.sh)
./run_cloud.sh
```

### Stopping Cloud Runtime

```bash
# Graceful shutdown
# Press Ctrl+C in each running process

# Or kill all cloud processes
pkill -f orchestrator_cloud.py
pkill -f health_monitor.py
pkill -f sync_manager.py
```

### Checking Status

```bash
# View health report
ls -la CloudRuntime/health_reports/
tail -n 50 CloudRuntime/health_reports/health_report_*.md

# View logs
tail -f Logs/cloud_orchestrator_*.log
tail -f Logs/cloud_health_*.log
tail -f Logs/cloud_sync_*.log

# Check pending approvals
ls -la notes/Approval_Requests/
```

---

## Configuration

### Cloud Config (`cloud_config.json`)

```json
{
  "orchestrator": {
    "num_workers": 3,
    "queue_max_size": 1000
  },
  "health_monitor": {
    "check_interval_seconds": 30,
    "alert_threshold_drafts": 100,
    "alert_threshold_approvals": 50
  },
  "sync_manager": {
    "sync_interval_seconds": 60,
    "enable_conflict_detection": true
  },
  "drafts": {
    "auto_archive_approved": true,
    "keep_rejected_days": 30
  }
}
```

---

## Security & Compliance

### Data Handling
- All drafts stored locally first
- No external API calls without approval
- Approval requests require explicit human response
- Full audit trail in logs

### Access Control
- Drafts readable by system and approver
- Approval requests writable only by approver
- Logs append-only

### Audit Trail
```
Every action logged with:
- Timestamp
- Component
- Action type
- Entity ID
- Result status
```

---

## Monitoring & Alerting

### Health Dashboard

| Metric | Current | Threshold | Status |
|--------|---------|-----------|--------|
| Orchestrator | Running | - | ✅ |
| Draft Rate | 5/hour | 100/hour | ✅ |
| Pending Approvals | 12 | 50 | ✅ |
| Disk Usage | 45% | 75% | ✅ |

### Alert Channels
- Log file entries (all alerts)
- Console output (real-time)
- Health reports (periodic summary)

---

## Failure Modes & Recovery

### Component Failures

| Component | Failure Mode | Recovery |
|-----------|--------------|----------|
| Orchestrator | Process crash | Auto-restart via supervisor |
| Health Monitor | Process crash | Restart, historical data preserved |
| Sync Manager | Process crash | Restart, state recovered from disk |

### Data Recovery
- Sync state persisted to disk
- Drafts backed up on conflict
- Approval requests immutable once created

---

## Performance Characteristics

### Expected Throughput
- Draft generation: ~100/hour per worker
- Approval processing: ~500/hour
- Sync operations: ~1000/hour

### Resource Usage
- Memory: ~200MB per component
- CPU: <5% during idle, <30% during processing
- Disk: Varies by draft volume (~1KB per draft)

---

## Integration Points

### With Gold Tier (Local)
```
Cloud Runtime → Sync Manager → Local Filesystem
     │                              │
     │                              ▼
     │                       Gold Tier Agents
     │                              │
     └──────────────←───────────────┘
           Approval decisions
```

### External Services (Future)
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ Gmail API   │     │ LinkedIn    │     │ QuickBooks  │
│ (Read only) │     │ API (Read)  │     │ API (Read)  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│              Cloud Orchestrator                          │
│         (Draft generation only)                          │
└─────────────────────────────────────────────────────────┘
```

---

## Migration from Gold Tier

### Prerequisites
- Gold Tier system operational
- Python 3.8+ installed
- Required packages: `psutil`

### Steps
1. Create `/Drafts/` and `/Approval_Requests/` folders
2. Copy CloudRuntime components
3. Configure `cloud_config.json`
4. Start orchestrator first
5. Start health monitor
6. Start sync manager
7. Verify health status

### Rollback
- Stop cloud components
- Resume Gold Tier operations
- No data loss (drafts preserved)

---

## Future Enhancements

### Planned Features
- [ ] Multi-cloud support (AWS, GCP, Azure)
- [ ] Distributed orchestrator cluster
- [ ] Real-time dashboard (WebSocket)
- [ ] Mobile approval notifications
- [ ] AI-powered draft quality scoring
- [ ] Approval delegation workflows

### Experimental
- [ ] Voice-based approval
- [ ] Slack/Teams integration
- [ ] Automated A/B testing for drafts

---

## Appendix A: API Reference

### CloudOrchestrator Methods
```python
orchestrator.start(num_workers: int) -> None
orchestrator.stop() -> None
orchestrator.submit_task(task: CloudTask) -> None
orchestrator.get_stats() -> Dict[str, int]
```

### CloudHealthMonitor Methods
```python
monitor.start() -> None
monitor.stop() -> None
monitor.check_health() -> SystemHealth
monitor.get_health_summary() -> Dict[str, Any]
monitor.generate_report() -> Path
```

### CloudSyncManager Methods
```python
manager.start() -> None
manager.stop() -> None
manager.get_sync_status() -> Dict[str, Any]
manager.queue_sync_operation(entity, direction) -> str
```

---

## Appendix B: File Formats

### Draft File Format
```markdown
---
draft_id: email_draft_001_20260302120000
task_id: task_12345
draft_type: email_reply
status: generated
created_at: 2026-03-02T12:00:00
---

--- DRAFT EMAIL REPLY ---

[Draft content...]

--- END DRAFT ---

--- METADATA ---
{
  "original_email": "...",
  "subject": "Re: Meeting",
  "recipient": "user@example.com"
}
```

### Approval Request Format
```markdown
---
request_id: approval_001_20260302120000
draft_id: email_draft_001_20260302120000
priority: normal
status: pending
created_at: 2026-03-02T12:00:00
---

# Approval Request

## Suggested Action
Send email reply

## Draft Content
[Draft content...]

---
## Response Required
Response: [PENDING]
```

---

**Document Version:** 1.0  
**Last Updated:** 2026-03-02  
**Maintained By:** AI Employee System
