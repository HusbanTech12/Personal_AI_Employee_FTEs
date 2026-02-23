#!/usr/bin/env python3
"""
Approval Agent - Silver Tier AI Employee

Monitors tasks requiring human approval before sensitive actions.
Moves tasks to Needs_Approval folder and waits for human decision.

Behavior:
- Detects sensitive actions (email, posting, payments)
- Moves task to /Needs_Approval folder
- Generates approval_request.md with details
- Monitors for human approval (APPROVED: YES/NO)
- Resumes execution automatically when approved

Sensitive Actions:
- Email sending
- Social media posting
- Payments/financial transactions
- Database modifications
- Production deployments

Usage:
    python approval_agent.py

Stop:
    Press Ctrl+C to gracefully stop
"""

import os
import sys
import re
import shutil
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ApprovalAgent")


class ApprovalStatus(Enum):
    """Approval status states."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_INFO = "needs_info"


class SensitiveActionType(Enum):
    """Types of sensitive actions requiring approval."""
    EMAIL = "email"
    SOCIAL_POST = "social_post"
    PAYMENT = "payment"
    DATABASE_CHANGE = "database_change"
    PRODUCTION_DEPLOY = "production_deploy"
    API_KEY_ACCESS = "api_key_access"
    DATA_EXPORT = "data_export"
    OTHER = "other"


class ApprovalAgent:
    """
    Approval Agent for AI Employee Vault.
    
    Manages human approval workflow for sensitive actions.
    """
    
    # Keywords that trigger approval requirement
    SENSITIVE_KEYWORDS = {
        SensitiveActionType.EMAIL: [
            'send email', 'email blast', 'mass email', 'newsletter',
            'skill: email', 'smtp', 'mailchimp'
        ],
        SensitiveActionType.SOCIAL_POST: [
            'linkedin', 'twitter', 'facebook', 'social media',
            'publish post', 'post to', 'skill: linkedin',
            'skill: twitter', 'skill: social'
        ],
        SensitiveActionType.PAYMENT: [
            'payment', 'pay', 'invoice', 'transfer', 'wire',
            'purchase', 'buy', 'charge', 'refund', 'billing',
            'credit card', 'bank', 'financial', '$', 'USD', 'EUR'
        ],
        SensitiveActionType.DATABASE_CHANGE: [
            'database', 'sql', 'migrate', 'schema', 'drop table',
            'alter table', 'delete from', 'truncate', 'db change'
        ],
        SensitiveActionType.PRODUCTION_DEPLOY: [
            'deploy', 'production', 'prod', 'live site',
            'release', 'push to prod', 'go live'
        ],
        SensitiveActionType.API_KEY_ACCESS: [
            'api key', 'secret', 'credential', 'password',
            'token', 'authentication', 'private key'
        ],
        SensitiveActionType.DATA_EXPORT: [
            'export data', 'download data', 'data dump',
            'backup', 'extract data', 'data export'
        ]
    }
    
    # Approval folder name
    NEEDS_APPROVAL_DIR_NAME = "Needs_Approval"
    
    def __init__(self, needs_action_dir: Path, needs_approval_dir: Path, 
                 logs_dir: Path, done_dir: Path):
        self.needs_action_dir = needs_action_dir
        self.needs_approval_dir = needs_approval_dir
        self.logs_dir = logs_dir
        self.done_dir = done_dir
        
        self.pending_approvals: Dict[str, ApprovalStatus] = {}
        self.processed_tasks: Set[str] = set()
        
        # Ensure directories exist
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)
        self.needs_approval_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.done_dir.mkdir(parents=True, exist_ok=True)
    
    def scan_for_sensitive_tasks(self) -> List[Path]:
        """Scan Needs_Action for tasks requiring approval."""
        sensitive_tasks = []
        
        if not self.needs_action_dir.exists():
            return sensitive_tasks
        
        for file_path in self.needs_action_dir.iterdir():
            if (file_path.is_file() and 
                file_path.suffix.lower() == '.md' and
                file_path.name not in self.processed_tasks):
                
                action_type = self.detect_sensitive_action(file_path)
                if action_type:
                    sensitive_tasks.append((file_path, action_type))
        
        return sensitive_tasks
    
    def detect_sensitive_action(self, file_path: Path) -> Optional[SensitiveActionType]:
        """Detect if task requires approval and what type."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()
            
            # Check each sensitive action type
            for action_type, keywords in self.SENSITIVE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in content:
                        logger.info(f"Detected {action_type.value} action in {file_path.name}")
                        return action_type
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to detect sensitive action: {e}")
            return None
    
    def read_task(self, file_path: Path) -> Tuple[str, Dict]:
        """Read task file and extract frontmatter + content."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        frontmatter = {}
        body = content
        
        # Parse frontmatter
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if frontmatter_match:
            fm_text = frontmatter_match.group(1)
            for line in fm_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip()
            body = content[frontmatter_match.end():]
        
        return body, frontmatter
    
    def generate_approval_request(self, file_path: Path, 
                                   action_type: SensitiveActionType) -> str:
        """Generate approval request markdown content."""
        content, frontmatter = self.read_task(file_path)
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Determine risk level based on action type
        risk_levels = {
            SensitiveActionType.EMAIL: "MEDIUM",
            SensitiveActionType.SOCIAL_POST: "LOW",
            SensitiveActionType.PAYMENT: "HIGH",
            SensitiveActionType.DATABASE_CHANGE: "HIGH",
            SensitiveActionType.PRODUCTION_DEPLOY: "CRITICAL",
            SensitiveActionType.API_KEY_ACCESS: "HIGH",
            SensitiveActionType.DATA_EXPORT: "MEDIUM",
            SensitiveActionType.OTHER: "MEDIUM"
        }
        
        risk_level = risk_levels.get(action_type, "MEDIUM")
        
        # Generate approval request
        approval_content = f"""---
