#!/usr/bin/env python3
"""
WhatsApp Agent - Gold Tier AI Employee

Autonomous agent that handles WhatsApp communication via Twilio.
Receives parsed WhatsApp tasks, communicates with planner agent,
waits for execution result, and sends automatic replies.

Flow:
    User WhatsApp Message → Twilio Webhook → WhatsApp Watcher → Inbox Task
    → Planner Agent → Skill Execution → WhatsApp Agent → Auto Reply

Requirements:
    pip install twilio python-dotenv requests

Usage:
    python Agents/whatsapp_agent.py

Stop:
    Press Ctrl+C to gracefully stop the agent
"""

import os
import sys
import re
import json
import time
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Set, Tuple
from dataclasses import dataclass, field
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.parent.resolve()

# Centralized vault path - all Obsidian vault folders are relative to this
VAULT_PATH = BASE_DIR / "notes"

CONFIG_DIR = BASE_DIR / "Config"
INBOX_DIR = VAULT_PATH / "Inbox"
NEEDS_ACTION_DIR = VAULT_PATH / "Needs_Action"
DONE_DIR = VAULT_PATH / "Done"
LOGS_DIR = BASE_DIR / "Logs"
CONFIG_FILE = CONFIG_DIR / "twilio_config.json"

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Polling interval in seconds
POLL_INTERVAL = 5

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to both file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"whatsapp_agent_{datetime.now().strftime('%Y-%m-%d')}.log"

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
    return logging.getLogger("WhatsAppAgent")


logger = setup_logging()


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class WhatsAppMessage:
    """Represents a WhatsApp message from task metadata."""
    sender: str
    message_body: str
    timestamp: str
    task_file: Path
    task_id: str = ""
    status: str = "pending"


@dataclass
class ExecutionResult:
    """Result from task execution."""
    success: bool
    summary: str
    details: str = ""
    error_message: str = ""
    completed_at: str = ""


@dataclass
class TwilioConfig:
    """Twilio configuration holder."""
    account_sid: str = ""
    auth_token: str = ""
    whatsapp_number: str = ""
    webhook_host: str = "127.0.0.1"
    webhook_port: int = 5000
    auto_reply: bool = True
    reply_on_complete: bool = True
    reply_on_failure: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 30


# =============================================================================
# WhatsApp Agent Class
# =============================================================================

