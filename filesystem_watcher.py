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
from datetime import datetime
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent

# =============================================================================
# Configuration
# =============================================================================

# Base directory (adjust for your system)
# Windows example: BASE_DIR = r"D:\Quarter_4\Hackathon_0\AI_Employee_Vault"
BASE_DIR = Path(__file__).parent.resolve()

INBOX_DIR = BASE_DIR / "Inbox"
NEEDS_ACTION_DIR = BASE_DIR / "Needs_Action"
LOGS_DIR = BASE_DIR / "Logs"
DASHBOARD_FILE = BASE_DIR / "Dashboard.md"

# File extensions to ignore (temporary files)
IGNORED_EXTENSIONS = {'.tmp', '.part', '.swp', '.bak'}

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
# Event Handler
# =============================================================================

class InboxEventHandler(FileSystemEventHandler):
    """Handles file creation events in the Inbox folder."""
    
    def __init__(self, needs_action_dir: Path):
        super().__init__()
        self.needs_action_dir = needs_action_dir
        self.processing_lock = set()  # Track files being processed
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        if not isinstance(event, FileCreatedEvent):
            return
        
        file_path = Path(event.src_path)
        
        # Skip temporary files
        if file_path.suffix.lower() in IGNORED_EXTENSIONS:
            logger.debug(f"Ignoring temporary file: {file_path.name}")
            return
        
        # Skip if already processing
        if file_path.name in self.processing_lock:
            logger.debug(f"File already being processed: {file_path.name}")
            return
        
        # Process the new file
        self.process_file(file_path)
    
    def process_file(self, file_path: Path):
        """Process a newly detected file."""
        self.processing_lock.add(file_path.name)
        
        try:
            logger.info(f"New file detected: {file_path.name}")
            
            # Small delay to ensure file is fully written
            time.sleep(0.5)
            
            # Validate file exists and is readable
            if not file_path.exists():
                logger.warning(f"File no longer exists: {file_path.name}")
                return
            
            # Copy to Needs_Action
            destination = self.needs_action_dir / file_path.name
            self.copy_to_needs_action(file_path, destination)
            
            # Create metadata file
            self.create_metadata(file_path, destination)
            
            # Update dashboard
            self.update_dashboard(file_path.name)
            
            logger.info(f"Successfully processed: {file_path.name}")
            
        except Exception as e:
            logger.error(f"Error processing {file_path.name}: {str(e)}")
            self.log_error(file_path.name, str(e))
            
        finally:
            self.processing_lock.discard(file_path.name)
    
    def copy_to_needs_action(self, source: Path, destination: Path):
        """Copy file from Inbox to Needs_Action."""
        if destination.exists():
            logger.warning(f"Destination already exists, skipping: {destination.name}")
            return
        
        shutil.copy2(source, destination)
        logger.info(f"Copied to Needs_Action: {destination.name}")
    
    def create_metadata(self, original: Path, copied: Path):
        """Create a metadata markdown file for the task."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        metadata_content = f"""# Task Metadata

- **Original File:** `{original.name}`
- **Received:** `{timestamp}`
- **Category:** `STANDARD`
- **Status:** `Pending`
- **Sensitive:** `false`
- **Source:** `/Inbox/{original.name}`
- **Location:** `/Needs_Action/{copied.name}`

---

## Processing Notes

*Awaiting AI Employee review*

"""
        
        meta_file = copied.with_name(f"{copied.stem}.meta.md")
        
        with open(meta_file, 'w', encoding='utf-8') as f:
            f.write(metadata_content)
        
        logger.info(f"Created metadata: {meta_file.name}")
    
    def update_dashboard(self, filename: str):
        """Add the new task to Dashboard.md pending tasks section."""
        try:
            if not DASHBOARD_FILE.exists():
                logger.warning("Dashboard.md not found, skipping update")
                return
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find and update the Pending_Tasks section
            start_marker = "<!-- AI_PARSE_START: Pending_Tasks -->"
            end_marker = "<!-- AI_PARSE_END: Pending_Tasks -->"
            
            if start_marker not in content or end_marker not in content:
                logger.warning("Dashboard markers not found, skipping update")
                return
            
            # Create new task entry
            new_entry = f"- [ ] `{filename}` - Added: {timestamp}\n"
            
            # Check if section is empty (default state)
            start_idx = content.find(start_marker) + len(start_marker)
            end_idx = content.find(end_marker)
            
            current_content = content[start_idx:end_idx].strip()
            
            if "*No pending tasks*" in current_content:
                # Replace empty state with new entry
                updated_section = f"\n{new_entry}"
            else:
                # Append to existing entries
                updated_section = f"{current_content}\n{new_entry}"
            
            # Rebuild content
            new_content = (
                content[:start_idx] + 
                updated_section + 
                content[end_idx:]
            )
            
            # Update timestamp
            timestamp_marker = "<!-- AI_PARSE_START: Timestamp -->"
            timestamp_end = "<!-- AI_PARSE_END: Timestamp -->"
            
            timestamp_content = f"\n**Timestamp:** `{timestamp}`\n"
            
            ts_start = new_content.find(timestamp_marker) + len(timestamp_marker)
            ts_end = new_content.find(timestamp_end)
            
            new_content = (
                new_content[:ts_start] + 
                timestamp_content + 
                new_content[ts_end:]
            )
            
            with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info("Dashboard updated successfully")
            
        except Exception as e:
            logger.error(f"Failed to update dashboard: {str(e)}")
    
    def log_error(self, filename: str, error: str):
        """Log errors to the Logs directory."""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        error_file = LOGS_DIR / f"error_{timestamp}.md"
        
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
# Main Execution
# =============================================================================

def ensure_directories():
    """Ensure all required directories exist."""
    for directory in [INBOX_DIR, NEEDS_ACTION_DIR, LOGS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory verified: {directory}")

def main():
    """Main entry point for the filesystem watcher."""
    logger.info("=" * 60)
    logger.info("AI Employee Filesystem Watcher (Bronze Tier)")
    logger.info("=" * 60)
    logger.info(f"Base Directory: {BASE_DIR}")
    logger.info(f"Monitoring: {INBOX_DIR}")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)
    
    # Ensure directories exist
    ensure_directories()
    
    # Set up the observer
    event_handler = InboxEventHandler(NEEDS_ACTION_DIR)
    observer = Observer()
    
    observer.schedule(
        event_handler,
        str(INBOX_DIR),
        recursive=False
    )
    
    observer.start()
    logger.info("Filesystem watcher started successfully")
    
    try:
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutdown signal received")
        observer.stop()
    
    observer.join()
    logger.info("Filesystem watcher stopped")

if __name__ == "__main__":
    main()