title: Approval Request: {frontmatter.get('title', file_path.stem)}
original_task: {file_path.name}
request_type: {action_type.value}
risk_level: {risk_level}
status: pending_approval
created: {timestamp}
expires: {(datetime.now().replace(hour=23, minute=59, second=59)).strftime('%Y-%m-%d %H:%M:%S')}
---

# Approval Request

**Generated:** {timestamp}

**Original Task:** `{file_path.name}`

**Action Type:** {action_type.value.replace('_', ' ').title()}

**Risk Level:** {risk_level}

---

## ⚠️ Approval Required

This task requires **human approval** before proceeding because it involves a **sensitive action**.

---

## Task Summary

**Title:** {frontmatter.get('title', file_path.stem)}

**Priority:** {frontmatter.get('priority', 'standard')}

**Description:**
```
{content[:500]}{'...' if len(content) > 500 else ''}
```

---

## Risk Assessment

| Factor | Assessment |
|--------|------------|
| **Action Type** | {action_type.value.replace('_', ' ').title()} |
| **Risk Level** | {risk_level} |
| **Reversible** | {'Yes' if action_type in [SensitiveActionType.EMAIL, SensitiveActionType.SOCIAL_POST] else 'No/Partial'} |
| **Impact Scope** | {'External' if action_type in [SensitiveActionType.EMAIL, SensitiveActionType.SOCIAL_POST] else 'Internal'} |

---

## Approval Instructions

To approve or reject this request:

1. **Review** the task details above
2. **Add your decision** at the bottom of this file:
   ```
   ---
   
   ## Decision
   
   APPROVED: YES
   
   Approved by: [Your Name]
   Date: {timestamp}
   Notes: [Optional notes]
   ```
   
   Or to reject:
   ```
   ---
   
   ## Decision
   
   APPROVED: NO
   
   Rejected by: [Your Name]
   Date: {timestamp}
   Reason: [Reason for rejection]
   ```

3. **Save** the file - the agent will automatically detect your decision

---

## Timeout

This approval request will expire at: **{(datetime.now().replace(hour=23, minute=59, second=59)).strftime('%Y-%m-%d %H:%M:%S')}**

If not approved/rejected by then, the task will be automatically rejected.

---

