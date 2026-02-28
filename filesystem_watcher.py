#!/usr/bin/env python3
"""
Filesystem Watcher for AI Employee Vault (Bronze Tier)

Monitors the /Inbox folder for new files and processes them
according to the task_processor skill definition.

Requirements:
    pip install watchdog

Usage:
    python filesystem_watcher.py

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
from threading import Thread, Event

# =============================================================================
# Configuration
# =============================================================================

# Auto-detect base directory (works on Windows and Linux)
BASE_DIR = Path(__file__).parent.resolve()

# Centralized vault path - all Obsidian vault folders are relative to this
VAULT_PATH = BASE_DIR / "notes"

INBOX_DIR = VAULT_PATH / "Inbox"
NEEDS_ACTION_DIR = VAULT_PATH / "Needs_Action"
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
# Logging Setup
# =============================================================================

def setup_logging():
    """Configure logging to both file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"watcher_{datetime.now().strftime('%Y-%m-%d')}.log"

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
# Event Handler with Processing Logic
# =============================================================================

class InboxEventHandler:
    """Handles file creation events in the Inbox folder."""

    def __init__(self, needs_action_dir: Path, logs_dir: Path):
        self.needs_action_dir = needs_action_dir
        self.logs_dir = logs_dir
        self.processing_lock = set()

    def on_file_created(self, file_path: Path):
        """Handle new file detection."""
        if file_path.is_dir():
            return

        if file_path.suffix.lower() in IGNORED_EXTENSIONS:
            logger.debug(f"Ignoring temporary file: {file_path.name}")
            return

        if file_path.suffix.lower() not in VALID_EXTENSIONS:
            logger.debug(f"Ignoring non-markdown file: {file_path.name}")
            return

        if file_path.name in self.processing_lock:
            logger.debug(f"File already being processed: {file_path.name}")
            return

        self.process_file(file_path)

    def process_file(self, file_path: Path):
        """Process a newly detected file."""
        self.processing_lock.add(file_path.name)

        try:
            print(f"\n✅ File detected: {file_path.name}")
            logger.info(f"New file detected: {file_path.name}")

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
                logger.warning(f"File no longer exists: {file_path.name}")
                print(f"❌ File no longer exists: {file_path.name}")
                return

            self.ensure_metadata(file_path)

            destination = self.needs_action_dir / file_path.name
            success = self.copy_to_needs_action(file_path, destination)

            if not success:
                return

            print(f"✅ Task moved: {file_path.name} → Needs_Action/")

            self.write_activity_log(file_path.name)
            print(f"✅ Log updated: activity_log.md")

            self.update_dashboard(file_path.name)
            print(f"✅ Dashboard updated")

            print(f"✅ Successfully processed: {file_path.name}\n")
            logger.info(f"Successfully processed: {file_path.name}")

        except Exception as e:
            print(f"❌ Error processing {file_path.name}: {str(e)}")
            logger.error(f"Error processing {file_path.name}: {str(e)}")
            self.log_error(file_path.name, str(e))

        finally:
            self.processing_lock.discard(file_path.name)

    def ensure_metadata(self, file_path: Path):
        """Read task file and add missing metadata fields."""
        if file_path.suffix.lower() != '.md':
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip().startswith('---'):
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                title = file_path.stem.replace('_', ' ').title()

                new_content = f"""---
title: {title}
status: needs_action
priority: standard
created: {timestamp}
skill: task_processor
---

{content}
"""
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                logger.info(f"Added frontmatter to: {file_path.name}")
                return

            frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            if not frontmatter_match:
                return

            frontmatter = frontmatter_match.group(1)
            body = content[frontmatter_match.end():]

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updates = {}

            if 'title:' not in frontmatter or not self._get_frontmatter_value(frontmatter, 'title'):
                updates['title'] = file_path.stem.replace('_', ' ').title()

            if 'created:' not in frontmatter or not self._get_frontmatter_value(frontmatter, 'created'):
                updates['created'] = timestamp

            if 'status:' not in frontmatter or not self._get_frontmatter_value(frontmatter, 'status'):
                updates['status'] = 'needs_action'

            if 'priority:' not in frontmatter or not self._get_frontmatter_value(frontmatter, 'priority'):
                updates['priority'] = 'standard'

            if updates:
                new_frontmatter = frontmatter
                for key, value in updates.items():
                    pattern = rf'^{key}:\s*(.*)$'
                    match = re.search(pattern, new_frontmatter, re.MULTILINE)
                    if match and match.group(1).strip():
                        continue
                    elif match:
                        new_frontmatter = re.sub(pattern, f'{key}: {value}', new_frontmatter, flags=re.MULTILINE)
                    else:
                        new_frontmatter += f'{key}: {value}\n'

                new_content = f'---\n{new_frontmatter}---\n{body}'

                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)

                logger.info(f"Added missing metadata to: {file_path.name}")

        except Exception as e:
            logger.warning(f"Failed to ensure metadata for {file_path.name}: {str(e)}")

    def _get_frontmatter_value(self, frontmatter: str, key: str) -> str:
        """Extract a value from YAML frontmatter."""
        pattern = rf'^{key}:\s*(.*)$'
        match = re.search(pattern, frontmatter, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return ""

    def copy_to_needs_action(self, source: Path, destination: Path):
        """Copy file from Inbox to Needs_Action."""
        if destination.exists():
            logger.warning(f"Destination already exists, skipping: {destination.name}")
            print(f"⚠️  Destination already exists: {destination.name}")
            return False

        try:
            shutil.copy2(source, destination)
            logger.info(f"Copied to Needs_Action: {destination.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to copy file: {str(e)}")
            print(f"❌ Failed to copy file: {str(e)}")
            return False

    def write_activity_log(self, filename: str):
        """Write an entry to the activity log."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            if not ACTIVITY_LOG_FILE.exists():
                with open(ACTIVITY_LOG_FILE, 'w', encoding='utf-8') as f:
                    f.write("timestamp | action | file | status\n")

            log_entry = f"{timestamp} | detected | {filename} | moved_to_needs_action\n"

            with open(ACTIVITY_LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(log_entry)

            logger.info(f"Activity log updated: {filename}")

        except Exception as e:
            logger.error(f"Failed to write activity log: {str(e)}")

    def update_dashboard(self, filename: str):
        """Update Dashboard.md with new task and timestamp."""
        try:
            if not DASHBOARD_FILE.exists():
                logger.warning("Dashboard.md not found, skipping update")
                return

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
                content = f.read()

            start_marker = "<!-- AI_PARSE_START: Pending_Tasks -->"
            end_marker = "<!-- AI_PARSE_END: Pending_Tasks -->"

            if start_marker not in content or end_marker not in content:
                logger.warning("Dashboard markers not found, skipping update")
                return

            new_entry = f"- [ ] `{filename}` - Added: {timestamp}\n"

            start_idx = content.find(start_marker) + len(start_marker)
            end_idx = content.find(end_marker)

            current_content = content[start_idx:end_idx].strip()

            if "*No pending tasks*" in current_content:
                updated_section = f"\n{new_entry}"
            else:
                updated_section = f"{current_content}\n{new_entry}"

            new_content = content[:start_idx] + updated_section + content[end_idx:]

            ts_marker = "<!-- AI_PARSE_START: Timestamp -->"
            ts_end = "<!-- AI_PARSE_END: Timestamp -->"

            ts_content = f"\n**Timestamp:** `{timestamp}`\n"

            ts_start = new_content.find(ts_marker) + len(ts_marker)
            ts_end_idx = new_content.find(ts_end)

            new_content = new_content[:ts_start] + ts_content + new_content[ts_end_idx:]

            metrics_start = "<!-- AI_PARSE_START: Metrics -->"
            metrics_end = "<!-- AI_PARSE_END: Metrics -->"

            if metrics_start in new_content and metrics_end in new_content:
                new_content = re.sub(
                    r'\| Last Activity \| `[^`]*` \|',
                    f'| Last Activity | `{timestamp}` |',
                    new_content
                )

                new_content = re.sub(
                    r'\| Watcher Status \| `[^`]*` \|',
                    '| Watcher Status | `ACTIVE` |',
                    new_content
                )

                inbox_match = re.search(r'\| Inbox Tasks Count \| `(\d+)` \|', new_content)
                if inbox_match:
                    current_count = int(inbox_match.group(1))
                    new_content = re.sub(
                        r'\| Inbox Tasks Count \| `\d+` \|',
                        f'| Inbox Tasks Count | `{current_count + 1}` |',
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
    Simple polling-based file watcher that works on WSL and mounted drives.
    Polls the directory at regular intervals to detect new files.
    """

    def __init__(self, watch_dir: Path, handler: InboxEventHandler, interval: float = 1.0):
        self.watch_dir = watch_dir
        self.handler = handler
        self.interval = interval
        self.stop_event = Event()
        self.thread = None
        self.known_files = set()

    def start(self):
        """Start the polling watcher."""
        self.known_files = self._scan_files()

        self.thread = Thread(target=self._poll_loop, daemon=True)
        self.thread.start()
        logger.info(f"Polling watcher started (interval: {self.interval}s)")

    def stop(self):
        """Stop the polling watcher."""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Polling watcher stopped")

    def _scan_files(self) -> set:
        """Scan directory for .md files."""
        files = set()
        if self.watch_dir.exists():
            for f in self.watch_dir.iterdir():
                if f.is_file() and f.suffix.lower() == '.md':
                    files.add(f.name)
        return files

    def _poll_loop(self):
        """Main polling loop."""
        while not self.stop_event.is_set():
            try:
                current_files = self._scan_files()
                new_files = current_files - self.known_files

                for filename in new_files:
                    file_path = self.watch_dir / filename
                    self.handler.on_file_created(file_path)

                self.known_files = current_files

            except Exception as e:
                logger.error(f"Polling error: {str(e)}")

            self.stop_event.wait(self.interval)


# =============================================================================
# Main Execution
# =============================================================================

def ensure_directories():
    """Ensure all required directories exist."""
    for directory in [INBOX_DIR, NEEDS_ACTION_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory verified: {directory}")


def main():
    """Main entry point for the filesystem watcher."""
    print("\n" + "=" * 60)
    print("AI Employee Filesystem Watcher (Bronze Tier)")
    print("=" * 60)
    print(f"Base Directory: {BASE_DIR}")
    print(f"Monitoring: {INBOX_DIR}")
    print("Press Ctrl+C to stop")
    print("=" * 60)

    ensure_directories()

    event_handler = InboxEventHandler(NEEDS_ACTION_DIR, LOGS_DIR)
    watcher = PollingFileWatcher(INBOX_DIR, event_handler, interval=1.0)

    watcher.start()
    logger.info("Filesystem watcher started successfully")
    print("\n✅ Watching Inbox...\n")

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\n⏹️  Shutdown signal received")
        logger.info("Shutdown signal received")
        watcher.stop()

    logger.info("Filesystem watcher stopped")
    print("✅ Watcher stopped")


if __name__ == "__main__":
    main()
