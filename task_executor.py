#!/usr/bin/env python3
"""
Task Executor for AI Employee Vault (Bronze Tier)

Monitors the /Needs_Action folder for completed tasks and automatically
moves them to /Done folder with proper logging and dashboard updates.

Requirements:
    pip install watchdog

Usage:
    python task_executor.py

Stop:
    Press Ctrl+C to gracefully stop monitoring
"""

import os
import sys
import time
import shutil
import logging
import re
from datetime import datetime
from pathlib import Path
from threading import Thread, Event, Lock
from enum import Enum
from typing import Dict, Optional

# =============================================================================
# Configuration
# =============================================================================

# Auto-detect base directory (works on Windows and Linux)
BASE_DIR = Path(__file__).parent.resolve()

# Centralized vault path - all Obsidian vault folders are relative to this
VAULT_PATH = BASE_DIR / "notes"

INBOX_DIR = VAULT_PATH / "Inbox"
NEEDS_ACTION_DIR = VAULT_PATH / "Needs_Action"
DONE_DIR = VAULT_PATH / "Done"
LOGS_DIR = BASE_DIR / "Logs"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"
ACTIVITY_LOG_FILE = LOGS_DIR / "activity_log.md"

# File extensions to process
VALID_EXTENSIONS = {'.md'}

# File extensions to ignore (temporary files)
IGNORED_EXTENSIONS = {'.tmp', '.part', '.swp', '.bak', '.crdownload'}

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Task Status Enum
# =============================================================================

