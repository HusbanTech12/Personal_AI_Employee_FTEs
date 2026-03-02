#!/usr/bin/env python3
"""
Cloud Sync Manager - PLATINUM Tier

Manages synchronization between cloud runtime and local systems.
Ensures data consistency across all components.

Responsibilities:
- Sync drafts between cloud and local storage
- Sync approval requests with local filesystem
- Maintain data consistency
- Handle conflict resolution
- Provide sync status reporting
"""

import os
import sys
import json
import time
import logging
import threading
import hashlib
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.parent.resolve()
VAULT_PATH = BASE_DIR / "notes"
CLOUD_RUNTIME_DIR = Path(__file__).parent.resolve()

INBOX_DIR = VAULT_PATH / "Inbox"
NEEDS_ACTION_DIR = VAULT_PATH / "Needs_Action"
DONE_DIR = VAULT_PATH / "Done"
LOGS_DIR = BASE_DIR / "Logs"
DRAFTS_DIR = VAULT_PATH / "Drafts"
APPROVAL_REQUESTS_DIR = VAULT_PATH / "Approval_Requests"
SYNC_STATE_DIR = CLOUD_RUNTIME_DIR / "sync_state"

# Sync intervals
SYNC_INTERVAL = 60  # seconds
CONFLICT_BACKUP_DIR = CLOUD_RUNTIME_DIR / "sync_conflicts"

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to both file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    SYNC_STATE_DIR.mkdir(parents=True, exist_ok=True)
    CONFLICT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"cloud_sync_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("CloudSyncManager")


logger = setup_logging()


# =============================================================================
# Enums and Data Classes
# =============================================================================

class SyncDirection(Enum):
    """Sync direction types."""
    CLOUD_TO_LOCAL = "cloud_to_local"
    LOCAL_TO_CLOUD = "local_to_cloud"
    BIDIRECTIONAL = "bidirectional"


