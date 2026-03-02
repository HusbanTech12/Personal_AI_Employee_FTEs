# Work-Zone Specialization Policy

**Version:** PLATINUM  
**Effective:** 2026-03-02  
**Enforcement:** MANDATORY

---

## Overview

The AI Employee system enforces strict **Work-Zone Specialization** to ensure proper separation of concerns between Cloud and Local execution environments. This policy defines ownership rules and prevents unauthorized cross-zone actions.

---

## Zone Ownership Matrix

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ZONE OWNERSHIP MATRIX                              │
├─────────────────────────────────────────────────────────────────────────────┤
│  Capability                    │  Cloud Zone  │  Local Zone  │  Enforced   │
├─────────────────────────────────────────────────────────────────────────────┤
│  Gmail Reading                 │      ✅       │      ❌       │    HARD     │
│  Email Draft Replies           │      ✅       │      ❌       │    HARD     │
│  LinkedIn Post Drafts          │      ✅       │      ❌       │    HARD     │
│  Accounting Draft Invoices     │      ✅       │      ❌       │    HARD     │
│  WhatsApp Sessions             │      ❌       │      ✅       │    HARD     │
│  Payments                      │      ❌       │      ✅       │    HARD     │
│  Approvals                     │      ❌       │      ✅       │    HARD     │
│  Final Send/Post Actions       │      ❌       │      ✅       │    HARD     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Cloud Zone Ownership

### ✅ Cloud-Owned Capabilities

| Capability | Description | Restrictions |
|------------|-------------|--------------|
| **Gmail Reading** | Read and triage incoming emails | Read-only, no send |
| **Email Draft Replies** | Generate reply drafts | Must create approval request |
| **LinkedIn Post Drafts** | Create social media content | Must create approval request |
| **Accounting Draft Invoices** | Prepare invoice entries | Must create approval request |

### ❌ Cloud-Prohibited Actions

```
┌─────────────────────────────────────────────────────────────────┐
│              CLOUD ZONE - NEVER ALLOWED                         │
├─────────────────────────────────────────────────────────────────┤
│  ❌ Send emails directly                                        │
│  ❌ Publish social media posts                                  │
│  ❌ Execute payments                                            │
│  ❌ Access WhatsApp sessions                                    │
│  ❌ Approve any action                                          │
│  ❌ Modify approval requests                                    │
│  ❌ Delete drafts without approval                              │
│  ❌ Access local-only directories                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Local Zone Ownership

### ✅ Local-Owned Capabilities

| Capability | Description | Restrictions |
|------------|-------------|--------------|
| **WhatsApp Sessions** | Manage WhatsApp connections | Cloud cannot access |
| **Payments** | Execute financial transactions | Requires approval first |
| **Approvals** | Review and approve/reject drafts | Human or local agent only |
| **Final Send/Post Actions** | Execute approved actions | Requires valid approval |

### ❌ Local-Prohibited Actions

```
┌─────────────────────────────────────────────────────────────────┐
│              LOCAL ZONE - NEVER ALLOWED                         │
├─────────────────────────────────────────────────────────────────┤
│  ❌ Bypass approval workflow                                    │
│  ❌ Execute without valid approval ID                           │
│  ❌ Modify cloud-generated drafts                               │
│  ❌ Access cloud internal state directly                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Enforcement Mechanisms

### Hard Enforcement (Code-Level)

```python
# Zone Policy Validator
class ZonePolicyValidator:
    """
    Enforces work-zone specialization at runtime.
    Blocks any prohibited cross-zone actions.
    """
    
    CLOUD_PROHIBITED_ACTIONS = {
        'send_email',
        'publish_post',
        'execute_payment',
        'access_whatsapp',
        'approve_action',
        'modify_approval',
        'delete_draft',
    }
    
    LOCAL_PROHIBITED_ACTIONS = {
        'bypass_approval',
        'execute_without_approval',
        'modify_cloud_draft',
    }
    
    def validate_action(self, zone: str, action: str) -> bool:
        """Validate if action is allowed in zone."""
        if zone == 'cloud' and action in self.CLOUD_PROHIBITED_ACTIONS:
            raise ZoneViolationError(
                f"Cloud zone cannot execute: {action}"
            )
        if zone == 'local' and action in self.LOCAL_PROHIBITED_ACTIONS:
            raise ZoneViolationError(
                f"Local zone cannot execute: {action}"
            )
        return True
```

### Directory Access Control

