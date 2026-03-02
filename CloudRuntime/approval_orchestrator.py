#!/usr/bin/env python3
"""
Approval Orchestrator - PLATINUM Tier

Monitors approval decision directories and executes actions based on decisions.

Monitors:
- /Approved/ - Tasks approved for execution
- /Rejected/ - Tasks rejected and to be archived

Actions:
- If Approved: Execute MCP action locally
- If Rejected: Archive task with reason
- Move completed tasks to /Done/

Zone: LOCAL (executes final actions)
"""

import os
import sys
import json
import shutil
import logging
import threading
import time
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import requests

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.parent.resolve()
VAULT_PATH = BASE_DIR / "notes"
CLOUD_RUNTIME_DIR = Path(__file__).parent.resolve()
LOGS_DIR = BASE_DIR / "Logs"

# Approval directories
APPROVED_DIR = VAULT_PATH / "Approved"
REJECTED_DIR = VAULT_PATH / "Rejected"
PENDING_APPROVAL_DIR = VAULT_PATH / "Pending_Approval"
DONE_DIR = VAULT_PATH / "Done"
ARCHIVE_DIR = VAULT_PATH / "Archive"

# MCP Servers
MCP_SERVERS = {
    'email': {'host': '127.0.0.1', 'port': 8765},
    'linkedin': {'host': '127.0.0.1', 'port': 8766},
    'accounting': {'host': '127.0.0.1', 'port': 8767},
    'social': {'host': '127.0.0.1', 'port': 8768},
    'automation': {'host': '127.0.0.1', 'port': 8769},
}

# Monitoring interval
MONITOR_INTERVAL = 10  # seconds

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to both file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"approval_orchestrator_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("ApprovalOrchestrator")


logger = setup_logging()


# =============================================================================
# Enums and Data Classes
# =============================================================================

class ApprovalDecision(Enum):
    """Approval decision types."""
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


class ExecutionStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class ApprovalTask:
    """Represents an approved/rejected task."""
    task_id: str
    original_file: str
    decision: ApprovalDecision
    decision_file: Path
    approved_at: datetime
    approved_by: str = ""
    mcp_action: Optional[str] = None
    mcp_params: Dict[str, Any] = field(default_factory=dict)
    rejection_reason: str = ""
    execution_status: ExecutionStatus = ExecutionStatus.PENDING
    result: Optional[str] = None


@dataclass
class ExecutionResult:
    """Result of MCP action execution."""
    success: bool
    action: str
    result_data: Any
    error_message: Optional[str] = None
    executed_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# MCP Action Executor
# =============================================================================

