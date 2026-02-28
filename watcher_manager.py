#!/usr/bin/env python3
"""
Watcher Manager - Gold Tier Resilience

Manages all external watchers with graceful degradation.
If one watcher fails, the system continues running other watchers.

Features:
- Try/except wrapping for every watcher startup
- Failed watchers marked as OFFLINE
- Other watchers continue running
- Centralized logging and status tracking

Usage:
    python watcher_manager.py

Stop:
    Press Ctrl+C to gracefully shutdown all watchers
"""

import os
import sys
import time
import signal
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from threading import Thread, Event, Lock

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.resolve()

# Centralized vault path - all Obsidian vault folders are relative to this
VAULT_PATH = BASE_DIR / "notes"

VENV_DIR = BASE_DIR / "venv"
LOGS_DIR = BASE_DIR / "Logs"
WATCHERS_DIR = BASE_DIR / "Watchers"
DASHBOARD_FILE = VAULT_PATH / "Dashboard.md"

# Watcher configurations
WATCHER_CONFIGS = {
    "gmail": {
        "script": WATCHERS_DIR / "gmail_watcher.py",
        "name": "Gmail Watcher",
        "description": "Email monitoring"
    },
    "whatsapp": {
        "script": WATCHERS_DIR / "whatsapp_watcher.py",
        "name": "WhatsApp Watcher",
        "description": "Message monitoring"
    },
    "linkedin": {
        "script": WATCHERS_DIR / "linkedin_watcher.py",
        "name": "LinkedIn Watcher",
        "description": "Professional network monitoring"
    },
    "filesystem": {
        "script": BASE_DIR / "filesystem_watcher.py",
        "name": "Filesystem Watcher",
        "description": "Inbox file monitoring"
    }
}

# =============================================================================
# Enums and Data Classes
# =============================================================================

class WatcherStatus(Enum):
    """Watcher status enumeration."""
    OFFLINE = "OFFLINE"
    STARTING = "STARTING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


@dataclass
class WatcherInfo:
    """Information about a watcher."""
    key: str
    name: str
    description: str
    script_path: Path
    status: WatcherStatus = WatcherStatus.OFFLINE
    pid: Optional[int] = None
    process: Optional[subprocess.Popen] = None
    error_message: str = ""
    start_time: Optional[datetime] = None
    restart_count: int = 0


@dataclass
class WatcherManagerState:
    """State of the watcher manager."""
    watchers: Dict[str, WatcherInfo] = field(default_factory=dict)
    start_time: Optional[datetime] = None
    shutdown_requested: bool = False


# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to both file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"watcher_manager_{datetime.now().strftime('%Y-%m-%d')}.log"

    # Clear existing handlers to avoid duplicates
    root_logger = logging.getLogger()
    root_logger.handlers = []

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("WatcherManager")


logger = setup_logging()


# =============================================================================
# Watcher Manager Class
# =============================================================================