```
┌─────────────────────────────────────────────────────────────────┐
│                    DIRECTORY PERMISSIONS                         │
├─────────────────────────────────────────────────────────────────┤
│  Directory                  │  Cloud  │  Local  │  Approval    │
├─────────────────────────────────────────────────────────────────┤
│  /Drafts/                   │  R/W    │  R      │  R           │
│  /Approval_Requests/        │  W      │  R/W    │  R/W         │
│  /Inbox/                    │  R      │  R/W    │  R           │
│  /Needs_Action/             │  R      │  R/W    │  R           │
│  /Done/                     │  R      │  W      │  R           │
│  /CloudRuntime/             │  R/W    │  R      │  R           │
│  /Watchers/                 │  ❌     │  R/W    │  ❌          │
│  /Config/                   │  R      │  R/W    │  R           │
└─────────────────────────────────────────────────────────────────┘

Legend: R = Read, W = Write, ❌ = No Access
```

---

## Action Flow with Zone Enforcement

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    CROSS-ZONE ACTION FLOW                                    │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │   Email      │
    │   Received   │
    └──────┬───────┘
           │
           ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                    CLOUD ZONE                                 │
    │                                                               │
    │  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐    │
    │  │ Gmail Read  │ ──→ │ Draft Reply │ ──→ │ Create      │    │
    │  │ (Allowed)   │     │ (Allowed)   │     │ Approval    │    │
    │  │             │     │             │     │ Request     │    │
    │  └─────────────┘     └─────────────┘     └──────┬──────┘    │
    │                                                 │            │
    │                                                 ▼            │
    │  ┌─────────────────────────────────────────────────────┐   │
    │  │  🚫 BLOCKED: Send Email (Cloud cannot execute)      │   │
    │  └─────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────┘
                                                   │
                                                   │ Approval Request
                                                   ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                    LOCAL ZONE                                 │
    │                                                               │
    │  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐    │
    │  │ Review      │ ──→ │ Approve/    │ ──→ │ Execute     │    │
    │  │ Draft       │     │ Reject      │     │ Send Email  │    │
    │  │ (Allowed)   │     │ (Allowed)   │     │ (Allowed)   │    │
    │  └─────────────┘     └─────────────┘     └─────────────┘    │
    │                                                               │
    │  ┌─────────────────────────────────────────────────────┐   │
    │  │  🚫 BLOCKED: Read Gmail Directly (Local cannot)     │   │
    │  └─────────────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────────────┘
```

---

## Zone Violation Handling

### Violation Detection

```python
class ZoneViolationError(Exception):
    """Raised when a zone policy violation is detected."""
    
    def __init__(self, message: str, zone: str, action: str):
        super().__init__(message)
        self.zone = zone
        self.action = action
        self.timestamp = datetime.now()
        self.violation_id = f"violation_{uuid.uuid4().hex[:12]}"
```

### Violation Response

| Severity | Response | Logging | Alert |
|----------|----------|---------|-------|
| **Hard Block** | Action rejected | Audit log | Real-time |
| **Soft Warning** | Action logged | Warning log | Summary |
| **Policy Review** | Queue for review | Review queue | Daily |

### Violation Audit Log

```markdown
---
violation_id: violation_a1b2c3d4e5f6
timestamp: 2026-03-02T14:30:00
zone: cloud
attempted_action: send_email
target: user@example.com
status: BLOCKED
enforced_by: ZonePolicyValidator
---

# Zone Policy Violation

## Details
- **Zone:** Cloud
- **Action:** send_email
- **Target:** user@example.com
- **Time:** 2026-03-02 14:30:00

## Enforcement
- **Status:** BLOCKED
- **Reason:** Cloud zone cannot execute send actions
- **Policy:** ZONE_POLICY.md Section 2.2

## Resolution
Action was blocked. Draft created and approval request submitted instead.
```

---

## Policy Enforcement Points

### 1. Orchestrator Level
```python
# In orchestrator_cloud.py
def execute_action(self, action: str, params: dict):
    # ENFORCEMENT POINT 1
    self.zone_validator.validate_action('cloud', action)
    
    # Only allow draft generation
    if action in ALLOWED_CLOUD_ACTIONS:
        return self._generate_draft(action, params)
    else:
        raise ZoneViolationError(
            f"Action not allowed in cloud: {action}"
        )
```

### 2. API Gateway Level
```python
# Middleware for all cloud API calls
@app.before_request
def zone_policy_check():
    action = request.endpoint
    if not zone_validator.is_cloud_allowed(action):
        audit_log.violation('cloud', action)
        return jsonify({
            'error': 'Zone policy violation',
            'action': action,
            'zone': 'cloud'
        }), 403
```

### 3. File System Level
```python
# Directory access control
class ZoneAwareFileSystem:
    def write(self, path: Path, content: str, zone: str):
        if not self._check_write_permission(path, zone):
            raise ZoneViolationError(
                f"Zone {zone} cannot write to {path}"
            )
        # Proceed with write