class SyncStatus(Enum):
    """Sync operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CONFLICT = "conflict"


class SyncEntityType(Enum):
    """Types of entities to sync."""
    DRAFT = "draft"
    APPROVAL_REQUEST = "approval_request"
    TASK = "task"
    CONFIG = "config"


@dataclass
class SyncEntity:
    """Represents an entity to be synced."""
    entity_id: str
    entity_type: SyncEntityType
    source_path: Path
    target_path: Path
    content_hash: str
    last_modified: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SyncOperation:
    """Represents a sync operation."""
    operation_id: str
    entity: SyncEntity
    direction: SyncDirection
    status: SyncStatus = SyncStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


@dataclass
class SyncState:
    """Represents the current sync state."""
    last_sync: Optional[datetime] = None
    sync_count: int = 0
    conflict_count: int = 0
    failed_count: int = 0
    entities_synced: Dict[str, datetime] = field(default_factory=dict)
    pending_operations: List[SyncOperation] = field(default_factory=list)


# =============================================================================
# Sync Manager
# =============================================================================

class CloudSyncManager:
    """
    Manages synchronization between cloud runtime and local systems.
    Ensures data consistency across all components.
    """

    def __init__(self):
        self.running = False
        self.sync_thread: Optional[threading.Thread] = None
        self.sync_state = SyncState()
        self.lock = threading.Lock()
        self.pending_operations: List[SyncOperation] = []
        
        # Ensure directories exist
        SYNC_STATE_DIR.mkdir(parents=True, exist_ok=True)
        CONFLICT_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load existing sync state
        self._load_sync_state()

    def start(self) -> None:
        """Start continuous sync monitoring."""
        self.running = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info("Cloud Sync Manager started")

    def stop(self) -> None:
        """Stop continuous sync monitoring."""
        self.running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        self._save_sync_state()
        logger.info("Cloud Sync Manager stopped")

    def _sync_loop(self) -> None:
        """Main sync loop."""
        while self.running:
            try:
                self._perform_sync()
                self._save_sync_state()
            except Exception as e:
                logger.error(f"Sync loop error: {e}")
            
            time.sleep(SYNC_INTERVAL)

    def _perform_sync(self) -> None:
        """Perform a complete sync cycle."""
        logger.info("Starting sync cycle...")
        
        # Sync drafts
        self._sync_drafts()
        
        # Sync approval requests
        self._sync_approval_requests()
        
        # Process pending operations
        self._process_pending_operations()
        
        # Update sync state
        with self.lock:
            self.sync_state.last_sync = datetime.now()
            self.sync_state.sync_count += 1
        
        logger.info(f"Sync cycle completed. Total syncs: {self.sync_state.sync_count}")

    def _sync_drafts(self) -> None:
        """Sync draft files between cloud and local storage."""
        logger.debug("Syncing drafts...")
        
        if not DRAFTS_DIR.exists():
            DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
            return
        
        # Check for new drafts
        for draft_file in DRAFTS_DIR.glob("*.md"):
            try:
                self._sync_draft_file(draft_file)
            except Exception as e:
                logger.error(f"Error syncing draft {draft_file.name}: {e}")

    def _sync_draft_file(self, draft_file: Path) -> None:
        """Sync a single draft file."""
        content_hash = self._compute_file_hash(draft_file)
        entity_id = draft_file.stem
        
        # Check if already synced
        with self.lock:
            last_synced_hash = self.sync_state.entities_synced.get(entity_id)
        
        if last_synced_hash == content_hash:
            logger.debug(f"Draft {entity_id} already synced, skipping")
            return
        
        # Parse draft metadata
        metadata = self._parse_draft_metadata(draft_file)
        
        # Create sync entity
        entity = SyncEntity(
            entity_id=entity_id,
            entity_type=SyncEntityType.DRAFT,
            source_path=draft_file,
            target_path=draft_file,  # Local storage is target for now
            content_hash=content_hash,
            last_modified=datetime.fromtimestamp(draft_file.stat().st_mtime),
            metadata=metadata
        )
        
        # Mark as synced
        with self.lock:
            self.sync_state.entities_synced[entity_id] = content_hash
        
        logger.debug(f"Draft synced: {entity_id}")

    def _sync_approval_requests(self) -> None:
        """Sync approval requests between cloud and local storage."""
        logger.debug("Syncing approval requests...")
        
        if not APPROVAL_REQUESTS_DIR.exists():
            APPROVAL_REQUESTS_DIR.mkdir(parents=True, exist_ok=True)
            return
        
        # Check for new/approved requests
        for request_file in APPROVAL_REQUESTS_DIR.glob("*.md"):
            try:
                self._sync_approval_file(request_file)
            except Exception as e:
                logger.error(f"Error syncing approval {request_file.name}: {e}")

    def _sync_approval_file(self, request_file: Path) -> None:
        """Sync a single approval request file."""
        content_hash = self._compute_file_hash(request_file)
        entity_id = request_file.stem
        
        # Check if already synced
        with self.lock:
            last_synced_hash = self.sync_state.entities_synced.get(entity_id)
        
        if last_synced_hash == content_hash:
            logger.debug(f"Approval {entity_id} already synced, skipping")
            return
        
        # Check if approval status changed
        status = self._get_approval_status(request_file)
        
        # If approved, trigger downstream actions
        if status == "approved":
            self._handle_approved_request(request_file)
        
        # Mark as synced
        with self.lock:
            self.sync_state.entities_synced[entity_id] = content_hash
        
        logger.debug(f"Approval synced: {entity_id} (status: {status})")

    def _handle_approved_request(self, request_file: Path) -> None:
        """Handle an approved request (move to Done, log, etc.)."""
        logger.info(f"Processing approved request: {request_file.name}")
        
        # Parse the request
        metadata = self._parse_approval_metadata(request_file)
        draft_id = metadata.get('draft_id', '')
        
        # Find corresponding draft
        if draft_id:
            draft_file = DRAFTS_DIR / f"{draft_id}.md"
            if draft_file.exists():
                # Move draft to Done with approval record
                done_draft_dir = DONE_DIR / "Drafts"
                done_draft_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy to Done
                shutil.copy2(draft_file, done_draft_dir / f"{draft_id}.md")
                
                # Copy approval to Done
                done_approval_dir = DONE_DIR / "Approval_Requests"
                done_approval_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(request_file, done_approval_dir / request_file.name)
                
                logger.info(f"Approved request {request_file.name} archived to Done")

    def _process_pending_operations(self) -> None:
        """Process any pending sync operations."""
        with self.lock:
            operations = self.pending_operations.copy()
        
        for op in operations:
            if op.status == SyncStatus.PENDING:
                self._execute_sync_operation(op)
                
                with self.lock:
                    if op in self.pending_operations:
                        self.pending_operations.remove(op)

    def _execute_sync_operation(self, op: SyncOperation) -> None:
        """Execute a single sync operation."""
        op.status = SyncStatus.IN_PROGRESS
        logger.info(f"Executing sync operation: {op.operation_id}")
        
        try:
            if op.direction == SyncDirection.CLOUD_TO_LOCAL:
                self._sync_cloud_to_local(op.entity)
            elif op.direction == SyncDirection.LOCAL_TO_CLOUD:
                self._sync_local_to_cloud(op.entity)
            else:
                self._sync_bidirectional(op.entity)
            
            op.status = SyncStatus.COMPLETED
            op.completed_at = datetime.now()
            logger.info(f"Sync operation completed: {op.operation_id}")
            
        except Exception as e:
            op.status = SyncStatus.FAILED
            op.error_message = str(e)
            logger.error(f"Sync operation failed: {op.operation_id} - {e}")

    def _sync_cloud_to_local(self, entity: SyncEntity) -> None:
        """Sync from cloud storage to local."""
        # Read source content
        content = entity.source_path.read_text(encoding='utf-8')
        
        # Write to target
        entity.target_path.parent.mkdir(parents=True, exist_ok=True)
        entity.target_path.write_text(content, encoding='utf-8')
        
        logger.debug(f"Synced {entity.entity_id} cloud -> local")

    def _sync_local_to_cloud(self, entity: SyncEntity) -> None:
        """Sync from local to cloud storage."""
        # Read source content
        content = entity.source_path.read_text(encoding='utf-8')
        
        # Write to target
        entity.target_path.parent.mkdir(parents=True, exist_ok=True)
        entity.target_path.write_text(content, encoding='utf-8')
        
        logger.debug(f"Synced {entity.entity_id} local -> cloud")

    def _sync_bidirectional(self, entity: SyncEntity) -> None:
        """Perform bidirectional sync with conflict detection."""
        source_hash = self._compute_file_hash(entity.source_path)
        
        if entity.target_path.exists():
            target_hash = self._compute_file_hash(entity.target_path)
            
            if source_hash != target_hash:
                # Conflict detected
                op = SyncOperation(
                    operation_id=f"conflict_{entity.entity_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    entity=entity,
                    direction=SyncDirection.BIDIRECTIONAL,
                    status=SyncStatus.CONFLICT
                )
                
                with self.lock:
                    self.sync_state.conflict_count += 1
                    self.pending_operations.append(op)
                
                self._handle_conflict(entity, op)
                return
        
        # No conflict, sync newer to older
        source_mtime = entity.source_path.stat().st_mtime
        target_mtime = entity.target_path.stat().st_mtime if entity.target_path.exists() else 0
        
        if source_mtime > target_mtime:
            self._sync_cloud_to_local(entity)
        else:
            self._sync_local_to_cloud(entity)

    def _handle_conflict(self, entity: SyncEntity, op: SyncOperation) -> None:
        """Handle a sync conflict."""
        logger.warning(f"Conflict detected for {entity.entity_id}")
        
        # Backup both versions
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        source_backup = CONFLICT_BACKUP_DIR / f"{entity.entity_id}_cloud_{timestamp}.md"
        target_backup = CONFLICT_BACKUP_DIR / f"{entity.entity_id}_local_{timestamp}.md"
        
        shutil.copy2(entity.source_path, source_backup)
        if entity.target_path.exists():
            shutil.copy2(entity.target_path, target_backup)
        
        # Create conflict resolution file
        conflict_file = CONFLICT_BACKUP_DIR / f"{entity.entity_id}_CONFLICT_{timestamp}.md"
        conflict_content = f"""---