class TaskStatus(Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"


# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging():
    """Configure logging to both file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"executor_{datetime.now().strftime('%Y-%m-%d')}.log"

    # Clear existing handlers to avoid duplicates
    root_logger = logging.getLogger()
    root_logger.handlers = []

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()


# =============================================================================
# Task Completion Handler
# =============================================================================

class TaskCompletionHandler:
    """Handles completed task detection and archival."""

    def __init__(self, needs_action_dir: Path, done_dir: Path, logs_dir: Path):
        self.needs_action_dir = needs_action_dir
        self.done_dir = done_dir
        self.logs_dir = logs_dir
        self.task_queue: Dict[str, TaskStatus] = {}
        self.queue_lock = Lock()

    def scan_for_tasks(self) -> list:
        """Scan Needs_Action directory for pending tasks."""
        pending_tasks = []

        if not self.needs_action_dir.exists():
            return pending_tasks

        try:
            for file_path in self.needs_action_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in VALID_EXTENSIONS:
                    filename = file_path.name
                    with self.queue_lock:
                        if filename not in self.task_queue:
                            self.task_queue[filename] = TaskStatus.PENDING
                            pending_tasks.append(file_path)
                            logger.info(f"New task detected: {filename}")
        except Exception as e:
            logger.error(f"Error scanning directory: {str(e)}")

        return pending_tasks

    def get_next_pending_task(self) -> Optional[Path]:
        """Get the next pending task from the queue."""
        with self.queue_lock:
            for filename, status in self.task_queue.items():
                if status == TaskStatus.PENDING:
                    file_path = self.needs_action_dir / filename
                    if file_path.exists():
                        self.task_queue[filename] = TaskStatus.RUNNING
                        return file_path
        return None

    def mark_task_completed(self, filename: str):
        """Mark a task as completed in the queue."""
        with self.queue_lock:
            if filename in self.task_queue:
                self.task_queue[filename] = TaskStatus.COMPLETED
                logger.info(f"Task marked completed: {filename}")

    def check_task(self, file_path: Path):
        """Check if a task is completed and should be archived."""
        if file_path.is_dir():
            return

        if file_path.suffix.lower() in IGNORED_EXTENSIONS:
            logger.debug(f"Ignoring temporary file: {file_path.name}")
            return

        if file_path.suffix.lower() not in VALID_EXTENSIONS:
            logger.debug(f"Ignoring non-markdown file: {file_path.name}")
            return

        self.process_completed_task(file_path)

    def process_completed_task(self, file_path: Path):
        """Process a task that may be completed."""
        filename = file_path.name

        try:
            # Check if task is marked as completed
            if not self.is_task_completed(file_path):
                return

            print(f"\n✅ Completed task detected: {filename}")
            logger.info(f"Completed task detected: {filename}")

            # Wait for file to be fully written
            retries = 5
            for attempt in range(retries):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        f.read()
                    break
                except (PermissionError, IOError):
                    if attempt < retries - 1:
                        time.sleep(0.3)
                    else:
                        raise

            if not file_path.exists():
                logger.warning(f"File no longer exists: {filename}")
                print(f"❌ File no longer exists: {filename}")
                self.mark_task_completed(filename)
                return

            # Move to Done folder
            success = self.move_to_done(file_path)

            if not success:
                self.mark_task_completed(filename)
                return

            print(f"✅ Task archived to Done: {filename}")

            # Write activity log entry
            self.write_activity_log(filename)
            print(f"✅ Log updated: activity_log.md")

            # Update Dashboard
            self.update_dashboard(filename)
            print(f"✅ Dashboard updated")

            print(f"✅ Successfully archived: {filename}\n")
            logger.info(f"Successfully archived: {filename}")

        except Exception as e:
            print(f"❌ Error processing {filename}: {str(e)}")
            logger.error(f"Error processing {filename}: {str(e)}")
            self.log_error(filename, str(e))

        finally:
            self.mark_task_completed(filename)

    def is_task_completed(self, file_path: Path) -> bool:
        """Check if task has status: completed in frontmatter."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for frontmatter
            if not content.strip().startswith('---'):
                return False

            frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            if not frontmatter_match:
                return False

            frontmatter = frontmatter_match.group(1)

            # Check for status: completed
            status_pattern = r'^status:\s*(.+)$'
            match = re.search(status_pattern, frontmatter, re.MULTILINE)

            if match:
                status = match.group(1).strip().lower()
                return status == 'completed'

            return False

        except Exception as e:
            logger.warning(f"Failed to check status for {file_path.name}: {str(e)}")
            return False

    def move_to_done(self, source: Path):
        """Move file from Needs_Action to Done folder."""
        destination = self.done_dir / source.name

        if destination.exists():
            logger.warning(f"Destination already exists, skipping: {destination.name}")
            print(f"⚠️  Destination already exists: {destination.name}")
            return False

        try:
            # Move file (copy + delete original)
            shutil.copy2(source, destination)
            source.unlink()  # Remove original after successful copy

            logger.info(f"Moved to Done: {destination.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to move file: {str(e)}")
            print(f"❌ Failed to move file: {str(e)}")
            return False

    def write_activity_log(self, filename: str):
        """Write an entry to the activity log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            if not ACTIVITY_LOG_FILE.exists():
                with open(ACTIVITY_LOG_FILE, 'w', encoding='utf-8') as f:
                    f.write("timestamp | action | file | status\n")

            log_entry = f"{timestamp} | completed | {filename} | archived_to_done\n"

            with open(ACTIVITY_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry)

            logger.info(f"Activity log updated: {filename}")

        except Exception as e:
            logger.error(f"Failed to write activity log: {str(e)}")

    def update_dashboard(self, filename: str):
        """Update Dashboard.md with completion info."""
        try:
            if not DASHBOARD_FILE.exists():
                logger.warning("Dashboard.md not found, skipping update")
                return

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
                content = f.read()

            # Update Completed_Tasks section
            start_marker = "<!-- AI_PARSE_START: Completed_Tasks -->"
            end_marker = "<!-- AI_PARSE_END: Completed_Tasks -->"

            if start_marker not in content or end_marker not in content:
                logger.warning("Dashboard markers not found, skipping update")
                return

            new_entry = f"- [x] `{filename}` - Completed: {timestamp}\n"

            start_idx = content.find(start_marker) + len(start_marker)
            end_idx = content.find(end_marker)

            current_content = content[start_idx:end_idx].strip()

            if "*No completed tasks this session*" in current_content:
                updated_section = f"\n{new_entry}"
            else:
                updated_section = f"{current_content}\n{new_entry}"

            new_content = content[:start_idx] + updated_section + content[end_idx:]

            # Remove from Pending_Tasks section
            pending_start = "<!-- AI_PARSE_START: Pending_Tasks -->"
            pending_end = "<!-- AI_PARSE_END: Pending_Tasks -->"

            if pending_start in new_content and pending_end in new_content:
                p_start_idx = new_content.find(pending_start) + len(pending_start)
                p_end_idx = new_content.find(pending_end)

                pending_content = new_content[p_start_idx:p_end_idx]

                # Remove the task entry from pending
                task_pattern = rf'- \[ \] `{re.escape(filename)}`[^\n]*\n?'
                pending_content = re.sub(task_pattern, '', pending_content)

                # If empty, add placeholder
                if pending_content.strip() == '':
                    pending_content = '\n*No pending tasks*\n'

                new_content = new_content[:p_start_idx] + pending_content + new_content[p_end_idx:]

            # Update Timestamp section
            ts_marker = "<!-- AI_PARSE_START: Timestamp -->"
            ts_end = "<!-- AI_PARSE_END: Timestamp -->"

            ts_content = f"\n**Timestamp:** `{timestamp}`\n"

            ts_start = new_content.find(ts_marker) + len(ts_marker)
            ts_end_idx = new_content.find(ts_end)

            new_content = new_content[:ts_start] + ts_content + new_content[ts_end_idx:]

            # Update Metrics section
            metrics_start = "<!-- AI_PARSE_START: Metrics -->"
            metrics_end = "<!-- AI_PARSE_END: Metrics -->"

            if metrics_start in new_content and metrics_end in new_content:
                # Update Last Activity
                new_content = re.sub(
                    r'\| Last Activity \| `[^`]*` \|',
                    f'| Last Activity | `{timestamp}` |',
                    new_content
                )

                # Increment Completed Tasks
                completed_match = re.search(r'\| Completed Tasks \| `(\d+)` \|', new_content)
                if completed_match:
                    current_count = int(completed_match.group(1))
                    new_content = re.sub(
                        r'\| Completed Tasks \| `\d+` \|',
                        f'| Completed Tasks | `{current_count + 1}` |',
                        new_content
                    )

            with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
                f.write(new_content)

            logger.info("Dashboard updated successfully")

        except Exception as e:
            logger.error(f"Failed to update dashboard: {str(e)}")

    def log_error(self, filename: str, error: str):
        """Log errors to the Logs directory."""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        error_file = self.logs_dir / f"error_{timestamp}.md"

        error_entry = f"""## Error: {filename}

- **Time:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
- **Error:** `{error}`

---

"""

        try:
            if error_file.exists():
                with open(error_file, 'a', encoding='utf-8') as f:
                    f.write(error_entry)
            else:
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(f"# Error Log - {timestamp}\n\n{error_entry}")
        except Exception as e:
            logger.error(f"Failed to write error log: {str(e)}")


# =============================================================================
# Polling File Watcher (WSL/Mounted Drive Compatible)
# =============================================================================

class PollingFileWatcher:
    """
    Simple polling-based file watcher for Needs_Action folder.
    Polls the directory at regular intervals to detect completed tasks.
    """

    def __init__(self, watch_dir: Path, handler: TaskCompletionHandler, interval: float = 5.0):
        self.watch_dir = watch_dir
        self.handler = handler
        self.interval = interval
        self.stop_event = Event()
        self.thread = None
        self.last_task_count = 0

    def start(self):
        """Start the polling watcher."""
        self.thread = Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        logger.info(f"Executor polling started (interval: {self.interval}s)")

    def stop(self):
        """Stop the polling watcher."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Executor polling stopped")

    def _poll_loop(self):
        """Main polling loop with task queue management."""
        while not self.stop_event.is_set():
            try:
                # Scan for new tasks
                pending_tasks = self.handler.scan_for_tasks()
                current_task_count = len(self.handler.task_queue)

                # Log only when task state changes
                if current_task_count != self.last_task_count:
                    logger.info(f"Task queue updated: {current_task_count} tasks tracked")
                    self.last_task_count = current_task_count

                if not pending_tasks:
                    # No new tasks, wait before next check
                    self.stop_event.wait(self.interval)
                    continue

                # Process pending tasks
                task_processed = False
                for file_path in pending_tasks:
                    if self.stop_event.is_set():
                        break
                    self.handler.check_task(file_path)
                    task_processed = True

                # If tasks were processed, wait before next scan
                if task_processed:
                    self.stop_event.wait(self.interval)

            except Exception as e:
                logger.error(f"Polling error: {str(e)}")
                self.stop_event.wait(self.interval)


# =============================================================================
# Main Execution
# =============================================================================

def ensure_directories():
    """Ensure all required directories exist."""
    for directory in [NEEDS_ACTION_DIR, DONE_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory verified: {directory}")


def main():
    """Main entry point for the task executor."""
    print("\n" + "=" * 60)
    print("AI Employee Task Executor (Bronze Tier)")
    print("=" * 60)
    print(f"Base Directory: {BASE_DIR}")
    print(f"Monitoring: {NEEDS_ACTION_DIR}")
    print("Watching for: status: completed")
    print("Status system: pending → running → completed")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    ensure_directories()

    handler = TaskCompletionHandler(NEEDS_ACTION_DIR, DONE_DIR, LOGS_DIR)
    watcher = PollingFileWatcher(NEEDS_ACTION_DIR, handler, interval=5.0)

    watcher.start()
    logger.info("Task executor started successfully")
    print("\n✅ Monitoring Needs_Action for completed tasks...")
    print("⏸️  Idle mode: waiting for new tasks\n")

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n⏹️  Shutdown signal received")
        logger.info("Shutdown signal received")
        watcher.stop()

    logger.info("Task executor stopped")
    print("✅ Executor stopped")


if __name__ == "__main__":
    main()