```

### 4. Approval Gateway
```python
# All approvals must go through local zone
class ApprovalGateway:
    def process_approval(self, request_id: str, decision: str, zone: str):
        if zone != 'local':
            raise ZoneViolationError(
                f"Approvals can only be processed in local zone"
            )
        # Process approval
```

---

## Configuration

### Zone Policy Config (`zone_config.json`)

```json
{
  "enforcement_mode": "strict",
  "zones": {
    "cloud": {
      "allowed_actions": [
        "read_email",
        "generate_draft",
        "create_approval_request",
        "read_social_feed",
        "read_accounting_data"
      ],
      "prohibited_actions": [
        "send_email",
        "publish_post",
        "execute_payment",
        "approve_action",
        "access_whatsapp"
      ],
      "directory_access": {
        "/Drafts/": ["read", "write"],
        "/Approval_Requests/": ["write"],
        "/Inbox/": ["read"],
        "/Watchers/": [],
        "/Config/": ["read"]
      }
    },
    "local": {
      "allowed_actions": [
        "approve_action",
        "reject_action",
        "send_email",
        "publish_post",
        "execute_payment",
        "access_whatsapp",
        "manage_sessions"
      ],
      "prohibited_actions": [
        "bypass_approval",
        "execute_without_approval"
      ],
      "directory_access": {
        "/Drafts/": ["read"],
        "/Approval_Requests/": ["read", "write"],
        "/Inbox/": ["read", "write"],
        "/Watchers/": ["read", "write"],
        "/Config/": ["read", "write"]
      }
    }
  },
  "violation_handling": {
    "log_all_violations": true,
    "alert_on_violation": true,
    "audit_retention_days": 90
  }
}
```

---

## Compliance Checklist

```
┌─────────────────────────────────────────────────────────────────┐
│              ZONE POLICY COMPLIANCE CHECKLIST                    │
├─────────────────────────────────────────────────────────────────┤
│  ☐  Cloud cannot send emails directly                           │
│  ☐  Cloud cannot publish social posts directly                  │
│  ☐  Cloud cannot execute payments                               │
│  ☐  Cloud cannot access WhatsApp                                │
│  ☐  Cloud cannot approve actions                                │
│  ☐  Local owns all approval decisions                           │
│  ☐  Local owns all final send actions                           │
│  ☐  Local owns WhatsApp sessions                                │
│  ☐  Zone validator blocks prohibited actions                    │
│  ☐  All violations logged to audit                              │
│  ☐  Directory permissions enforced                              │
│  ☐  Approval gateway validates zone                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Testing Zone Enforcement

### Unit Tests

```python
class TestZonePolicy:
    
    def test_cloud_cannot_send_email(self):
        validator = ZonePolicyValidator()
        with pytest.raises(ZoneViolationError):
            validator.validate_action('cloud', 'send_email')
    
    def test_cloud_can_create_draft(self):
        validator = ZonePolicyValidator()
        assert validator.validate_action('cloud', 'generate_draft')
    
    def test_local_can_approve(self):
        validator = ZonePolicyValidator()
        assert validator.validate_action('local', 'approve_action')
    
    def test_local_cannot_bypass_approval(self):
        validator = ZonePolicyValidator()
        with pytest.raises(ZoneViolationError):
            validator.validate_action('local', 'bypass_approval')
```

### Integration Tests

```python
class TestZoneEnforcement:
    
    def test_orchestrator_blocks_send(self):
        orchestrator = CloudOrchestrator()
        with pytest.raises(ZoneViolationError):
            orchestrator.execute_action('send_email', {...})
    
    def test_approval_gateway_blocks_cloud(self):
        gateway = ApprovalGateway()
        with pytest.raises(ZoneViolationError):
            gateway.process_approval('req_123', 'APPROVE', zone='cloud')
```

---

## Audit & Reporting

### Daily Zone Policy Report

```markdown
# Zone Policy Audit Report
**Date:** 2026-03-02

## Summary
- Total Actions Processed: 1,247
- Zone Violations Detected: 3
- Violations Blocked: 3
- False Positives: 0

## Violations by Zone
| Zone | Violations | Blocked | Warned |
|------|------------|---------|--------|
| Cloud | 2 | 2 | 0 |
| Local | 1 | 1 | 0 |

## Top Violation Types
1. send_email attempted from cloud (2)
2. bypass_approval attempted from local (1)

## Compliance Status: ✅ PASS
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-02 | Initial policy definition |

---

**Policy Owner:** AI Employee System  
**Review Cycle:** Monthly  
**Enforcement:** Automatic via ZonePolicyValidator
