#!/usr/bin/env python3
"""
Distributed PLATINUM Autonomy Loop

Separates reasoning (Cloud) from execution (Local) with approval-based workflow.

Architecture:
┌─────────────────────────────────────────────────────────────────┐
│                    CLOUD ZONE                                    │
│  Continuous Reasoning Loop                                       │
│  - Analyze tasks                                                 │
│  - Generate plans                                                │
│  - Create drafts                                                 │
│  - Submit for approval                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    /Pending_Approval/
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LOCAL ZONE                                    │
│  Approval Execution Loop                                         │
│  - Monitor approved tasks                                        │
│  - Execute MCP actions                                           │
│  - Move to /Done/ on completion                                  │
└─────────────────────────────────────────────────────────────────┘

Completion Condition: File moved to /Done/
"""

import os
import sys
import json
import logging
import time
import threading
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import requests

# Import zone policy validator
sys.path.insert(0, str(Path(__file__).parent))
from zone_policy_validator import ZonePolicyValidator, ZoneViolationError, EnforcementLevel

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.parent.resolve()
VAULT_PATH = BASE_DIR / "notes"
CLOUD_RUNTIME_DIR = Path(__file__).parent.resolve()
LOGS_DIR = BASE_DIR / "Logs"

# Directories
NEEDS_ACTION_DIR = VAULT_PATH / "Needs_Action"
PENDING_APPROVAL_DIR = VAULT_PATH / "Pending_Approval"
APPROVED_DIR = VAULT_PATH / "Approved"
REJECTED_DIR = VAULT_PATH / "Rejected"
DONE_DIR = VAULT_PATH / "Done"
IN_PROGRESS_DIR = VAULT_PATH / "In_Progress"
UPDATES_DIR = VAULT_PATH / "Updates"

# MCP Servers
MCP_SERVERS = {
    'email': {'host': '127.0.0.1', 'port': 8765},
    'linkedin': {'host': '127.0.0.1', 'port': 8766},
    'accounting': {'host': '127.0.0.1', 'port': 8767},
    'social': {'host': '127.0.0.1', 'port': 8768},
    'automation': {'host': '127.0.0.1', 'port': 8769},
}

# Loop intervals
CLOUD_REASONING_INTERVAL = 15  # seconds
LOCAL_EXECUTION_INTERVAL = 10  # seconds

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"platinum_loop_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("PLATINUMAutonomyLoop")


logger = setup_logging()


# =============================================================================
# Enums and Data Classes
# =============================================================================

class LoopPhase(Enum):
    """Autonomy loop phases."""
    REASONING = "reasoning"
    PLANNING = "planning"
    APPROVAL_WAIT = "approval_wait"
    EXECUTION = "execution"
    VALIDATION = "validation"
    COMPLETION = "completion"


class TaskStatus(Enum):
    """Task status in the loop."""
    NEW = "new"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReasoningState:
    """Cloud reasoning state."""
    task_id: str
    task_file: Path
    status: TaskStatus = TaskStatus.NEW
    analysis: str = ""
    plan: List[Dict[str, Any]] = field(default_factory=list)
    drafts_created: List[str] = field(default_factory=list)
    approval_requests: List[str] = field(default_factory=list)
    reasoning_iterations: int = 0
    last_reasoning: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'status': self.status.value,
            'analysis': self.analysis,
            'plan': self.plan,
            'drafts_created': self.drafts_created,
            'approval_requests': self.approval_requests,
            'reasoning_iterations': self.reasoning_iterations,
            'last_reasoning': self.last_reasoning.isoformat() if self.last_reasoning else None,
        }


@dataclass
class ExecutionState:
    """Local execution state."""
    task_id: str
    approval_file: Path
    status: TaskStatus = TaskStatus.APPROVED
    actions_executed: List[Dict[str, Any]] = field(default_factory=list)
    results: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'status': self.status.value,
            'actions_executed': self.actions_executed,
            'results': self.results,
            'errors': self.errors,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


# =============================================================================
# Cloud Reasoning Loop
# =============================================================================