*Generated by AI Employee Approval Agent*
"""
        
        return approval_content
    
    def move_to_approval(self, file_path: Path, action_type: SensitiveActionType) -> Optional[Path]:
        """Move task to Needs_Approval folder and create approval request."""
        try:
            # Create approval request filename
            approval_filename = f"approval_{file_path.stem}.md"
            approval_path = self.needs_approval_dir / approval_filename
            
            # Generate and save approval request
            approval_content = self.generate_approval_request(file_path, action_type)
            
            with open(approval_path, 'w', encoding='utf-8') as f:
                f.write(approval_content)
            
            logger.info(f"Approval request created: {approval_path.name}")
            
            # Move original task to approval folder (keep beside approval request)
            task_copy_path = self.needs_approval_dir / file_path.name
            shutil.copy2(file_path, task_copy_path)
            
            logger.info(f"Task copied to approval folder: {task_copy_path.name}")
            
            # Track pending approval
            self.pending_approvals[approval_path.name] = ApprovalStatus.PENDING
            
            return approval_path
            
        except Exception as e:
            logger.error(f"Failed to move to approval: {e}")
            return None
    
    def check_approval_status(self, approval_path: Path) -> Tuple[ApprovalStatus, Optional[str]]:
        """Check if approval has been granted or rejected."""
        try:
            with open(approval_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Look for approval decision
            approved_yes = re.search(r'APPROVED:\s*YES', content, re.IGNORECASE)
            approved_no = re.search(r'APPROVED:\s*NO', content, re.IGNORECASE)
            rejected = re.search(r'REJECTED:\s*YES', content, re.IGNORECASE)
            
            if approved_yes:
                # Extract approver info
                approver_match = re.search(r'Approved by:\s*([^\n]+)', content)
                approver = approver_match.group(1).strip() if approver_match else "Unknown"
                
                return ApprovalStatus.APPROVED, approver
            
            if approved_no or rejected:
                # Extract rejection reason
                reason_match = re.search(r'Reason:\s*([^\n]+)', content)
                reason = reason_match.group(1).strip() if reason_match else "No reason provided"
                
                return ApprovalStatus.REJECTED, reason
            
            # Check for needs more info
            needs_info = re.search(r'NEEDS INFO|NEEDS_MORE_INFO|MORE INFORMATION', content, re.IGNORECASE)
            if needs_info:
                return ApprovalStatus.NEEDS_INFO, "More information requested"
            
            return ApprovalStatus.PENDING, None
            
        except Exception as e:
            logger.error(f"Failed to check approval status: {e}")
            return ApprovalStatus.PENDING, None
    
    def process_approved_task(self, approval_path: Path, approver: str):
        """Process an approved task - move back to Needs_Action for execution."""
        try:
            # Find the original task file
            content, frontmatter = self.read_task(approval_path)
            original_task = frontmatter.get('original_task', '')
            
            if original_task:
                task_path = self.needs_approval_dir / original_task
                
                if task_path.exists():
                    # Update task frontmatter to indicate approved
                    with open(task_path, 'r', encoding='utf-8') as f:
                        task_content = f.read()
                    
                    # Add approval info to frontmatter
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    approval_marker = f"""
# Approval Information
approved: true
approved_by: {approver}
approved_at: {timestamp}

"""
                    
                    # Insert after existing frontmatter
                    if '---\n' in task_content:
                        parts = task_content.split('---\n', 2)
                        if len(parts) >= 2:
                            task_content = f"---\n{parts[1]}---\n{approval_marker}{parts[2] if len(parts) > 2 else ''}"
                    
                    with open(task_path, 'w', encoding='utf-8') as f:
                        f.write(task_content)
                    
                    # Move back to Needs_Action
                    destination = self.needs_action_dir / original_task
                    shutil.move(str(task_path), str(destination))
                    
                    logger.info(f"Approved task moved back to Needs_Action: {original_task}")
            
            # Move approval request to Done
            done_approval = self.done_dir / approval_path.name
            shutil.move(str(approval_path), str(done_approval))
            
            # Clean up tracking
            if approval_path.name in self.pending_approvals:
                del self.pending_approvals[approval_path.name]
            
            # Log approval
            self.log_approval_event(approval_path.name, "APPROVED", approver)
            
        except Exception as e:
            logger.error(f"Failed to process approved task: {e}")
    
    def process_rejected_task(self, approval_path: Path, reason: str):
        """Process a rejected task - move to Done with rejection note."""
        try:
            # Find the original task file
            content, frontmatter = self.read_task(approval_path)
            original_task = frontmatter.get('original_task', '')
            
            if original_task:
                task_path = self.needs_approval_dir / original_task
                
                if task_path.exists():
                    # Add rejection note
                    rejection_note = f"""
