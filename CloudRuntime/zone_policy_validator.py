#!/usr/bin/env python3
"""
Zone Policy Validator - PLATINUM Tier

Enforces work-zone specialization at runtime.
Blocks any prohibited cross-zone actions.

ZONE OWNERSHIP:
- CLOUD OWNS: Gmail reading, Email draft replies, LinkedIn post drafts, Accounting draft invoices
- LOCAL OWNS: WhatsApp sessions, Payments, Approvals, Final send/post actions

This validator MUST be called before any action execution.
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import uuid

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.parent.resolve()
CLOUD_RUNTIME_DIR = Path(__file__).parent.resolve()
LOGS_DIR = BASE_DIR / "Logs"
VIOLATIONS_DIR = CLOUD_RUNTIME_DIR / "violations"

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to both file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    VIOLATIONS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"zone_validator_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("ZonePolicyValidator")


logger = setup_logging()


# =============================================================================
# Enums
# =============================================================================

class Zone(Enum):
    """Execution zones."""
    CLOUD = "cloud"
    LOCAL = "local"


class EnforcementLevel(Enum):
    """Enforcement severity levels."""
    HARD = "hard"       # Block action immediately
    SOFT = "soft"       # Log warning, allow with audit
    DISABLED = "disabled"  # No enforcement


# =============================================================================
# Zone Policy Definition
# =============================================================================

class ZonePolicy:
    """
    Defines zone ownership and prohibited actions.
    This is the authoritative source for zone policy rules.
    """
    
    # Cloud-owned capabilities (Cloud can execute)
    CLOUD_OWNED = {
        'read_gmail',
        'generate_email_reply',
        'generate_linkedin_post',
        'generate_accounting_invoice',
        'create_draft',
        'create_approval_request',
        'read_social_feed',
        'read_accounting_data',
        'triage_email',
        'analyze_content',
    }
    
    # Local-owned capabilities (Local can execute)
    LOCAL_OWNED = {
        'send_email',
        'publish_post',
        'publish_linkedin',
        'execute_payment',
        'approve_action',
        'reject_action',
        'access_whatsapp',
        'manage_whatsapp_session',
        'send_whatsapp_message',
        'execute_final_action',
        'move_to_done',
        'archive_draft',
    }
    
    # Actions that are ALWAYS prohibited for Cloud (regardless of context)
    CLOUD_PROHIBITED = {
        'send_email',
        'publish_post',
        'publish_linkedin',
        'execute_payment',
        'approve_action',
        'reject_action',
        'access_whatsapp',
        'manage_whatsapp_session',
        'send_whatsapp_message',
        'execute_final_action',
        'bypass_approval',
        'modify_approval',
        'delete_draft',
        'send_message',
        'post_content',
        'transfer_funds',
        'finalize_invoice',
    }
    
    # Actions that are ALWAYS prohibited for Local
    LOCAL_PROHIBITED = {
        'bypass_approval',
        'execute_without_approval',
        'modify_cloud_draft',
        'access_cloud_internal',
        'read_gmail_direct',  # Must go through cloud
    }
    
    # Directory access permissions
    DIRECTORY_PERMISSIONS = {
        '/Drafts/': {
            Zone.CLOUD: {'read', 'write'},
            Zone.LOCAL: {'read'},
        },
        '/Approval_Requests/': {
            Zone.CLOUD: {'write'},
            Zone.LOCAL: {'read', 'write'},
        },
        '/Inbox/': {
            Zone.CLOUD: {'read'},
            Zone.LOCAL: {'read', 'write'},
        },
        '/Needs_Action/': {
            Zone.CLOUD: {'read'},
            Zone.LOCAL: {'read', 'write'},
        },
        '/Done/': {
            Zone.CLOUD: set(),  # No access
            Zone.LOCAL: {'read', 'write'},
        },
        '/Watchers/': {
            Zone.CLOUD: set(),  # No access
            Zone.LOCAL: {'read', 'write'},
        },
        '/Config/': {
            Zone.CLOUD: {'read'},
            Zone.LOCAL: {'read', 'write'},
        },
        '/CloudRuntime/': {
            Zone.CLOUD: {'read', 'write'},
            Zone.LOCAL: {'read'},
        },
    }


# =============================================================================
# Exceptions
# =============================================================================

class ZoneViolationError(Exception):
    """Raised when a zone policy violation is detected."""
    
    def __init__(self, message: str, zone: str, action: str, 
                 violation_id: Optional[str] = None):
        super().__init__(message)
        self.zone = zone
        self.action = action
        self.timestamp = datetime.now()
        self.violation_id = violation_id or f"violation_{uuid.uuid4().hex[:12]}"


class ZoneAccessDeniedError(Exception):
    """Raised when zone access to a resource is denied."""
    
    def __init__(self, message: str, zone: str, resource: str,
                 violation_id: Optional[str] = None):
        super().__init__(message)
        self.zone = zone
        self.resource = resource
        self.timestamp = datetime.now()
        self.violation_id = violation_id or f"access_{uuid.uuid4().hex[:12]}"


# =============================================================================
# Violation Record
# =============================================================================

@dataclass
class ViolationRecord:
    """Record of a zone policy violation."""
    violation_id: str
    timestamp: datetime
    zone: str
    action: str
    target: Optional[str] = None
    status: str = "BLOCKED"
    message: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'violation_id': self.violation_id,
            'timestamp': self.timestamp.isoformat(),
            'zone': self.zone,
            'action': self.action,
            'target': self.target,
            'status': self.status,
            'message': self.message,
            'context': self.context,
        }
    
    def to_markdown(self) -> str:
        return f"""---
