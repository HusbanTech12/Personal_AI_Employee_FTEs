#!/usr/bin/env python3
"""
Delegation Manager - PLATINUM Tier

Implements Synced Vault Delegation System with claim-by-move ownership.

Folder Structure:
- /Needs_Action/<domain>/     - Unclaimed tasks by domain
- /Plans/<domain>/            - Task plans by domain
- /Pending_Approval/<domain>/ - Tasks awaiting approval
- /In_Progress/<agent>/       - Tasks claimed by agents
- /Updates/                   - Cloud-written status updates
- /Done/                      - Completed tasks

Rules:
1. Claim-by-move ownership: Agent moves file → Needs_Action → In_Progress/<agent>
2. Other agents ignore claimed tasks (in In_Progress folders)
3. Cloud writes updates only to /Updates/
4. Local merges updates into Dashboard.md (single writer rule)
"""

import os
import sys
import json
import shutil
import logging
import threading
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.parent.resolve()
VAULT_PATH = BASE_DIR / "notes"
CLOUD_RUNTIME_DIR = Path(__file__).parent.resolve()
LOGS_DIR = BASE_DIR / "Logs"

# Delegated folder structure
NEEDS_ACTION_DIR = VAULT_PATH / "Needs_Action"
PLANS_DIR = VAULT_PATH / "Plans"
PENDING_APPROVAL_DIR = VAULT_PATH / "Pending_Approval"
IN_PROGRESS_DIR = VAULT_PATH / "In_Progress"
UPDATES_DIR = VAULT_PATH / "Updates"
DONE_DIR = VAULT_PATH / "Done"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"

# Delegation state file
DELEGATION_STATE_DIR = CLOUD_RUNTIME_DIR / "delegation_state"
CLAIM_REGISTRY_FILE = DELEGATION_STATE_DIR / "claim_registry.json"

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to both file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    DELEGATION_STATE_DIR.mkdir(parents=True, exist_ok=True)
    UPDATES_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"delegation_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("DelegationManager")


logger = setup_logging()


# =============================================================================
# Enums and Data Classes
# =============================================================================

class TaskStatus(Enum):
    """Task lifecycle states."""
    UNCLAIMED = "unclaimed"           # In Needs_Action
    CLAIMED = "claimed"               # In In_Progress/<agent>
    PLANNED = "planned"               # In Plans
    PENDING_APPROVAL = "pending_approval"  # In Pending_Approval
    COMPLETED = "completed"           # In Done


class AgentType(Enum):
    """Agent types for task ownership."""
    CLOUD = "cloud"
    LOCAL = "local"
    EMAIL_AGENT = "email_agent"
    LINKEDIN_AGENT = "linkedin_agent"
    ACCOUNTING_AGENT = "accounting_agent"
    SOCIAL_AGENT = "social_agent"
    MANAGER_AGENT = "manager_agent"
    PLANNER_AGENT = "planner_agent"


@dataclass
class TaskClaim:
    """Represents a task claim by an agent."""
    task_id: str
    task_file: str
    claimed_by: str  # Agent name
    claimed_at: datetime
    source_domain: str
    status: TaskStatus = TaskStatus.CLAIMED
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'task_file': self.task_file,
            'claimed_by': self.claimed_by,
            'claimed_at': self.claimed_at.isoformat(),
            'source_domain': self.source_domain,
            'status': self.status.value,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskClaim':
        return cls(
            task_id=data['task_id'],
            task_file=data['task_file'],
            claimed_by=data['claimed_by'],
            claimed_at=datetime.fromisoformat(data['claimed_at']),
            source_domain=data['source_domain'],
            status=TaskStatus(data['status']),
            metadata=data.get('metadata', {}),
        )


@dataclass
class Update:
    """Represents a status update written by cloud."""
    update_id: str
    task_id: str
    agent: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    update_type: str = "status"  # status, progress, completion
    
    def to_markdown(self) -> str:
        return f"""---
update_id: {self.update_id}
task_id: {self.task_id}
agent: {self.agent}
timestamp: {self.timestamp.isoformat()}
update_type: {self.update_type}
---

# Update: {self.task_id}

{self.content}
"""


# =============================================================================
# Claim Registry
# =============================================================================