class WhatsAppAgent:
    """
    WhatsApp Agent for Gold Tier AI Employee.

    Responsibilities:
    - Monitor completed WhatsApp tasks in Done folder
    - Read execution results
    - Send automatic replies via Twilio WhatsApp API
    - Handle failures with retry logic
    - Log all communication
    """

    def __init__(self):
        self.config = self._load_config()
        self.twilio_client: Optional[Client] = None
        self.processed_tasks: Set[str] = set()
        self.retry_queue: Dict[str, Tuple[WhatsAppMessage, int]] = {}  # task_id -> (message, retry_count)
        
        # Initialize Twilio client if credentials available
        self._init_twilio_client()

    def _load_config(self) -> TwilioConfig:
        """Load Twilio configuration from config file."""
        config = TwilioConfig()

        if not CONFIG_FILE.exists():
            logger.warning(f"Twilio config file not found: {CONFIG_FILE}")
            logger.warning("Running without Twilio integration")
            return config

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                raw_config = json.load(f)

            # Load credentials from environment variables (secure)
            config.account_sid = os.getenv("TWILIO_ACCOUNT_SID", raw_config.get("account_sid", ""))
            config.auth_token = os.getenv("TWILIO_AUTH_TOKEN", raw_config.get("auth_token", ""))
            config.whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER", raw_config.get("whatsapp_number", ""))

            # Load webhook settings
            webhook_config = raw_config.get("webhook", {})
            config.webhook_host = webhook_config.get("host", "127.0.0.1")
            config.webhook_port = webhook_config.get("port", 5000)

            # Load settings
            settings = raw_config.get("settings", {})
            config.auto_reply = settings.get("auto_reply", True)
            config.reply_on_complete = settings.get("reply_on_complete", True)
            config.reply_on_failure = settings.get("reply_on_failure", True)
            config.max_retries = settings.get("max_retries", 3)
            config.retry_delay_seconds = settings.get("retry_delay_seconds", 30)

            logger.info("Twilio configuration loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load Twilio config: {e}")

        return config

    def _init_twilio_client(self):
        """Initialize Twilio client if credentials are available."""
        if not self.config.account_sid or not self.config.auth_token:
            logger.warning("Twilio credentials not configured - running in demo mode")
            return

        try:
            self.twilio_client = Client(self.config.account_sid, self.config.auth_token)
            # Test connection
            self.twilio_client.api.accounts(self.config.account_sid).fetch()
            logger.info("Twilio client initialized successfully")
            logger.info(f"WhatsApp number: {self.config.whatsapp_number}")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            self.twilio_client = None

    def _format_whatsapp_number(self, number: str) -> str:
        """Format phone number for WhatsApp (whatsapp:+1234567890)."""
        # Remove any existing 'whatsapp:' prefix
        number = number.replace('whatsapp:', '')
        # Remove spaces, dashes, parentheses
        number = re.sub(r'[\s\-\(\)]', '', number)
        # Ensure it starts with +
        if not number.startswith('+'):
            # Assume US number if no country code
            if number.startswith('1'):
                number = '+' + number
            else:
                number = '+1' + number
        return f"whatsapp:{number}"

    def _extract_sender_from_task(self, content: str, frontmatter: Dict) -> Optional[str]:
        """Extract sender phone number from task content."""
        # Check frontmatter first
        sender = frontmatter.get('sender', '')
        if sender:
            return self._format_whatsapp_number(sender)

        # Check content for sender pattern
        sender_match = re.search(r'\*\*Sender:\*\*\s*(\+?\d[\d\-\s\(\)]+)', content)
        if sender_match:
            return self._format_whatsapp_number(sender_match.group(1))

        # Check for contact field
        contact = frontmatter.get('contact', '')
        if contact:
            # Contact might be a name, try to find number in content
            number_match = re.search(r'(\+?\d{10,15})', content)
            if number_match:
                return self._format_whatsapp_number(number_match.group(1))

        return None

    def _parse_task_file(self, task_file: Path) -> Optional[WhatsAppMessage]:
        """Parse WhatsApp task file and extract message data."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
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

            # Check if this is a WhatsApp task
            source = frontmatter.get('source', '').lower()
            if 'whatsapp' not in source:
                return None

            # Extract sender
            sender = self._extract_sender_from_task(content, frontmatter)
            if not sender:
                logger.warning(f"No sender found in task: {task_file.name}")
                return None

            # Extract original message
            message_body = frontmatter.get('message', '')
            if not message_body:
                # Try to find message in content
                msg_match = re.search(r'## Message Content\s*\n(.*?)(?=---|\n##|\Z)', content, re.DOTALL)
                if msg_match:
                    message_body = msg_match.group(1).strip()

            # Extract timestamp
            timestamp = frontmatter.get('created', frontmatter.get('timestamp', datetime.now().isoformat()))

            return WhatsAppMessage(
                sender=sender,
                message_body=message_body,
                timestamp=timestamp,
                task_file=task_file,
                task_id=task_file.stem
            )

        except Exception as e:
            logger.error(f"Failed to parse task file {task_file.name}: {e}")
            return None

    def _extract_execution_result(self, task_file: Path) -> ExecutionResult:
        """Extract execution result from completed task file."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for execution result section
            result_match = re.search(
                r'## Execution Result\s*\n(.*?)(?=---|\n##|\Z)',
                content,
                re.DOTALL
            )

            if result_match:
                result_text = result_match.group(1).strip()

                # Determine success/failure
                success = '✅' in result_text or 'Success' in result_text or 'completed' in result_text.lower()
                if '❌' in result_text or 'Failed' in result_text or 'Error' in result_text:
                    success = False

                # Extract summary
                summary_match = re.search(r'\*\*Summary:\*\*\s*(.+)', result_text)
                summary = summary_match.group(1).strip() if summary_match else result_text[:200]

                return ExecutionResult(
                    success=success,
                    summary=summary,
                    details=result_text,
                    completed_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )

            # Check for generic completion markers
            if '## Completion' in content or 'Status: done' in content or 'Status:completed' in content:
                return ExecutionResult(
                    success=True,
                    summary="Task completed successfully",
                    details="Task processed by AI Employee system",
                    completed_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )

            # Default: assume completed if in Done folder
            return ExecutionResult(
                success=True,
                summary="Task processed",
                details="Task completed by AI Employee",
                completed_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )

        except Exception as e:
            logger.error(f"Failed to extract execution result: {e}")
            return ExecutionResult(
                success=False,
                summary="Failed to read execution result",
                error_message=str(e)
            )

    def send_whatsapp_message(self, to_number: str, body: str) -> bool:
        """
        Send WhatsApp message via Twilio.

        Args:
            to_number: Recipient number in whatsapp:+1234567890 format
            body: Message body text

        Returns:
            True if message sent successfully, False otherwise
        """
        if not self.twilio_client:
            logger.info(f"[DEMO MODE] Would send to {to_number}: {body[:100]}...")
            return True

        try:
            from_number = self._format_whatsapp_number(self.config.whatsapp_number)

            message = self.twilio_client.messages.create(
                from_=from_number,
                body=body,
                to=to_number
            )

            logger.info(f"WhatsApp message sent: {message.sid}")
            return True

        except TwilioRestException as e:
            logger.error(f"Twilio API error: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            return False

    def _format_success_reply(self, result: ExecutionResult) -> str:
        """Format success reply message."""
        return f"""✅ Task Completed

Result:
{result.summary}

Your AI Employee has processed your request.
"""

    def _format_failure_reply(self, result: ExecutionResult) -> str:
        """Format failure reply message."""
        return f"""⚠️ Task Failed

{result.summary}

AI Employee is retrying your request.
Please stand by.
"""

    def send_reply(self, message: WhatsAppMessage, result: ExecutionResult) -> bool:
        """
        Send reply to WhatsApp user based on execution result.

        Args:
            message: Original WhatsApp message
            result: Execution result

        Returns:
            True if reply sent successfully
        """
        if not self.config.auto_reply:
            logger.info("Auto-reply disabled in config")
            return False

        # Format reply based on result
        if result.success:
            if not self.config.reply_on_complete:
                logger.info("Reply on complete disabled in config")
                return False
            body = self._format_success_reply(result)
        else:
            if not self.config.reply_on_failure:
                logger.info("Reply on failure disabled in config")
                return False
            body = self._format_failure_reply(result)

        # Send message
        success = self.send_whatsapp_message(message.sender, body)

        if success:
            self._log_reply(message, result, success=True)
        else:
            self._log_reply(message, result, success=False)

        return success

    def _log_reply(self, message: WhatsAppMessage, result: ExecutionResult, success: bool):
        """Log reply to activity log."""
        log_file = LOGS_DIR / f"whatsapp_replies_{datetime.now().strftime('%Y-%m-%d')}.md"

        log_entry = f"""
---

## Reply Log

**Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Task:** {message.task_id}
**Sender:** {message.sender}
**Original Message:** {message.message_body[:100]}...
**Result:** {'Success' if result.success else 'Failed'}
**Reply Sent:** {'✅ Yes' if success else '❌ No'}

"""
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to log reply: {e}")

    def scan_done_folder(self) -> List[Path]:
        """Scan Done folder for completed WhatsApp tasks."""
        completed_tasks = []

        if not DONE_DIR.exists():
            return completed_tasks

        for file_path in DONE_DIR.iterdir():
            if (file_path.is_file() and
                file_path.suffix.lower() == '.md' and
                file_path.stem not in self.processed_tasks):
                completed_tasks.append(file_path)

        return completed_tasks

    def scan_needs_action_folder(self) -> List[Path]:
        """Scan Needs_Action folder for WhatsApp tasks to track."""
        whatsapp_tasks = []

        if not NEEDS_ACTION_DIR.exists():
            return whatsapp_tasks

        for file_path in NEEDS_ACTION_DIR.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.md':
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if 'source: WhatsApp' in content or 'Source: WhatsApp' in content:
                        whatsapp_tasks.append(file_path)
                except Exception:
                    pass

        return whatsapp_tasks

    def process_completed_task(self, task_file: Path):
        """Process a completed WhatsApp task and send reply."""
        logger.info(f"Processing completed task: {task_file.name}")

        # Parse task
        message = self._parse_task_file(task_file)
        if not message:
            logger.warning(f"Invalid WhatsApp task: {task_file.name}")
            return

        # Extract execution result
        result = self._extract_execution_result(task_file)

        # Send reply
        reply_sent = self.send_reply(message, result)

        if reply_sent:
            self.processed_tasks.add(task_file.stem)
            logger.info(f"Reply sent for task: {task_file.name}")
        else:
            # Add to retry queue
            if task_file.stem not in self.retry_queue:
                self.retry_queue[task_file.stem] = (message, 0)
            logger.warning(f"Failed to send reply for task: {task_file.name}")

    def process_retry_queue(self):
        """Process retry queue for failed replies."""
        to_remove = []

        for task_id, (message, retry_count) in self.retry_queue.items():
            if retry_count >= self.config.max_retries:
                logger.error(f"Max retries reached for task: {task_id}")
                to_remove.append(task_id)
                continue

            # Check if enough time has passed
            retry_count += 1
            self.retry_queue[task_id] = (message, retry_count)

            # Re-extract result and retry
            result = self._extract_execution_result(message.task_file)
            reply_sent = self.send_reply(message, result)

            if reply_sent:
                self.processed_tasks.add(task_id)
                to_remove.append(task_id)
                logger.info(f"Retry successful for task: {task_id}")

        for task_id in to_remove:
            del self.retry_queue[task_id]

    def run(self):
        """Main agent loop."""
        logger.info("=" * 60)
        logger.info("WhatsApp Agent Starting...")
        logger.info(f"Inbox: {INBOX_DIR}")
        logger.info(f"Done: {DONE_DIR}")
        logger.info(f"Poll Interval: {POLL_INTERVAL}s")
        logger.info(f"Twilio Configured: {self.twilio_client is not None}")
        logger.info(f"Auto-Reply: {self.config.auto_reply}")
        logger.info("=" * 60)

        if not self.twilio_client:
            logger.warning("Running in DEMO MODE - no actual messages will be sent")
            logger.warning("Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN to enable")

        while True:
            try:
                # Process completed tasks
                completed_tasks = self.scan_done_folder()
                for task_file in completed_tasks:
                    self.process_completed_task(task_file)

                # Process retry queue
                self.process_retry_queue()

                # Wait for next poll
                time.sleep(POLL_INTERVAL)

            except KeyboardInterrupt:
                logger.info("WhatsApp Agent stopping...")
                break
            except Exception as e:
                logger.error(f"Error in WhatsApp agent loop: {e}")
                time.sleep(POLL_INTERVAL)


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    agent = WhatsAppAgent()
    agent.run()