class CloudReasoningLoop:
    """
    Cloud Zone: Continuous reasoning loop.
    
    Responsibilities:
    - Analyze tasks in Needs_Action
    - Generate execution plans
    - Create drafts via MCP
    - Submit approval requests
    - Track reasoning iterations
    """
    
    def __init__(self):
        self.zone_validator = ZonePolicyValidator(EnforcementLevel.HARD)
        self.zone = "cloud"
        self.running = False
        self.reasoning_thread: Optional[threading.Thread] = None
        
        # Active reasoning states
        self.active_tasks: Dict[str, ReasoningState] = {}
        self.processed_tasks: set = set()
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'tasks_analyzed': 0,
            'plans_generated': 0,
            'drafts_created': 0,
            'approvals_submitted': 0,
            'reasoning_iterations': 0,
        }
        
        logger.info("Cloud Reasoning Loop initialized")
    
    def start(self) -> None:
        """Start the reasoning loop."""
        self.running = True
        self.reasoning_thread = threading.Thread(target=self._reasoning_loop, daemon=True)
        self.reasoning_thread.start()
        logger.info("Cloud Reasoning Loop started")
    
    def stop(self) -> None:
        """Stop the reasoning loop."""
        self.running = False
        if self.reasoning_thread:
            self.reasoning_thread.join(timeout=5)
        logger.info("Cloud Reasoning Loop stopped")
    
    def _reasoning_loop(self) -> None:
        """Main reasoning loop."""
        while self.running:
            try:
                self._reasoning_cycle()
            except Exception as e:
                logger.error(f"Reasoning loop error: {e}")
            
            time.sleep(CLOUD_REASONING_INTERVAL)
    
    def _reasoning_cycle(self) -> None:
        """Single reasoning cycle."""
        # Find new tasks
        new_tasks = self._find_new_tasks()
        
        for task_file in new_tasks:
            self._process_task(task_file)
        
        # Update active tasks
        for task_id, state in list(self.active_tasks.items()):
            if state.status == TaskStatus.COMPLETED:
                continue
            
            # Continuous reasoning
            self._continuous_reasoning(state)
    
    def _find_new_tasks(self) -> List[Path]:
        """Find new tasks in Needs_Action."""
        new_tasks = []
        
        if not NEEDS_ACTION_DIR.exists():
            return new_tasks
        
        for f in NEEDS_ACTION_DIR.glob("*.md"):
            task_id = f.stem
            
            # Skip if already processed or in progress
            if task_id in self.processed_tasks:
                continue
            
            if task_id in self.active_tasks:
                continue
            
            new_tasks.append(f)
        
        return new_tasks
    
    def _process_task(self, task_file: Path) -> None:
        """Process a new task."""
        task_id = task_file.stem
        
        logger.info(f"Processing new task: {task_id}")
        
        # Create reasoning state
        state = ReasoningState(
            task_id=task_id,
            task_file=task_file,
            status=TaskStatus.ANALYZING,
        )
        
        # Analyze task
        self._analyze_task(state)
        
        # Generate plan
        self._generate_plan(state)
        
        # Create drafts
        self._create_drafts(state)
        
        # Submit for approval
        self._submit_approval(state)
        
        # Add to active tasks
        with self.lock:
            self.active_tasks[task_id] = state
            self.processed_tasks.add(task_id)
    
    def _analyze_task(self, state: ReasoningState) -> None:
        """Analyze task requirements."""
        logger.info(f"Analyzing task: {state.task_id}")
        
        # Read task file
        content = state.task_file.read_text(encoding='utf-8')
        
        # Extract metadata
        frontmatter = self._parse_frontmatter(content)
        
        # Analyze
        state.analysis = f"""
Task: {state.task_id}
Type: {frontmatter.get('type', frontmatter.get('skill', 'general'))}
Priority: {frontmatter.get('priority', 'normal')}
Content Preview: {content[:200]}...
"""
        
        with self.lock:
            self.stats['tasks_analyzed'] += 1
        
        logger.info(f"Task analysis complete: {state.task_id}")
    
    def _generate_plan(self, state: ReasoningState) -> None:
        """Generate execution plan."""
        logger.info(f"Generating plan for: {state.task_id}")
        
        # Parse task content for steps
        content = state.task_file.read_text(encoding='utf-8')
        
        # Generate plan steps
        plan = []
        
        # Step 1: Create draft
        plan.append({
            'step': 1,
            'action': 'create_draft',
            'zone': 'cloud',
            'description': 'Create draft content',
        })
        
        # Step 2: Request approval
        plan.append({
            'step': 2,
            'action': 'request_approval',
            'zone': 'cloud',
            'description': 'Submit for local approval',
        })
        
        # Step 3: Wait for approval (blocking)
        plan.append({
            'step': 3,
            'action': 'wait_approval',
            'zone': 'local',
            'description': 'Wait for local approval decision',
        })
        
        # Step 4: Execute (local only)
        plan.append({
            'step': 4,
            'action': 'execute_action',
            'zone': 'local',
            'description': 'Execute approved action via MCP',
        })
        
        state.plan = plan
        
        with self.lock:
            self.stats['plans_generated'] += 1
        
        logger.info(f"Plan generated: {len(plan)} steps")
    
    def _create_drafts(self, state: ReasoningState) -> None:
        """Create draft content."""
        logger.info(f"Creating drafts for: {state.task_id}")
        
        # Read task content
        content = state.task_file.read_text(encoding='utf-8')
        frontmatter = self._parse_frontmatter(content)
        
        # Determine draft type
        draft_type = frontmatter.get('type', frontmatter.get('skill', 'general'))
        
        # Create draft file
        drafts_dir = VAULT_PATH / "Drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        
        draft_file = drafts_dir / f"{state.task_id}_draft.md"
        
        draft_content = f"""---
draft_id: {state.task_id}
draft_type: {draft_type}
task_file: {state.task_file}
created_at: {datetime.now().isoformat()}
status: draft
---

# Draft: {state.task_id}

{content}

---
*Generated by Cloud Reasoning Loop*
"""
        
        draft_file.write_text(draft_content, encoding='utf-8')
        
        state.drafts_created.append(str(draft_file))
        
        with self.lock:
            self.stats['drafts_created'] += 1
        
        logger.info(f"Draft created: {draft_file}")
    
    def _submit_approval(self, state: ReasoningState) -> None:
        """Submit task for approval."""
        logger.info(f"Submitting for approval: {state.task_id}")
        
        # Create approval request
        PENDING_APPROVAL_DIR.mkdir(parents=True, exist_ok=True)
        
        approval_file = PENDING_APPROVAL_DIR / f"{state.task_id}_approval.md"
        
        approval_content = f"""---
request_id: approval_{state.task_id}
task_id: {state.task_id}
draft_file: {state.drafts_created[0] if state.drafts_created else 'N/A'}
priority: normal
status: pending
created_at: {datetime.now().isoformat()}
---

# Approval Request

**Task:** {state.task_id}

**Analysis:**
{state.analysis}

**Plan:**
{json.dumps(state.plan, indent=2)}

**Drafts Created:**
{', '.join(state.drafts_created)}

---

## Response Required

Please review and respond with:
- APPROVE: Execute the planned actions
- REJECT: Decline with reason

Response: [PENDING]

---
*Submitted by Cloud Reasoning Loop*
*Cloud cannot execute - Local approval required*
"""
        
        approval_file.write_text(approval_content, encoding='utf-8')
        
        state.approval_requests.append(str(approval_file))
        state.status = TaskStatus.PENDING_APPROVAL
        
        with self.lock:
            self.stats['approvals_submitted'] += 1
        
        logger.info(f"Approval submitted: {approval_file}")
    
    def _continuous_reasoning(self, state: ReasoningState) -> None:
        """Continuous reasoning for active tasks."""
        state.reasoning_iterations += 1
        state.last_reasoning = datetime.now()
        
        # Check approval status
        for approval_file in state.approval_requests:
            approval_path = Path(approval_file)
            
            if not approval_path.exists():
                continue
            
            content = approval_path.read_text(encoding='utf-8')
            
            if "Response: [APPROVED]" in content:
                state.status = TaskStatus.APPROVED
                logger.info(f"Task approved: {state.task_id}")
            
            elif "Response: [REJECTED]" in content:
                state.status = TaskStatus.REJECTED
                logger.info(f"Task rejected: {state.task_id}")
        
        with self.lock:
            self.stats['reasoning_iterations'] += 1
    
    def _parse_frontmatter(self, content: str) -> Dict[str, str]:
        """Parse YAML frontmatter."""
        metadata = {}
        
        match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            frontmatter = match.group(1)
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
        
        return metadata
    
    def get_stats(self) -> Dict[str, Any]:
        """Get reasoning loop statistics."""
        with self.lock:
            stats = self.stats.copy()
        
        stats['active_tasks'] = len(self.active_tasks)
        stats['pending_approval'] = sum(
            1 for s in self.active_tasks.values() 
            if s.status == TaskStatus.PENDING_APPROVAL
        )
        stats['approved'] = sum(
            1 for s in self.active_tasks.values() 
            if s.status == TaskStatus.APPROVED
        )
        
        return stats