class ClaimRegistry:
    """
    Maintains registry of all task claims.
    Ensures only one agent can claim a task at a time.
    """
    
    def __init__(self, registry_file: Path):
        self.registry_file = registry_file
        self.claims: Dict[str, TaskClaim] = {}  # task_id -> TaskClaim
        self.lock = threading.Lock()
        self._load_registry()
    
    def _load_registry(self) -> None:
        """Load claim registry from disk."""
        if not self.registry_file.exists():
            logger.info("No existing claim registry found, starting fresh")
            return
        
        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for task_id, claim_data in data.get('claims', {}).items():
                self.claims[task_id] = TaskClaim.from_dict(claim_data)
            
            logger.info(f"Loaded claim registry: {len(self.claims)} claims")
        except Exception as e:
            logger.error(f"Failed to load claim registry: {e}")
    
    def _save_registry(self) -> None:
        """Save claim registry to disk."""
        data = {
            'last_updated': datetime.now().isoformat(),
            'claims': {
                task_id: claim.to_dict()
                for task_id, claim in self.claims.items()
            }
        }
        
        with open(self.registry_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
    
    def is_claimed(self, task_id: str) -> bool:
        """Check if a task is already claimed."""
        with self.lock:
            return task_id in self.claims
    
    def get_claim(self, task_id: str) -> Optional[TaskClaim]:
        """Get claim info for a task."""
        with self.lock:
            return self.claims.get(task_id)
    
    def register_claim(self, claim: TaskClaim) -> bool:
        """
        Register a new task claim.
        
        Returns:
            True if claim was registered successfully
            False if task was already claimed
        """
        with self.lock:
            if claim.task_id in self.claims:
                existing = self.claims[claim.task_id]
                logger.warning(
                    f"Task {claim.task_id} already claimed by {existing.claimed_by}"
                )
                return False
            
            self.claims[claim.task_id] = claim
            self._save_registry()
            logger.info(f"Task {claim.task_id} claimed by {claim.claimed_by}")
            return True
    
    def release_claim(self, task_id: str, agent: str) -> bool:
        """
        Release a task claim (when task is completed or abandoned).
        
        Returns:
            True if claim was released
            False if agent doesn't own the claim
        """
        with self.lock:
            if task_id not in self.claims:
                logger.warning(f"Task {task_id} has no claim to release")
                return False
            
            claim = self.claims[task_id]
            if claim.claimed_by != agent:
                logger.warning(
                    f"Agent {agent} cannot release claim by {claim.claimed_by}"
                )
                return False
            
            del self.claims[task_id]
            self._save_registry()
            logger.info(f"Task {task_id} claim released by {agent}")
            return True
    
    def get_claims_by_agent(self, agent: str) -> List[TaskClaim]:
        """Get all claims owned by an agent."""
        with self.lock:
            return [
                claim for claim in self.claims.values()
                if claim.claimed_by == agent
            ]
    
    def get_unclaimed_tasks(self) -> List[str]:
        """Get list of unclaimed task IDs."""
        # This would need to scan Needs_Action directory
        # For now, return tasks not in claims
        return []
    
    def get_registry_summary(self) -> Dict[str, Any]:
        """Get summary of claim registry."""
        with self.lock:
            agents: Dict[str, int] = {}
            for claim in self.claims.values():
                agents[claim.claimed_by] = agents.get(claim.claimed_by, 0) + 1
            
            return {
                'total_claims': len(self.claims),
                'claims_by_agent': agents,
                'last_updated': datetime.now().isoformat(),
            }


# =============================================================================
# Delegation Manager
# =============================================================================

class DelegationManager:
    """
    Manages task delegation with claim-by-move ownership.
    
    Implements the Synced Vault Delegation System:
    1. Agents claim tasks by moving them to In_Progress/<agent>
    2. Other agents ignore claimed tasks
    3. Cloud writes updates only to /Updates/
    4. Local merges updates into Dashboard.md (single writer)
    """
    
    def __init__(self):
        self.registry = ClaimRegistry(CLAIM_REGISTRY_FILE)
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Ensure all directories exist
        self._ensure_directories()
        
        logger.info("DelegationManager initialized")
    
    def _ensure_directories(self) -> None:
        """Ensure all delegated directories exist."""
        dirs = [
            NEEDS_ACTION_DIR,
            PLANS_DIR,
            PENDING_APPROVAL_DIR,
            IN_PROGRESS_DIR,
            UPDATES_DIR,
            DONE_DIR,
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {d}")
    
    def _get_domain_subdir(self, base_dir: Path, domain: str) -> Path:
        """Get or create domain subdirectory."""
        domain_dir = base_dir / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        return domain_dir
    
    def _get_agent_subdir(self, base_dir: Path, agent: str) -> Path:
        """Get or create agent subdirectory."""
        agent_dir = base_dir / agent
        agent_dir.mkdir(parents=True, exist_ok=True)
        return agent_dir
    
    def claim_task(self, task_file: Path, agent: str, 
                   domain: str = "general") -> Tuple[bool, str]:
        """
        Claim a task by moving it from Needs_Action to In_Progress/<agent>.
        
        Args:
            task_file: Path to task file in Needs_Action
            agent: Name of the claiming agent
            domain: Task domain for categorization
            
        Returns:
            Tuple of (success, message)
        """
        # Validate task file exists in Needs_Action
        if not task_file.exists():
            return False, f"Task file not found: {task_file}"
        
        if not str(task_file).startswith(str(NEEDS_ACTION_DIR)):
            return False, f"Task must be in Needs_Action: {task_file}"
        
        # Extract task ID from filename
        task_id = task_file.stem
        
        # Check if already claimed
        if self.registry.is_claimed(task_id):
            existing_claim = self.registry.get_claim(task_id)
            return False, f"Task already claimed by {existing_claim.claimed_by}"
        
        # Create claim record
        claim = TaskClaim(
            task_id=task_id,
            task_file=task_file.name,
            claimed_by=agent,
            claimed_at=datetime.now(),
            source_domain=domain,
            status=TaskStatus.CLAIMED,
        )
        
        # Register claim (atomic - fails if already claimed)
        if not self.registry.register_claim(claim):
            return False, "Failed to register claim (race condition)"
        
        # Move file to In_Progress/<agent>
        agent_dir = self._get_agent_subdir(IN_PROGRESS_DIR, agent)
        destination = agent_dir / task_file.name
        
        try:
            shutil.move(str(task_file), str(destination))
            logger.info(f"Task {task_id} claimed by {agent}: {task_file} → {destination}")
            return True, f"Task claimed successfully: {destination}"
        except Exception as e:
            # Rollback claim registration
            self.registry.release_claim(task_id, agent)
            return False, f"Failed to move task file: {e}"
    
    def release_task(self, task_id: str, agent: str, 
                     destination: str = "done") -> Tuple[bool, str]:
        """
        Release a claimed task (move to Done or back to Needs_Action).
        
        Args:
            task_id: ID of the task to release
            agent: Name of the releasing agent (must own the claim)
            destination: Where to move the task ('done', 'needs_action', 'pending_approval')
            
        Returns:
            Tuple of (success, message)
        """
        # Verify agent owns the claim
        claim = self.registry.get_claim(task_id)
        if not claim:
            return False, f"No claim found for task: {task_id}"
        
        if claim.claimed_by != agent:
            return False, f"Agent {agent} does not own claim for {task_id}"
        
        # Find current task file
        current_file = IN_PROGRESS_DIR / agent / claim.task_file
        if not current_file.exists():
            # Try to find it anyway
            current_file = self._find_task_file(task_id)
            if not current_file:
                return False, f"Task file not found: {task_id}"
        
        # Determine destination directory
        if destination == "done":
            dest_dir = DONE_DIR
            status = TaskStatus.COMPLETED
        elif destination == "needs_action":
            dest_dir = self._get_domain_subdir(NEEDS_ACTION_DIR, claim.source_domain)
            status = TaskStatus.UNCLAIMED
        elif destination == "pending_approval":
            dest_dir = self._get_domain_subdir(PENDING_APPROVAL_DIR, claim.source_domain)
            status = TaskStatus.PENDING_APPROVAL
        else:
            return False, f"Invalid destination: {destination}"
        
        # Move file
        try:
            destination_file = dest_dir / claim.task_file
            shutil.move(str(current_file), str(destination_file))
            
            # Release claim
            self.registry.release_claim(task_id, agent)
            
            # Update claim status before releasing
            claim.status = status
            
            logger.info(f"Task {task_id} released by {agent} to {destination}")
            return True, f"Task released to {destination}"
        except Exception as e:
            return False, f"Failed to move task file: {e}"
    
    def _find_task_file(self, task_id: str) -> Optional[Path]:
        """Find a task file by ID across all directories."""
        # Search in In_Progress first
        for agent_dir in IN_PROGRESS_DIR.iterdir():
            if agent_dir.is_dir():
                for f in agent_dir.glob(f"{task_id}*"):
                    return f
        
        # Search in other directories
        for search_dir in [NEEDS_ACTION_DIR, PENDING_APPROVAL_DIR, PLANS_DIR]:
            for f in search_dir.glob(f"{task_id}*"):
                return f
        
        return None
    
    def write_update(self, task_id: str, agent: str, content: str,
                     update_type: str = "status") -> Path:
        """
        Write an update to /Updates/ directory.
        
        Cloud agents write updates here only.
        Local merges these into Dashboard.md (single writer rule).
        
        Args:
            task_id: ID of the task being updated
            agent: Name of the updating agent
            content: Update content
            update_type: Type of update (status, progress, completion)
            
        Returns:
            Path to the update file
        """
        update = Update(
            update_id=f"update_{task_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            task_id=task_id,
            agent=agent,
            content=content,
            update_type=update_type,
        )
        
        # Write update file
        update_file = UPDATES_DIR / f"{update.update_id}.md"
        
        with open(update_file, 'w', encoding='utf-8') as f:
            f.write(update.to_markdown())
        
        logger.info(f"Update written for {task_id}: {update_file}")
        return update_file
    
    def get_unclaimed_tasks(self, domain: Optional[str] = None) -> List[Path]:
        """
        Get list of unclaimed tasks in Needs_Action.
        
        Args:
            domain: Optional domain filter
            
        Returns:
            List of task file paths
        """
        unclaimed = []
        
        # Determine search directory
        if domain:
            search_dir = self._get_domain_subdir(NEEDS_ACTION_DIR, domain)
        else:
            search_dir = NEEDS_ACTION_DIR
        
        if not search_dir.exists():
            return unclaimed
        
        # Find all markdown files
        for f in search_dir.glob("*.md"):
            task_id = f.stem
            if not self.registry.is_claimed(task_id):
                unclaimed.append(f)
        
        return unclaimed
    
    def get_agent_tasks(self, agent: str) -> List[TaskClaim]:
        """Get all tasks claimed by an agent."""
        return self.registry.get_claims_by_agent(agent)
    
    def get_dashboard_updates(self) -> List[Update]:
        """
        Get all updates that need to be merged into Dashboard.
        
        Local component should call this and merge updates,
        then mark them as processed.
        """
        updates = []
        
        if not UPDATES_DIR.exists():
            return updates
        
        for f in UPDATES_DIR.glob("*.md"):
            try:
                content = f.read_text(encoding='utf-8')
                
                # Parse frontmatter
                update_data = self._parse_update_frontmatter(content)
                if update_data:
                    updates.append(Update(
                        update_id=update_data.get('update_id', f.stem),
                        task_id=update_data.get('task_id', 'unknown'),
                        agent=update_data.get('agent', 'unknown'),
                        content=self._extract_update_body(content),
                        timestamp=datetime.fromisoformat(update_data.get('timestamp', datetime.now().isoformat())),
                        update_type=update_data.get('update_type', 'status'),
                    ))
            except Exception as e:
                logger.error(f"Failed to parse update {f.name}: {e}")
        
        # Sort by timestamp
        updates.sort(key=lambda u: u.timestamp, reverse=True)
        return updates
    
    def _parse_update_frontmatter(self, content: str) -> Dict[str, Any]:
        """Parse YAML frontmatter from update content."""
        match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            frontmatter = match.group(1)
            data = {}
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    data[key.strip()] = value.strip()
            return data
        return {}
    
    def _extract_update_body(self, content: str) -> str:
        """Extract body content after frontmatter."""
        match = re.search(r'^---\s*\n.*?\n---\s*\n(.*)', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return content
    
    def mark_update_processed(self, update_file: Path) -> bool:
        """
        Mark an update as processed (move to Done subfolder).
        
        Local should call this after merging update into Dashboard.
        """
        if not update_file.exists():
            return False
        
        processed_dir = UPDATES_DIR / "processed"
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            shutil.move(str(update_file), str(processed_dir / update_file.name))
            logger.info(f"Update processed: {update_file.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to mark update processed: {e}")
            return False
    
    def get_delegation_summary(self) -> Dict[str, Any]:
        """Get summary of delegation state."""
        registry_summary = self.registry.get_registry_summary()
        
        # Count files in each directory
        dir_counts = {
            'needs_action': self._count_files(NEEDS_ACTION_DIR),
            'plans': self._count_files(PLANS_DIR),
            'pending_approval': self._count_files(PENDING_APPROVAL_DIR),
            'in_progress': self._count_files(IN_PROGRESS_DIR),
            'updates': self._count_files(UPDATES_DIR),
            'done': self._count_files(DONE_DIR),
        }
        
        # Get pending updates
        pending_updates = len([
            f for f in UPDATES_DIR.glob("*.md")
            if f.is_file() and not str(f).endswith('/processed')
        ])
        
        return {
            'registry': registry_summary,
            'directory_counts': dir_counts,
            'pending_updates': pending_updates,
            'timestamp': datetime.now().isoformat(),
        }
    
    def _count_files(self, directory: Path) -> int:
        """Count files in a directory recursively."""
        if not directory.exists():
            return 0
        return len([f for f in directory.rglob("*.md") if f.is_file()])
    
    def start_monitoring(self) -> None:
        """Start monitoring delegation state."""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Delegation monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop monitoring delegation state."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Delegation monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                summary = self.get_delegation_summary()
                logger.debug(
                    f"Delegation state: {summary['registry']['total_claims']} claims, "
                    f"{summary['pending_updates']} pending updates"
                )
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
            
            # Check every 30 seconds
            time.sleep(30)


# =============================================================================
# Decorator for Claim Enforcement
# =============================================================================

def require_claim(agent: str):
    """
    Decorator to enforce task claim before executing action.
    
    Usage:
        @require_claim(agent="email_agent")
        def process_email(self, task_id: str, ...):
            ...
    """
    def decorator(func):
        def wrapper(self, task_id: str, *args, **kwargs):
            # Verify claim
            claim = self.delegation.registry.get_claim(task_id)
            if not claim:
                raise ValueError(f"Task {task_id} is not claimed")
            if claim.claimed_by != agent:
                raise ValueError(
                    f"Task {task_id} is claimed by {claim.claimed_by}, not {agent}"
                )
            
            return func(self, task_id, *args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# Time import for monitoring
# =============================================================================
import time


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for delegation manager."""
    print("=" * 60)
    print("AI Employee - PLATINUM Tier Delegation Manager")
    print("=" * 60)
    print()
    print("Synced Vault Delegation System")
    print()
    print("Folder Structure:")
    print("  /Needs_Action/<domain>/     - Unclaimed tasks")
    print("  /Plans/<domain>/            - Task plans")
    print("  /Pending_Approval/<domain>/ - Awaiting approval")
    print("  /In_Progress/<agent>/       - Claimed tasks")
    print("  /Updates/                   - Cloud status updates")
    print("  /Done/                      - Completed tasks")
    print()
    print("Rules:")
    print("  1. Claim-by-move ownership")
    print("  2. Other agents ignore claimed tasks")
    print("  3. Cloud writes updates only to /Updates/")
    print("  4. Local merges updates (single writer)")
    print()
    print("=" * 60)

    manager = DelegationManager()
    
    try:
        manager.start_monitoring()
        logger.info("Delegation Manager running. Press Ctrl+C to stop.")
        
        # Keep main thread alive and show periodic status
        while True:
            time.sleep(60)
            summary = manager.get_delegation_summary()
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                  f"Claims: {summary['registry']['total_claims']}, "
                  f"Pending Updates: {summary['pending_updates']}")
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        manager.stop_monitoring()
        print("\nDelegation Manager stopped.")


if __name__ == "__main__":
    main()