Conflict Resolution Required
Entity: {entity.entity_id}
Type: {entity.entity_type.value}
Detected: {datetime.now().isoformat()}
---

# Sync Conflict Detected

Both cloud and local versions have been modified.

## Cloud Version
Location: {source_backup}

## Local Version  
Location: {target_backup}

## Resolution Required
Please review both versions and decide which to keep:
1. Keep cloud version (copy to local)
2. Keep local version (copy to cloud)
3. Merge manually

---
Resolution: [PENDING]
"""
        conflict_file.write_text(conflict_content, encoding='utf-8')
        
        logger.warning(f"Conflict file created: {conflict_file}")

    def queue_sync_operation(self, entity: SyncEntity, direction: SyncDirection) -> str:
        """Queue a sync operation for later processing."""
        op = SyncOperation(
            operation_id=f"sync_{entity.entity_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            entity=entity,
            direction=direction
        )
        
        with self.lock:
            self.pending_operations.append(op)
        
        logger.info(f"Queued sync operation: {op.operation_id}")
        return op.operation_id

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute MD5 hash of a file."""
        hasher = hashlib.md5()
        content = file_path.read_bytes()
        hasher.update(content)
        return hasher.hexdigest()

    def _parse_draft_metadata(self, draft_file: Path) -> Dict[str, Any]:
        """Parse metadata from a draft file."""
        metadata = {}
        
        if not draft_file.exists():
            return metadata
        
        content = draft_file.read_text(encoding='utf-8')
        
        # Extract YAML frontmatter
        match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            frontmatter = match.group(1)
            for line in frontmatter.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    metadata[key.strip()] = value.strip()
        
        return metadata

    def _parse_approval_metadata(self, request_file: Path) -> Dict[str, Any]:
        """Parse metadata from an approval request file."""
        return self._parse_draft_metadata(request_file)

    def _get_approval_status(self, request_file: Path) -> str:
        """Get the approval status from a request file."""
        if not request_file.exists():
            return "unknown"
        
        content = request_file.read_text(encoding='utf-8')
        
        if "Response: [APPROVED]" in content:
            return "approved"
        elif "Response: [REJECTED]" in content:
            return "rejected"
        elif "Response: [PENDING]" in content:
            return "pending"
        
        return "unknown"

    def _load_sync_state(self) -> None:
        """Load sync state from disk."""
        state_file = SYNC_STATE_DIR / "sync_state.json"
        
        if not state_file.exists():
            logger.info("No existing sync state found, starting fresh")
            return
        
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.sync_state.last_sync = datetime.fromisoformat(data['last_sync']) if data.get('last_sync') else None
            self.sync_state.sync_count = data.get('sync_count', 0)
            self.sync_state.conflict_count = data.get('conflict_count', 0)
            self.sync_state.failed_count = data.get('failed_count', 0)
            self.sync_state.entities_synced = data.get('entities_synced', {})
            
            logger.info(f"Loaded sync state: {self.sync_state.sync_count} previous syncs")
            
        except Exception as e:
            logger.error(f"Failed to load sync state: {e}")

    def _save_sync_state(self) -> None:
        """Save sync state to disk."""
        state_file = SYNC_STATE_DIR / "sync_state.json"
        
        data = {
            'last_sync': self.sync_state.last_sync.isoformat() if self.sync_state.last_sync else None,
            'sync_count': self.sync_state.sync_count,
            'conflict_count': self.sync_state.conflict_count,
            'failed_count': self.sync_state.failed_count,
            'entities_synced': self.sync_state.entities_synced,
        }
        
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        logger.debug("Sync state saved")

    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status."""
        with self.lock:
            return {
                'running': self.running,
                'last_sync': self.sync_state.last_sync.isoformat() if self.sync_state.last_sync else None,
                'sync_count': self.sync_state.sync_count,
                'conflict_count': self.sync_state.conflict_count,
                'failed_count': self.sync_state.failed_count,
                'pending_operations': len(self.pending_operations),
                'entities_synced': len(self.sync_state.entities_synced),
            }


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for sync manager."""
    print("=" * 60)
    print("AI Employee - PLATINUM Tier Cloud Sync Manager")
    print("=" * 60)
    print()
    print("Sync Responsibilities:")
    print("  - Draft synchronization")
    print("  - Approval request synchronization")
    print("  - Conflict detection and resolution")
    print("  - Data consistency maintenance")
    print()
    print("=" * 60)

    manager = CloudSyncManager()
    
    try:
        manager.start()
        logger.info("Sync Manager running. Press Ctrl+C to stop.")
        
        # Keep main thread alive and show periodic status
        while True:
            time.sleep(60)
            status = manager.get_sync_status()
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Sync Status: "
                  f"Syncs={status['sync_count']}, "
                  f"Conflicts={status['conflict_count']}, "
                  f"Pending={status['pending_operations']}")
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        manager.stop()
        print("\nSync Manager stopped.")


if __name__ == "__main__":
    main()