class MCPActionExecutor:
    """
    Executes MCP actions locally after approval.
    Only runs in LOCAL zone.
    """
    
    def __init__(self):
        self.mcp_servers = MCP_SERVERS
        self.execution_log: List[ExecutionResult] = []
    
    def execute_action(self, action: str, params: Dict[str, Any]) -> ExecutionResult:
        """
        Execute an MCP action.
        
        Args:
            action: Action in format "server/action" (e.g., "email/send")
            params: Action parameters
            
        Returns:
            ExecutionResult
        """
        logger.info(f"Executing MCP action: {action}")
        
        # Parse action
        parts = action.split('/')
        if len(parts) != 2:
            return ExecutionResult(
                success=False,
                action=action,
                result_data=None,
                error_message=f"Invalid action format: {action}. Expected 'server/action'"
            )
        
        server_name, action_name = parts
        
        # Get server config
        if server_name not in self.mcp_servers:
            return ExecutionResult(
                success=False,
                action=action,
                result_data=None,
                error_message=f"Unknown MCP server: {server_name}"
            )
        
        server = self.mcp_servers[server_name]
        
        # Execute via MCP RPC
        try:
            result = self._call_mcp_rpc(server, action_name, params)
            
            execution_result = ExecutionResult(
                success=True,
                action=action,
                result_data=result
            )
            
            logger.info(f"MCP action completed: {action}")
            
        except Exception as e:
            execution_result = ExecutionResult(
                success=False,
                action=action,
                result_data=None,
                error_message=str(e)
            )
            logger.error(f"MCP action failed: {action} - {e}")
        
        self.execution_log.append(execution_result)
        return execution_result
    
    def _call_mcp_rpc(self, server: Dict[str, str], action: str, 
                      params: Dict[str, Any]) -> Any:
        """Call MCP server via RPC."""
        url = f"http://{server['host']}:{server['port']}/rpc"
        
        payload = {
            'action': action,
            'params': params
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get('error'):
            raise Exception(f"MCP error: {result['error']}")
        
        return result.get('result')
    
    def execute_email_send(self, params: Dict[str, Any]) -> ExecutionResult:
        """Send email via MCP."""
        return self.execute_action('email/send', params)
    
    def execute_linkedin_publish(self, params: Dict[str, Any]) -> ExecutionResult:
        """Publish LinkedIn post via MCP."""
        return self.execute_action('linkedin/publish', params)
    
    def execute_accounting_post(self, params: Dict[str, Any]) -> ExecutionResult:
        """Post accounting entry via MCP."""
        return self.execute_action('accounting/post', params)
    
    def execute_social_publish(self, params: Dict[str, Any]) -> ExecutionResult:
        """Publish social media post via MCP."""
        return self.execute_action('social/publish', params)
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total = len(self.execution_log)
        successful = sum(1 for r in self.execution_log if r.success)
        failed = total - successful
        
        return {
            'total_executions': total,
            'successful': successful,
            'failed': failed,
            'success_rate': f"{(successful/total*100):.1f}%" if total > 0 else "N/A"
        }


# =============================================================================
# Task Parser
# =============================================================================

class TaskParser:
    """Parses approval task files to extract action details."""
    
    @staticmethod
    def parse_approval_file(file_path: Path) -> Optional[ApprovalTask]:
        """Parse an approval decision file."""
        if not file_path.exists():
            return None
        
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # Extract frontmatter
            metadata = TaskParser._parse_frontmatter(content)
            
            # Determine decision
            decision = ApprovalDecision.PENDING
            if 'approved' in file_path.parent.name.lower():
                decision = ApprovalDecision.APPROVED
            elif 'rejected' in file_path.parent.name.lower():
                decision = ApprovalDecision.REJECTED
            
            # Extract approval info
            approved_by = metadata.get('approved_by', metadata.get('approver', 'unknown'))
            rejection_reason = metadata.get('rejection_reason', metadata.get('reason', ''))
            
            # Extract MCP action
            mcp_action = metadata.get('mcp_action', metadata.get('action', ''))
            
            # Extract MCP params
            mcp_params = {}
            params_str = metadata.get('mcp_params', metadata.get('params', ''))
            if params_str:
                try:
                    mcp_params = json.loads(params_str)
                except:
                    pass
            
            # Extract original file reference
            original_file = metadata.get('original_file', metadata.get('draft_file', ''))
            draft_id = metadata.get('draft_id', '')
            
            return ApprovalTask(
                task_id=metadata.get('task_id', metadata.get('request_id', file_path.stem)),
                original_file=original_file or draft_id,
                decision=decision,
                decision_file=file_path,
                approved_at=datetime.now(),
                approved_by=approved_by,
                mcp_action=mcp_action,
                mcp_params=mcp_params,
                rejection_reason=rejection_reason,
            )
            
        except Exception as e:
            logger.error(f"Failed to parse approval file {file_path}: {e}")
            return None
    
    @staticmethod
    def _parse_frontmatter(content: str) -> Dict[str, str]:
        """Parse YAML frontmatter from content."""
        metadata = {}
        
        match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            frontmatter = match.group(1)
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
        
        return metadata
    
    @staticmethod
    def extract_draft_content(draft_file: Path) -> Dict[str, Any]:
        """Extract content from draft file for MCP action."""
        if not draft_file.exists():
            return {}
        
        try:
            content = draft_file.read_text(encoding='utf-8')
            metadata = TaskParser._parse_frontmatter(content)
            
            # Extract relevant fields based on draft type
            draft_type = metadata.get('draft_type', '')
            
            params = {'metadata': metadata}
            
            if draft_type == 'email_reply':
                params['to'] = metadata.get('recipient', '')
                params['subject'] = metadata.get('subject', '')
                params['body'] = TaskParser._extract_body(content)
                
            elif draft_type in ('social_media_post', 'linkedin_post'):
                params['content'] = TaskParser._extract_body(content)
                params['hashtags'] = metadata.get('hashtags', [])
                
            elif draft_type == 'accounting_action':
                params['action_type'] = metadata.get('action_type', '')
                params['amount'] = float(metadata.get('amount', 0))
                params['category'] = metadata.get('category', '')
                params['description'] = metadata.get('description', '')
            
            return params
            
        except Exception as e:
            logger.error(f"Failed to extract draft content: {e}")
            return {}
    
    @staticmethod
    def _extract_body(content: str) -> str:
        """Extract body content after frontmatter."""
        match = re.search(r'^---\s*\n.*?\n---\s*\n(.*)', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return content


# =============================================================================
# Approval Orchestrator
# =============================================================================

class ApprovalOrchestrator:
    """
    Orchestrates approval-based task execution.
    
    Monitors /Approved/ and /Rejected/ directories.
    Executes MCP actions for approved tasks.
    Archives rejected tasks.
    Moves completed tasks to /Done/.
    """
    
    def __init__(self):
        self.executor = MCPActionExecutor()
        self.parser = TaskParser()
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.processed_files: set = set()
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'approved_processed': 0,
            'rejected_processed': 0,
            'actions_executed': 0,
            'tasks_archived': 0,
            'tasks_completed': 0,
            'execution_failures': 0,
        }
        
        # Ensure directories exist
        self._ensure_directories()
        
        logger.info("ApprovalOrchestrator initialized (LOCAL zone)")
    
    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        dirs = [
            APPROVED_DIR,
            REJECTED_DIR,
            PENDING_APPROVAL_DIR,
            DONE_DIR,
            ARCHIVE_DIR,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
    
    def start(self) -> None:
        """Start monitoring approval directories."""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Approval Orchestrator started monitoring")
    
    def stop(self) -> None:
        """Stop monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Approval Orchestrator stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                self._check_approved()
                self._check_rejected()
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
            
            time.sleep(MONITOR_INTERVAL)
    
    def _check_approved(self) -> None:
        """Check for approved tasks to execute."""
        if not APPROVED_DIR.exists():
            return
        
        for file_path in APPROVED_DIR.glob("*.md"):
            # Skip already processed
            if str(file_path) in self.processed_files:
                continue
            
            logger.info(f"Processing approved task: {file_path.name}")
            
            # Parse approval file
            task = self.parser.parse_approval_file(file_path)
            if not task:
                logger.warning(f"Failed to parse: {file_path.name}")
                continue
            
            # Execute MCP action
            self._execute_approved_task(task)
            
            # Mark as processed
            with self.lock:
                self.processed_files.add(str(file_path))
    
    def _check_rejected(self) -> None:
        """Check for rejected tasks to archive."""
        if not REJECTED_DIR.exists():
            return
        
        for file_path in REJECTED_DIR.glob("*.md"):
            # Skip already processed
            if str(file_path) in self.processed_files:
                continue
            
            logger.info(f"Processing rejected task: {file_path.name}")
            
            # Parse rejection file
            task = self.parser.parse_approval_file(file_path)
            if not task:
                logger.warning(f"Failed to parse: {file_path.name}")
                continue
            
            # Archive task
            self._archive_rejected_task(task)
            
            # Mark as processed
            with self.lock:
                self.processed_files.add(str(file_path))
    
    def _execute_approved_task(self, task: ApprovalTask) -> None:
        """Execute an approved task."""
        logger.info(f"Executing approved task: {task.task_id}")
        
        try:
            # Determine MCP action
            if task.mcp_action:
                # Execute specified MCP action
                result = self.executor.execute_action(
                    task.mcp_action,
                    task.mcp_params
                )
            else:
                # Try to infer action from task type
                result = self._infer_and_execute(task)
            
            if result.success:
                # Move to Done
                self._move_to_done(task, result)
                
                with self.lock:
                    self.stats['approved_processed'] += 1
                    self.stats['actions_executed'] += 1
                    self.stats['tasks_completed'] += 1
                
                logger.info(f"Task completed: {task.task_id}")
            else:
                # Execution failed
                self._handle_execution_failure(task, result.error_message)
                
                with self.lock:
                    self.stats['approved_processed'] += 1
                    self.stats['execution_failures'] += 1
                
                logger.error(f"Task failed: {task.task_id} - {result.error_message}")
                
        except Exception as e:
            self._handle_execution_failure(task, str(e))
            
            with self.lock:
                self.stats['approved_processed'] += 1
                self.stats['execution_failures'] += 1
            
            logger.error(f"Task execution error: {task.task_id} - {e}")
    
    def _infer_and_execute(self, task: ApprovalTask) -> ExecutionResult:
        """Infer MCP action from task and execute."""
        # Try to find draft file
        draft_file = None
        if task.original_file:
            draft_path = Path(task.original_file)
            if draft_path.exists():
                draft_file = draft_path
            else:
                # Search in Drafts directory
                drafts_dir = BASE_DIR / "notes" / "Drafts"
                if drafts_dir.exists():
                    for f in drafts_dir.glob(f"*{task.original_file}*.md"):
                        draft_file = f
                        break
        
        if draft_file:
            # Extract params from draft
            params = self.parser.extract_draft_content(draft_file)
            metadata = params.get('metadata', {})
            draft_type = metadata.get('draft_type', '')
            
            # Map draft type to MCP action
            action_map = {
                'email_reply': 'email/send',
                'social_media_post': 'social/publish',
                'linkedin_post': 'linkedin/publish',
                'linkedin_message': 'linkedin/publish',
                'accounting_action': 'accounting/post',
                'accounting_invoice': 'accounting/post',
            }
            
            action = action_map.get(draft_type)
            if action:
                logger.info(f"Inferred action: {action} from draft type: {draft_type}")
                return self.executor.execute_action(action, params)
        
        # No action could be inferred
        return ExecutionResult(
            success=True,  # Not a failure, just no action needed
            action='none',
            result_data={'message': 'No MCP action required'}
        )
    
    def _archive_rejected_task(self, task: ApprovalTask) -> None:
        """Archive a rejected task."""
        logger.info(f"Archiving rejected task: {task.task_id}")
        
        try:
            # Create archive directory for this task
            archive_subdir = ARCHIVE_DIR / "Rejected" / datetime.now().strftime('%Y-%m')
            archive_subdir.mkdir(parents=True, exist_ok=True)
            
            # Move decision file to archive
            archive_file = archive_subdir / task.decision_file.name
            shutil.move(str(task.decision_file), str(archive_file))
            
            # Also archive original draft if exists
            if task.original_file:
                draft_path = Path(task.original_file)
                if draft_path.exists():
                    shutil.move(str(draft_path), str(archive_subdir / draft_path.name))
            
            # Create archive summary
            summary_file = archive_subdir / f"{task.task_id}_summary.md"
            self._create_archive_summary(summary_file, task)
            
            with self.lock:
                self.stats['rejected_processed'] += 1
                self.stats['tasks_archived'] += 1
            
            logger.info(f"Task archived: {task.task_id}")
            
        except Exception as e:
            logger.error(f"Failed to archive task: {task.task_id} - {e}")
    
    def _move_to_done(self, task: ApprovalTask, result: ExecutionResult) -> None:
        """Move completed task to Done directory."""
        logger.info(f"Moving task to Done: {task.task_id}")
        
        try:
            # Create Done subdirectory
            done_subdir = DONE_DIR / datetime.now().strftime('%Y-%m')
            done_subdir.mkdir(parents=True, exist_ok=True)
            
            # Move decision file to Done
            done_file = done_subdir / task.decision_file.name
            shutil.move(str(task.decision_file), str(done_file))
            
            # Also move original draft if exists
            if task.original_file:
                draft_path = Path(task.original_file)
                if draft_path.exists():
                    shutil.move(str(draft_path), str(done_subdir / draft_path.name))
            
            # Create completion summary
            summary_file = done_subdir / f"{task.task_id}_completed.md"
            self._create_completion_summary(summary_file, task, result)
            
            logger.info(f"Task moved to Done: {task.task_id}")
            
        except Exception as e:
            logger.error(f"Failed to move task to Done: {task.task_id} - {e}")
    
    def _handle_execution_failure(self, task: ApprovalTask, error: str) -> None:
        """Handle execution failure."""
        logger.warning(f"Execution failed for {task.task_id}: {error}")
        
        # Move to failed subdirectory
        failed_dir = DONE_DIR / "Failed"
        failed_dir.mkdir(parents=True, exist_ok=True)
        
        # Create failure record
        failure_file = failed_dir / f"{task.task_id}_failed.md"
        
        content = f"""---
task_id: {task.task_id}
status: failed
error: {error}
failed_at: {datetime.now().isoformat()}
---

# Execution Failed

**Task:** {task.task_id}
**Error:** {error}
**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Original Approval

Task was approved but execution failed.

## Next Steps

1. Review the error above
2. Fix any issues
3. Re-submit for approval if needed

---
"""
        
        with open(failure_file, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_archive_summary(self, file_path: Path, task: ApprovalTask) -> None:
        """Create archive summary for rejected task."""
        content = f"""---
task_id: {task.task_id}
status: rejected
archived_at: {datetime.now().isoformat()}
rejected_by: {task.approved_by}
---

# Rejected Task Archive

**Task ID:** {task.task_id}
**Rejected By:** {task.approved_by}
**Rejection Time:** {task.approved_at.strftime('%Y-%m-%d %H:%M:%S')}

---

## Rejection Reason

{task.rejection_reason or 'No reason provided.'}

---

## Original Action

- **MCP Action:** {task.mcp_action or 'N/A'}
- **Decision File:** {task.decision_file.name}

---
*Archived by ApprovalOrchestrator*
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def _create_completion_summary(self, file_path: Path, task: ApprovalTask, 
                                    result: ExecutionResult) -> None:
        """Create completion summary for executed task."""
        content = f"""---
task_id: {task.task_id}
status: completed
completed_at: {datetime.now().isoformat()}
approved_by: {task.approved_by}
mcp_action: {task.mcp_action or 'inferred'}
---

# Completed Task

**Task ID:** {task.task_id}
**Approved By:** {task.approved_by}
**Completed:** {task.approved_at.strftime('%Y-%m-%d %H:%M:%S')}

---

## Execution Details

- **MCP Action:** {result.action}
- **Status:** {'Success' if result.success else 'Failed'}
- **Executed At:** {result.executed_at.strftime('%Y-%m-%d %H:%M:%S')}

---

## Result

```json
{json.dumps(result.result_data if result.result_data else {}, indent=2)}
```

---

## Error (if any)

{result.error_message or 'No errors.'}

---
*Completed by ApprovalOrchestrator*
"""
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        with self.lock:
            stats = self.stats.copy()
        
        stats['execution_stats'] = self.executor.get_execution_stats()
        stats['processed_files'] = len(self.processed_files)
        stats['running'] = self.running
        
        return stats
    
    def process_pending_approvals(self) -> int:
        """
        Manually process any pending approvals.
        Returns count of approvals processed.
        """
        count = 0
        
        if not PENDING_APPROVAL_DIR.exists():
            return 0
        
        for file_path in PENDING_APPROVAL_DIR.glob("*.md"):
            # Check if approval decision has been made
            content = file_path.read_text(encoding='utf-8')
            
            if "Response: [APPROVED]" in content:
                # Move to Approved
                shutil.move(str(file_path), str(APPROVED_DIR / file_path.name))
                logger.info(f"Moved to Approved: {file_path.name}")
                count += 1
                
            elif "Response: [REJECTED]" in content:
                # Move to Rejected
                shutil.move(str(file_path), str(REJECTED_DIR / file_path.name))
                logger.info(f"Moved to Rejected: {file_path.name}")
                count += 1
        
        return count


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for Approval Orchestrator."""
    print("=" * 60)
    print("Approval Orchestrator - PLATINUM Tier")
    print("=" * 60)
    print()
    print("Monitoring Directories:")
    print(f"  Approved:   {APPROVED_DIR}")
    print(f"  Rejected:   {REJECTED_DIR}")
    print()
    print("Actions:")
    print("  If Approved:  Execute MCP action locally")
    print("  If Rejected:  Archive task with reason")
    print("  Completed:    Move to /Done/")
    print()
    print("Zone: LOCAL (executes final actions)")
    print()
    print("=" * 60)

    orchestrator = ApprovalOrchestrator()
    
    # Process any pending approvals first
    pending_count = orchestrator.process_pending_approvals()
    if pending_count > 0:
        print(f"\nProcessed {pending_count} pending approvals")
    
    try:
        orchestrator.start()
        logger.info("Approval Orchestrator running. Press Ctrl+C to stop.")
        
        # Keep main thread alive and show periodic status
        while True:
            time.sleep(60)
            stats = orchestrator.get_stats()
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                  f"Approved: {stats['approved_processed']}, "
                  f"Rejected: {stats['rejected_processed']}, "
                  f"Completed: {stats['tasks_completed']}, "
                  f"Archived: {stats['tasks_archived']}")
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        orchestrator.stop()
        
        # Final stats
        stats = orchestrator.get_stats()
        print("\n" + "=" * 60)
        print("Final Statistics:")
        print(f"  Approved Processed:  {stats['approved_processed']}")
        print(f"  Rejected Processed:  {stats['rejected_processed']}")
        print(f"  Actions Executed:    {stats['actions_executed']}")
        print(f"  Tasks Completed:     {stats['tasks_completed']}")
        print(f"  Tasks Archived:      {stats['tasks_archived']}")
        print(f"  Execution Failures:  {stats['execution_failures']}")
        print("=" * 60)
        
        print("\nApproval Orchestrator stopped.")


if __name__ == "__main__":
    main()