class WatcherManager:
    """
    Manages all external watchers with Gold Tier resilience.

    Features:
    - Graceful degradation when watchers fail
    - Automatic status tracking
    - Centralized shutdown handling
    """

    def __init__(self):
        self.state = WatcherManagerState()
        self.state.start_time = datetime.now()
        self._lock = Lock()
        self._status_update_thread: Optional[Thread] = None
        self._stop_status_thread = Event()

        # Initialize watcher info
        for key, config in WATCHER_CONFIGS.items():
            self.state.watchers[key] = WatcherInfo(
                key=key,
                name=config["name"],
                description=config["description"],
                script_path=config["script"]
            )

    def _get_python_command(self) -> str:
        """Get the Python command to use."""
        return "python3" if sys.version_info >= (3, 0) else "python"

    def _start_watcher(self, key: str) -> bool:
        """
        Start a single watcher with try/except protection.

        Returns True if started successfully, False otherwise.
        """
        watcher = self.state.watchers.get(key)
        if not watcher:
            logger.error(f"Unknown watcher: {key}")
            return False

        try:
            logger.info(f"[{watcher.name}] Starting watcher...")
            watcher.status = WatcherStatus.STARTING

            # Check if script exists
            if not watcher.script_path.exists():
                raise FileNotFoundError(f"Watcher script not found: {watcher.script_path}")

            # Build command
            python_cmd = "python3" if sys.version_info >= (3, 0) else "python"
            cmd = [python_cmd, str(watcher.script_path)]

            # Start the process
            log_file = LOGS_DIR / f"{key}_watcher.log"
            with open(log_file, 'a', encoding='utf-8') as f:
                process = subprocess.Popen(
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    preexec_fn=os.setsid
                )

            watcher.process = process
            watcher.pid = process.pid
            watcher.status = WatcherStatus.ACTIVE
            watcher.start_time = datetime.now()
            watcher.error_message = ""

            # Verify process is running
            time.sleep(2)
            if process.poll() is not None:
                # Process exited immediately
                raise RuntimeError(f"Watcher exited immediately with code: {process.returncode}")

            logger.info(f"[{watcher.name}] Started successfully (PID: {watcher.pid})")
            return True

        except FileNotFoundError as e:
            watcher.status = WatcherStatus.OFFLINE
            watcher.error_message = f"Script not found: {e}"
            logger.error(f"[{watcher.name}] FAILED - {watcher.error_message}")
            return False

        except PermissionError as e:
            watcher.status = WatcherStatus.OFFLINE
            watcher.error_message = f"Permission denied: {e}"
            logger.error(f"[{watcher.name}] FAILED - {watcher.error_message}")
            return False

        except Exception as e:
            watcher.status = WatcherStatus.OFFLINE
            watcher.error_message = str(e)
            logger.error(f"[{watcher.name}] FAILED - {watcher.error_message}")
            return False

    def _stop_watcher(self, key: str) -> bool:
        """Stop a single watcher gracefully."""
        watcher = self.state.watchers.get(key)
        if not watcher:
            return False

        try:
            if watcher.process and watcher.pid:
                logger.info(f"[{watcher.name}] Stopping watcher (PID: {watcher.pid})...")

                # Send SIGTERM
                os.killpg(os.getpgid(watcher.pid), signal.SIGTERM)

                # Wait for graceful shutdown
                try:
                    watcher.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if not stopped
                    os.killpg(os.getpgid(watcher.pid), signal.SIGKILL)
                    watcher.process.wait()

                watcher.status = WatcherStatus.STOPPED
                logger.info(f"[{watcher.name}] Stopped successfully")
                return True

        except ProcessLookupError:
            # Process already dead
            watcher.status = WatcherStatus.STOPPED
            logger.info(f"[{watcher.name}] Already stopped")
            return True

        except Exception as e:
            logger.error(f"[{watcher.name}] Error stopping: {e}")
            watcher.status = WatcherStatus.OFFLINE
            return False

        return False

    def _check_watcher_health(self, key: str) -> bool:
        """Check if a watcher is still running."""
        watcher = self.state.watchers.get(key)
        if not watcher or not watcher.process:
            return False

        # Check if process is still running
        if watcher.process.poll() is not None:
            # Process has exited
            if watcher.status == WatcherStatus.ACTIVE:
                logger.warning(f"[{watcher.name}] Process exited unexpectedly (code: {watcher.process.returncode})")
                watcher.status = WatcherStatus.OFFLINE
                watcher.error_message = f"Process exited with code: {watcher.process.returncode}"
            return False

        return True

    def _monitor_watchers(self):
        """Background thread to monitor watcher health."""
        while not self._stop_status_thread.is_set():
            try:
                for key in self.state.watchers:
                    watcher = self.state.watchers[key]
                    if watcher.status == WatcherStatus.ACTIVE:
                        if not self._check_watcher_health(key):
                            logger.warning(f"[{watcher.name}] Detected failure, marking OFFLINE")

                # Update dashboard periodically
                self._update_dashboard()

            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")

            self._stop_status_thread.wait(5)  # Check every 5 seconds

    def _update_dashboard(self):
        """Update Dashboard.md with current watcher status."""
        try:
            if not DASHBOARD_FILE.exists():
                return

            with open(DASHBOARD_FILE, 'r', encoding='utf-8') as f:
                content = f.read()

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Update watcher status section
            status_lines = []
            active_count = 0
            offline_count = 0

            for key, watcher in self.state.watchers.items():
                status_icon = "🟢" if watcher.status == WatcherStatus.ACTIVE else "🔴"
                status_lines.append(f"- {status_icon} **{watcher.name}**: `{watcher.status.value}`")
                if watcher.status == WatcherStatus.ACTIVE:
                    active_count += 1
                else:
                    offline_count += 1

            status_section = "\n".join(status_lines)

            # Find and replace watcher status section
            start_marker = "<!-- AI_PARSE_START: Watcher_Status -->"
            end_marker = "<!-- AI_PARSE_END: Watcher_Status -->"

            if start_marker in content and end_marker in content:
                new_status_block = f"\n{start_marker}\n{status_section}\n{end_marker}\n"
                start_idx = content.find(start_marker)
                end_idx = content.find(end_marker) + len(end_marker)
                content = content[:start_idx] + new_status_block + content[end_idx:]

            # Update metrics table
            metrics_start = "<!-- AI_PARSE_START: Metrics -->"
            metrics_end = "<!-- AI_PARSE_END: Metrics -->"

            if metrics_start in content and metrics_end in content:
                content = content.replace(
                    '| Watcher Status | `ACTIVE` |',
                    f'| Watcher Status | `{"DEGRADED" if offline_count > 0 else "ACTIVE"}` |'
                )
                content = re.sub(
                    r'\| Active Watchers \| `\d+` \|',
                    f'| Active Watchers | `{active_count}` |',
                    content
                )
                content = re.sub(
                    r'\| Offline Watchers \| `\d+` \|',
                    f'| Offline Watchers | `{offline_count}` |',
                    content
                )

            with open(DASHBOARD_FILE, 'w', encoding='utf-8') as f:
                f.write(content)

        except Exception as e:
            logger.error(f"Failed to update dashboard: {e}")

    def start_all_watchers(self) -> Dict[str, bool]:
        """
        Start all watchers with graceful degradation.

        If one watcher fails, continue starting others.
        Returns a dict of watcher keys to success status.
        """
        results = {}

        logger.info("=" * 60)
        logger.info("Starting all watchers with Gold Tier resilience...")
        logger.info("=" * 60)

        for key in self.state.watchers:
            try:
                success = self._start_watcher(key)
                results[key] = success
            except Exception as e:
                logger.error(f"[{key}] Unexpected error during startup: {e}")
                self.state.watchers[key].status = WatcherStatus.OFFLINE
                self.state.watchers[key].error_message = str(e)
                results[key] = False

        # Log summary
        active_count = sum(1 for w in self.state.watchers.values() if w.status == WatcherStatus.ACTIVE)
        total_count = len(self.state.watchers)

        logger.info("-" * 60)
        logger.info(f"Watcher startup complete: {active_count}/{total_count} active")

        if active_count < total_count:
            logger.warning("SYSTEM RUNNING IN DEGRADED MODE")
            for key, watcher in self.state.watchers.items():
                if watcher.status != WatcherStatus.ACTIVE:
                    logger.warning(f"  - {watcher.name}: {watcher.error_message}")
        else:
            logger.info("All watchers started successfully")

        logger.info("=" * 60)

        return results

    def stop_all_watchers(self):
        """Stop all watchers gracefully."""
        logger.info("Initiating graceful shutdown of all watchers...")

        for key in self.state.watchers:
            try:
                self._stop_watcher(key)
            except Exception as e:
                logger.error(f"[{key}] Error during shutdown: {e}")

        # Stop monitoring thread
        self._stop_status_thread.set()
        if self._status_update_thread:
            self._status_update_thread.join(timeout=5)

        logger.info("All watchers stopped. Goodbye!")

    def get_status_summary(self) -> str:
        """Get a formatted status summary of all watchers."""
        lines = [
            "",
            "=" * 50,
            "  External Watchers - Status",
            "=" * 50,
            ""
        ]

        for key, watcher in self.state.watchers.items():
            status_icon = "✓" if watcher.status == WatcherStatus.ACTIVE else "✗"
            pid_info = f"PID {watcher.pid}" if watcher.pid else "N/A"
            lines.append(f"  {watcher.name}: {status_icon} [{watcher.status.value}] ({pid_info})")
            if watcher.error_message:
                lines.append(f"    Error: {watcher.error_message}")

        lines.extend([
            "",
            f"  Active: {sum(1 for w in self.state.watchers.values() if w.status == WatcherStatus.ACTIVE)}/{len(self.state.watchers)}",
            ""
        ])

        return "\n".join(lines)

    def run(self):
        """Main run loop."""
        # Start health monitoring thread
        self._status_update_thread = Thread(target=self._monitor_watchers, daemon=True)
        self._status_update_thread.start()

        # Start all watchers
        self.start_all_watchers()

        # Show initial status
        print(self.get_status_summary())

        # Wait for shutdown signal
        try:
            while not self.state.shutdown_requested:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_all_watchers()


# Import re for dashboard updates
import re


# =============================================================================
# Signal Handlers
# =============================================================================

_manager: Optional[WatcherManager] = None


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    global _manager
    logger.info(f"Received signal {signum}, initiating shutdown...")
    if _manager:
        _manager.state.shutdown_requested = True


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for the watcher manager."""
    global _manager

    print("\n" + "=" * 60)
    print("  AI Employee Vault - Watcher Manager (Gold Tier)")
    print("=" * 60)
    print(f"  Base Directory: {BASE_DIR}")
    print(f"  Watchers Directory: {WATCHERS_DIR}")
    print(f"  Logs Directory: {LOGS_DIR}")
    print("=" * 60)

    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create and run manager
    _manager = WatcherManager()

    try:
        _manager.run()
    except Exception as e:
        logger.error(f"Fatal error in watcher manager: {e}")
        if _manager:
            _manager.stop_all_watchers()
        sys.exit(1)


if __name__ == "__main__":
    main()