violation_id: {self.violation_id}
timestamp: {self.timestamp.isoformat()}
zone: {self.zone}
attempted_action: {self.action}
target: {self.target or 'N/A'}
status: {self.status}
enforced_by: ZonePolicyValidator
---

# Zone Policy Violation

## Details
- **Zone:** {self.zone}
- **Action:** {self.action}
- **Target:** {self.target or 'N/A'}
- **Time:** {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

## Enforcement
- **Status:** {self.status}
- **Reason:** {self.message}
- **Policy:** ZONE_POLICY.md

## Resolution
{self._get_resolution_message()}

---
Context:
```json
{json.dumps(self.context, indent=2)}
```
"""
    
    def _get_resolution_message(self) -> str:
        if self.zone == 'cloud':
            return (
                f"Action was BLOCKED. Cloud zone cannot execute {self.action}. "
                f"Draft created and approval request submitted instead."
            )
        else:
            return (
                f"Action was BLOCKED. Local zone policy violation: {self.message}"
            )


# =============================================================================
# Zone Policy Validator
# =============================================================================

class ZonePolicyValidator:
    """
    Enforces work-zone specialization at runtime.
    
    This validator MUST be called before any action execution.
    It blocks prohibited cross-zone actions and logs violations.
    """
    
    def __init__(self, enforcement_level: EnforcementLevel = EnforcementLevel.HARD):
        self.enforcement_level = enforcement_level
        self.policy = ZonePolicy()
        self.violations: List[ViolationRecord] = []
        self.violation_count = 0
        self.blocked_count = 0
        
        # Load configuration if available
        self._load_config()
        
        logger.info(f"ZonePolicyValidator initialized (enforcement: {enforcement_level.value})")

    def _load_config(self) -> None:
        """Load zone configuration from file if available."""
        config_file = CLOUD_RUNTIME_DIR / "zone_config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                self.enforcement_level = EnforcementLevel(
                    config.get('enforcement_mode', 'hard')
                )
                logger.info(f"Loaded zone config: enforcement={self.enforcement_level.value}")
            except Exception as e:
                logger.warning(f"Failed to load zone config: {e}")

    def validate_action(self, zone: str, action: str, 
                        target: Optional[str] = None) -> bool:
        """
        Validate if an action is allowed in the specified zone.
        
        Args:
            zone: The execution zone ('cloud' or 'local')
            action: The action to validate
            target: Optional target of the action (for logging)
            
        Returns:
            True if action is allowed
            
        Raises:
            ZoneViolationError: If action is prohibited in zone
        """
        zone_lower = zone.lower()
        action_lower = action.lower()
        
        # Check cloud zone prohibitions
        if zone_lower == 'cloud':
            if action_lower in self.policy.CLOUD_PROHIBITED:
                return self._handle_violation('cloud', action, target,
                    f"Cloud zone cannot execute action: {action}")
        
        # Check local zone prohibitions
        elif zone_lower == 'local':
            if action_lower in self.policy.LOCAL_PROHIBITED:
                return self._handle_violation('local', action, target,
                    f"Local zone cannot execute action: {action}")
        
        # Action is allowed
        logger.debug(f"Action '{action}' allowed in zone '{zone}'")
        return True

    def validate_directory_access(self, zone: str, path: str, 
                                   operation: str) -> bool:
        """
        Validate if a zone can access a directory.
        
        Args:
            zone: The execution zone ('cloud' or 'local')
            path: The directory path
            operation: The operation ('read' or 'write')
            
        Returns:
            True if access is allowed
            
        Raises:
            ZoneAccessDeniedError: If access is denied
        """
        zone_enum = Zone(zone.lower())
        
        # Normalize path
        normalized_path = self._normalize_directory_path(path)
        
        # Check permissions
        if normalized_path in self.policy.DIRECTORY_PERMISSIONS:
            perms = self.policy.DIRECTORY_PERMISSIONS[normalized_path]
            if zone_enum in perms:
                if operation.lower() in perms[zone_enum]:
                    logger.debug(f"Access allowed: {zone} {operation} {normalized_path}")
                    return True
                else:
                    return self._handle_access_denial(
                        zone, path, operation,
                        f"Zone {zone} cannot {operation} {normalized_path}"
                    )
        
        # Default: deny if not explicitly allowed
        return self._handle_access_denial(
            zone, path, operation,
            f"No explicit permission for {zone} to {operation} {path}"
        )

    def can_create_draft(self, zone: str) -> bool:
        """Check if zone can create drafts."""
        return self.validate_action(zone, 'create_draft')

    def can_send_message(self, zone: str) -> bool:
        """Check if zone can send messages (should fail for cloud)."""
        return self.validate_action(zone, 'send_email')

    def can_approve(self, zone: str) -> bool:
        """Check if zone can approve actions (should fail for cloud)."""
        return self.validate_action(zone, 'approve_action')

    def can_execute_payment(self, zone: str) -> bool:
        """Check if zone can execute payments (should fail for cloud)."""
        return self.validate_action(zone, 'execute_payment')

    def can_access_whatsapp(self, zone: str) -> bool:
        """Check if zone can access WhatsApp (should fail for cloud)."""
        return self.validate_action(zone, 'access_whatsapp')

    def _handle_violation(self, zone: str, action: str, 
                          target: Optional[str], message: str) -> bool:
        """Handle a zone policy violation."""
        violation_id = f"violation_{uuid.uuid4().hex[:12]}"
        
        record = ViolationRecord(
            violation_id=violation_id,
            timestamp=datetime.now(),
            zone=zone,
            action=action,
            target=target,
            status="BLOCKED",
            message=message,
        )
        
        self.violations.append(record)
        self.violation_count += 1
        self.blocked_count += 1
        
        # Log violation
        logger.warning(
            f"🚫 ZONE VIOLATION [{violation_id}]: "
            f"{zone} zone attempted '{action}' - BLOCKED"
        )
        
        # Save violation record
        self._save_violation(record)
        
        # Raise exception if hard enforcement
        if self.enforcement_level == EnforcementLevel.HARD:
            raise ZoneViolationError(message, zone, action, violation_id)
        
        return False

    def _handle_access_denial(self, zone: str, path: str,
                               operation: str, message: str) -> bool:
        """Handle directory access denial."""
        violation_id = f"access_{uuid.uuid4().hex[:12]}"
        
        logger.warning(
            f"🚫 ACCESS DENIED [{violation_id}]: "
            f"{zone} zone {operation} access to {path} - BLOCKED"
        )
        
        if self.enforcement_level == EnforcementLevel.HARD:
            raise ZoneAccessDeniedError(message, zone, path, violation_id)
        
        return False

    def _save_violation(self, record: ViolationRecord) -> None:
        """Save violation record to file."""
        timestamp = record.timestamp.strftime('%Y%m%d_%H%M%S')
        violation_file = VIOLATIONS_DIR / f"{record.violation_id}_{timestamp}.md"
        
        with open(violation_file, 'w', encoding='utf-8') as f:
            f.write(record.to_markdown())
        
        logger.debug(f"Violation saved: {violation_file}")

    def _normalize_directory_path(self, path: str) -> str:
        """Normalize directory path for permission checking."""
        path_str = str(path)
        
        # Check against known directories
        known_dirs = list(self.policy.DIRECTORY_PERMISSIONS.keys())
        
        for known_dir in known_dirs:
            if path_str.endswith(known_dir.rstrip('/')) or path_str.endswith(known_dir):
                return known_dir
        
        # Return as-is if no match
        return path_str

    def get_violation_summary(self) -> Dict[str, Any]:
        """Get summary of violations."""
        cloud_violations = [v for v in self.violations if v.zone == 'cloud']
        local_violations = [v for v in self.violations if v.zone == 'local']
        
        return {
            'total_violations': len(self.violations),
            'blocked_count': self.blocked_count,
            'cloud_violations': len(cloud_violations),
            'local_violations': len(local_violations),
            'enforcement_level': self.enforcement_level.value,
            'recent_violations': [
                {
                    'id': v.violation_id,
                    'zone': v.zone,
                    'action': v.action,
                    'timestamp': v.timestamp.isoformat(),
                }
                for v in self.violations[-10:]
            ],
        }

    def generate_violation_report(self) -> Path:
        """Generate a violation report."""
        report_file = VIOLATIONS_DIR / f"violation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        summary = self.get_violation_summary()
        
        content = f"""# Zone Policy Violation Report

**Generated:** {datetime.now().isoformat()}

## Summary
| Metric | Value |
|--------|-------|
| Total Violations | {summary['total_violations']} |
| Blocked Actions | {summary['blocked_count']} |
| Cloud Violations | {summary['cloud_violations']} |
| Local Violations | {summary['local_violations']} |
| Enforcement Level | {summary['enforcement_level']} |

## Recent Violations

| ID | Zone | Action | Timestamp |
|----|------|--------|-----------|
"""
        for v in summary['recent_violations']:
            content += f"| {v['id']} | {v['zone']} | {v['action']} | {v['timestamp']} |\n"

        content += """
## Compliance Status
"""
        if summary['total_violations'] == 0:
            content += "✅ **PASS** - No violations detected\n"
        else:
            content += f"⚠️ **REVIEW** - {summary['total_violations']} violations detected (all blocked)\n"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Violation report generated: {report_file}")
        return report_file


# =============================================================================
# Decorator for Zone Validation
# =============================================================================

def enforce_zone(zone: str, allowed_actions: Optional[List[str]] = None):
    """
    Decorator to enforce zone policy on functions.
    
    Usage:
        @enforce_zone('cloud')
        def generate_draft(...):
            ...
            
        @enforce_zone('local', allowed_actions=['approve', 'reject'])
        def process_approval(...):
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            validator = ZonePolicyValidator()
            action_name = func.__name__
            
            # Validate action
            validator.validate_action(zone, action_name)
            
            # Validate against allowed actions if specified
            if allowed_actions and action_name not in allowed_actions:
                raise ZoneViolationError(
                    f"Action '{action_name}' not in allowed list",
                    zone, action_name
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# Main Entry Point (Testing)
# =============================================================================

def main():
    """Test zone policy validator."""
    print("=" * 60)
    print("Zone Policy Validator - Test Mode")
    print("=" * 60)
    print()
    
    validator = ZonePolicyValidator()
    
    # Test cases
    test_cases = [
        # (zone, action, should_pass)
        ('cloud', 'generate_email_reply', True),
        ('cloud', 'create_approval_request', True),
        ('cloud', 'send_email', False),
        ('cloud', 'approve_action', False),
        ('cloud', 'execute_payment', False),
        ('cloud', 'access_whatsapp', False),
        ('local', 'approve_action', True),
        ('local', 'send_email', True),
        ('local', 'execute_payment', True),
        ('local', 'bypass_approval', False),
    ]
    
    print("Running test cases...\n")
    
    passed = 0
    failed = 0
    
    for zone, action, should_pass in test_cases:
        try:
            result = validator.validate_action(zone, action)
            if should_pass:
                print(f"✅ PASS: {zone}.{action} allowed")
                passed += 1
            else:
                print(f"❌ FAIL: {zone}.{action} should have been blocked")
                failed += 1
        except ZoneViolationError as e:
            if not should_pass:
                print(f"✅ PASS: {zone}.{action} correctly blocked")
                passed += 1
            else:
                print(f"❌ FAIL: {zone}.{action} should have been allowed: {e}")
                failed += 1
    
    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print()
    
    summary = validator.get_violation_summary()
    print(f"Violations recorded: {summary['total_violations']}")
    print(f"Actions blocked: {summary['blocked_count']}")


if __name__ == "__main__":
    main()