---

## Rejected

**Status:** REJECTED
**Reason:** {reason}
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

This task was rejected during the approval process and will not be executed.
"""
                    
                    with open(task_path, 'a', encoding='utf-8') as f:
                        f.write(rejection_note)
                    
                    # Move to Done
                    done_task = self.done_dir / original_task
                    shutil.move(str(task_path), str(done_task))
                    
                    logger.info(f"Rejected task moved to Done: {original_task}")
            
            # Move approval request to Done
            done_approval = self.done_dir / approval_path.name
            shutil.move(str(approval_path), str(done_approval))
            
            # Clean up tracking
            if approval_path.name in self.pending_approvals:
                del self.pending_approvals[approval_path.name]
            
            # Log rejection
            self.log_approval_event(approval_path.name, "REJECTED", reason)
            
        except Exception as e:
            logger.error(f"Failed to process rejected task: {e}")
    
    def log_approval_event(self, approval_name: str, decision: str, details: str):
        """Log approval/rejection event."""
        try:
            log_file = self.logs_dir / "approval_log.md"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Create log file if doesn't exist
            if not log_file.exists():
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write("# Approval Log\n\n")
                    f.write("| Timestamp | Request | Decision | Details |\n")
                    f.write("|-----------|---------|----------|--------|\n")
            
            # Write entry
            log_entry = f"| {timestamp} | {approval_name} | {decision} | {details} |\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            logger.debug("Approval log updated")
            
        except Exception as e:
            logger.error(f"Failed to log approval event: {e}")
    
    def scan_pending_approvals(self) -> List[Path]:
        """Scan Needs_Approval for pending approval requests."""
        pending = []
        
        if not self.needs_approval_dir.exists():
            return pending
        
        for file_path in self.needs_approval_dir.iterdir():
            if (file_path.is_file() and 
                file_path.suffix.lower() == '.md' and
                file_path.name.startswith('approval_')):
                
                # Check if already processed
                status, _ = self.check_approval_status(file_path)
                if status == ApprovalStatus.PENDING:
                    pending.append(file_path)
                else:
                    # Status changed - process it
                    if status == ApprovalStatus.APPROVED:
                        _, approver = self.check_approval_status(file_path)
                        self.process_approved_task(file_path, approver or "Unknown")
                    elif status == ApprovalStatus.REJECTED:
                        _, reason = self.check_approval_status(file_path)
                        self.process_rejected_task(file_path, reason or "Unknown")
        
        return pending
    
    def run(self):
        """Main approval agent loop."""
        logger.info("=" * 60)
        logger.info("Approval Agent started")
        logger.info(f"Monitoring: {self.needs_action_dir}")
        logger.info(f"Approval Folder: {self.needs_approval_dir}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Sensitive actions requiring approval:")
        for action_type in SensitiveActionType:
            logger.info(f"  - {action_type.value.replace('_', ' ').title()}")
        logger.info("")
        logger.info("Waiting for tasks requiring approval...")
        logger.info("")
        
        while True:
            try:
                # Scan for new sensitive tasks
                sensitive_tasks = self.scan_for_sensitive_tasks()
                
                for task_file, action_type in sensitive_tasks:
                    logger.info(f"Sensitive action detected: {action_type.value}")
                    self.move_to_approval(task_file, action_type)
                    self.processed_tasks.add(task_file.name)
                
                # Check pending approvals for decisions
                pending = self.scan_pending_approvals()
                
                if pending:
                    logger.info(f"Pending approvals: {len(pending)}")
                    for approval_path in pending:
                        logger.info(f"  - {approval_path.name}")
                elif not sensitive_tasks:
                    # No activity - wait before next check
                    time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("")
                logger.info("Approval Agent stopping...")
                break
            except Exception as e:
                logger.error(f"Error in approval agent loop: {e}")
                time.sleep(5)


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    agent = ApprovalAgent(
        needs_action_dir=BASE_DIR / "Needs_Action",
        needs_approval_dir=BASE_DIR / "Needs_Approval",
        logs_dir=BASE_DIR / "Logs",
        done_dir=BASE_DIR / "Done"
    )
    agent.run()