# =============================================================================
# Local Execution Loop
# =============================================================================

class LocalExecutionLoop:
    """
    Local Zone: Approval execution loop.
    
    Responsibilities:
    - Monitor Approved directory
    - Execute MCP actions
    - Track execution results
    - Move completed tasks to /Done/
    """
    
    def __init__(self):
        self.zone_validator = ZonePolicyValidator(EnforcementLevel.HARD)
        self.zone = "local"
        self.running = False
        self.execution_thread: Optional[threading.Thread] = None
        
        # Active execution states
        self.active_executions: Dict[str, ExecutionState] = {}
        self.completed_tasks: set = set()
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            'tasks_executed': 0,
            'actions_completed': 0,
            'tasks_to_done': 0,
            'execution_errors': 0,
        }
        
        logger.info("Local Execution Loop initialized")
    
    def start(self) -> None:
        """Start the execution loop."""
        self.running = True
        self.execution_thread = threading.Thread(target=self._execution_loop, daemon=True)
        self.execution_thread.start()
        logger.info("Local Execution Loop started")
    
    def stop(self) -> None:
        """Stop the execution loop."""
        self.running = False
        if self.execution_thread:
            self.execution_thread.join(timeout=5)
        logger.info("Local Execution Loop stopped")
    
    def _execution_loop(self) -> None:
        """Main execution loop."""
        while self.running:
            try:
                self._execution_cycle()
            except Exception as e:
                logger.error(f"Execution loop error: {e}")
            
            time.sleep(LOCAL_EXECUTION_INTERVAL)
    
    def _execution_cycle(self) -> None:
        """Single execution cycle."""
        # Check for approved tasks
        self._check_approved()
        
        # Process active executions
        for task_id, state in list(self.active_executions.items()):
            if state.status == TaskStatus.COMPLETED:
                continue
            
            self._execute_task(state)
    
    def _check_approved(self) -> None:
        """Check for newly approved tasks."""
        if not APPROVED_DIR.exists():
            return
        
        # Also check Pending_Approval for decisions
        if PENDING_APPROVAL_DIR.exists():
            for approval_file in PENDING_APPROVAL_DIR.glob("*.md"):
                content = approval_file.read_text(encoding='utf-8')
                
                if "Response: [APPROVED]" in content:
                    # Move to Approved
                    shutil.move(str(approval_file), str(APPROVED_DIR / approval_file.name))
                    logger.info(f"Task approved: {approval_file.name}")
                
                elif "Response: [REJECTED]" in content:
                    # Move to Rejected
                    shutil.move(str(approval_file), str(REJECTED_DIR / approval_file.name))
                    logger.info(f"Task rejected: {approval_file.name}")
        
        # Process Approved directory
        for approval_file in APPROVED_DIR.glob("*.md"):
            task_id = approval_file.stem.replace('_approval', '')
            
            if task_id in self.completed_tasks:
                continue
            
            if task_id in self.active_executions:
                continue
            
            # Create execution state
            state = ExecutionState(
                task_id=task_id,
                approval_file=approval_file,
                status=TaskStatus.APPROVED,
            )
            
            with self.lock:
                self.active_executions[task_id] = state
            
            logger.info(f"New approved task: {task_id}")
    
    def _execute_task(self, state: ExecutionState) -> None:
        """Execute an approved task."""
        if state.status != TaskStatus.APPROVED:
            return
        
        logger.info(f"Executing task: {state.task_id}")
        
        state.started_at = state.started_at or datetime.now()
        state.status = TaskStatus.EXECUTING
        
        # Parse approval file
        content = state.approval_file.read_text(encoding='utf-8')
        frontmatter = self._parse_frontmatter(content)
        
        # Get draft file
        draft_file = frontmatter.get('draft_file', '')
        
        # Execute actions from plan
        plan = self._extract_plan(content)
        
        for action_item in plan:
            if action_item.get('zone') != 'local':
                continue
            
            action = action_item.get('action', '')
            
            if action == 'execute_action':
                # Execute via MCP
                result = self._execute_mcp_action(state, draft_file)
                state.results.append(result)
                
                if result.get('success'):
                    with self.lock:
                        self.stats['actions_completed'] += 1
                else:
                    state.errors.append(result.get('error', 'Unknown error'))
                    with self.lock:
                        self.stats['execution_errors'] += 1
        
        # Mark as completed
        state.status = TaskStatus.COMPLETED
        state.completed_at = datetime.now()
        
        # Move to Done
        self._move_to_done(state)
        
        with self.lock:
            self.stats['tasks_executed'] += 1
            self.stats['tasks_to_done'] += 1
            self.completed_tasks.add(state.task_id)
        
        logger.info(f"Task completed: {state.task_id}")
    
    def _execute_mcp_action(self, state: ExecutionState, draft_file: str) -> Dict[str, Any]:
        """Execute action via MCP server."""
        logger.info(f"Executing MCP action for: {state.task_id}")
        
        try:
            # Read draft content
            draft_path = Path(draft_file)
            if not draft_path.exists():
                return {'success': False, 'error': f'Draft not found: {draft_file}'}
            
            content = draft_path.read_text(encoding='utf-8')
            frontmatter = self._parse_frontmatter(content)
            
            # Determine action type
            draft_type = frontmatter.get('draft_type', 'general')
            
            # Map to MCP action
            action_map = {
                'email_reply': ('email', 'send'),
                'social_media_post': ('social', 'publish'),
                'linkedin_post': ('linkedin', 'publish'),
                'accounting_action': ('accounting', 'post'),
            }
            
            server, action = action_map.get(draft_type, ('automation', 'execute'))
            
            # Call MCP server
            mcp_server = MCP_SERVERS.get(server)
            if not mcp_server:
                return {'success': False, 'error': f'Unknown MCP server: {server}'}
            
            url = f"http://{mcp_server['host']}:{mcp_server['port']}/rpc"
            
            payload = {
                'action': action,
                'params': {
                    'draft_id': state.task_id,
                    'content': content,
                    'metadata': frontmatter,
                }
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            return {
                'success': not result.get('error'),
                'action': f"{server}/{action}",
                'result': result.get('result'),
                'error': result.get('error'),
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _move_to_done(self, state: ExecutionState) -> None:
        """Move completed task to /Done/."""
        logger.info(f"Moving task to Done: {state.task_id}")
        
        try:
            # Create Done subdirectory
            done_subdir = DONE_DIR / datetime.now().strftime('%Y-%m')
            done_subdir.mkdir(parents=True, exist_ok=True)
            
            # Move approval file
            if state.approval_file.exists():
                shutil.move(str(state.approval_file), str(done_subdir / state.approval_file.name))
            
            # Create completion summary
            summary_file = done_subdir / f"{state.task_id}_completed.md"
            
            summary_content = f"""---
task_id: {state.task_id}
status: completed
started_at: {state.started_at.isoformat() if state.started_at else 'N/A'}
completed_at: {state.completed_at.isoformat() if state.completed_at else 'N/A'}
---

# Task Completed

**Task:** {state.task_id}
**Completed:** {state.completed_at.strftime('%Y-%m-%d %H:%M:%S') if state.completed_at else 'N/A'}

---

## Execution Summary

- **Actions Executed:** {len(state.actions_executed)}
- **Results:** {len(state.results)}
- **Errors:** {len(state.errors)}

---

## Results

{json.dumps(state.results, indent=2)}

---

## Errors (if any)

{chr(10).join(state.errors) if state.errors else 'None'}

---
*Completed by PLATINUM Autonomy Loop*
*Completion Condition: File moved to /Done/*
"""
            
            summary_file.write_text(summary_content, encoding='utf-8')
            
            logger.info(f"Task moved to Done: {state.task_id}")
            
        except Exception as e:
            logger.error(f"Failed to move task to Done: {e}")
    
    def _extract_plan(self, content: str) -> List[Dict[str, Any]]:
        """Extract plan from approval content."""
        # Try to parse plan from content
        match = re.search(r'\*\*Plan:\*\*\s*\n```(?:json)?\s*\n(.*?)\n```', content, re.DOTALL)
        
        if match:
            try:
                return json.loads(match.group(1))
            except:
                pass
        
        # Default plan
        return [
            {'step': 4, 'action': 'execute_action', 'zone': 'local'},
        ]
    
    def _parse_frontmatter(self, content: str) -> Dict[str, str]:
        """Parse YAML frontmatter."""
        metadata = {}
        
        match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            frontmatter = match.group(1)
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
        
        return metadata
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution loop statistics."""
        with self.lock:
            stats = self.stats.copy()
        
        stats['active_executions'] = len(self.active_executions)
        stats['completed_tasks'] = len(self.completed_tasks)
        
        return stats


# =============================================================================
# PLATINUM Autonomy Loop
# =============================================================================

class PLATINUMAutonomyLoop:
    """
    Distributed PLATINUM Autonomy Loop.
    
    Combines Cloud Reasoning and Local Execution loops.
    """
    
    def __init__(self):
        self.cloud_loop = CloudReasoningLoop()
        self.local_loop = LocalExecutionLoop()
        self.running = False
        
        logger.info("PLATINUM Autonomy Loop initialized")
    
    def start(self) -> None:
        """Start both loops."""
        logger.info("Starting PLATINUM Autonomy Loop...")
        
        self.cloud_loop.start()
        self.local_loop.start()
        
        self.running = True
        
        logger.info("PLATINUM Autonomy Loop started")
    
    def stop(self) -> None:
        """Stop both loops."""
        logger.info("Stopping PLATINUM Autonomy Loop...")
        
        self.cloud_loop.stop()
        self.local_loop.stop()
        
        self.running = False
        
        logger.info("PLATINUM Autonomy Loop stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics."""
        return {
            'cloud': self.cloud_loop.get_stats(),
            'local': self.local_loop.get_stats(),
            'running': self.running,
        }


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point."""
    print("=" * 60)
    print("PLATINUM Autonomy Loop - Distributed")
    print("=" * 60)
    print()
    print("Cloud Zone (Reasoning):")
    print("  - Continuous task analysis")
    print("  - Plan generation")
    print("  - Draft creation")
    print("  - Approval submission")
    print()
    print("Local Zone (Execution):")
    print("  - Approval monitoring")
    print("  - MCP action execution")
    print("  - Task completion")
    print()
    print("Completion Condition: File moved to /Done/")
    print()
    print("=" * 60)

    loop = PLATINUMAutonomyLoop()
    
    try:
        loop.start()
        logger.info("PLATINUM Autonomy Loop running. Press Ctrl+C to stop.")
        
        while True:
            time.sleep(60)
            
            stats = loop.get_stats()
            cloud = stats['cloud']
            local = stats['local']
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                  f"Cloud: Analyzed={cloud['tasks_analyzed']}, "
                  f"Pending={cloud['pending_approval']}, "
                  f"Approved={cloud['approved']} | "
                  f"Local: Executed={local['tasks_executed']}, "
                  f"Done={local['tasks_to_done']}")
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        loop.stop()
        
        stats = loop.get_stats()
        print("\n" + "=" * 60)
        print("Final Statistics:")
        print(f"  Cloud - Analyzed: {stats['cloud']['tasks_analyzed']}")
        print(f"  Cloud - Drafts Created: {stats['cloud']['drafts_created']}")
        print(f"  Local - Executed: {stats['local']['tasks_executed']}")
        print(f"  Local - Moved to Done: {stats['local']['tasks_to_done']}")
        print("=" * 60)
        
        print("\nPLATINUM Autonomy Loop stopped.")


if __name__ == "__main__":
    import shutil  # Import here to avoid circular dependency
    main()
