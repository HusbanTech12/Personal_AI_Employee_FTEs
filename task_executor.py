#!/usr/bin/env python3
"""
AI Employee Task Executor - Full Workflow Engine

Enforces complete execution pipeline for every task:
Watcher → Inbox → Needs_Action → task_executor → Skill → AI Response → Approval → Done

CRITICAL: Every task from clients MUST go through full execution.

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
from typing import Dict, Optional, List, Tuple
from enum import Enum
from dataclasses import dataclass, field
from dotenv import load_dotenv

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.resolve()
VAULT_PATH = BASE_DIR / "notes"
SKILLS_PATH = BASE_DIR / "Skills"

INBOX_DIR = VAULT_PATH / "Inbox"
NEEDS_ACTION_DIR = VAULT_PATH / "Needs_Action"
IN_PROGRESS_DIR = VAULT_PATH / "In_Progress"
PENDING_APPROVAL_DIR = VAULT_PATH / "Pending_Approval"
DONE_DIR = VAULT_PATH / "Done"
UNCLASSIFIED_DIR = NEEDS_ACTION_DIR / "Unclassified"
LOGS_DIR = BASE_DIR / "Logs"

# Load client list configuration (fallback - deprecated)
CLIENT_LIST_FILE = BASE_DIR / "Config" / "client_list.env"
if CLIENT_LIST_FILE.exists():
    load_dotenv(dotenv_path=CLIENT_LIST_FILE)

# Load official accounts from .env (PRIMARY source)
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE, override=True)

# Official Accounts Filtering - PRIMARY FILTER (from .env)
OFFICIAL_FILTER_ENABLED = os.getenv("OFFICIAL_ACCOUNTS_FILTER_ENABLED", "true").lower() == "true"
LINKEDIN_OFFICIAL_ACCOUNTS = [c.strip().lower() for c in os.getenv("LINKEDIN_OFFICIAL_ACCOUNTS", "").split(",") if c.strip() and c.strip().upper() != "NONE"]
WHATSAPP_OFFICIAL_NUMBERS = [c.strip().lower() for c in os.getenv("WHATSAPP_OFFICIAL_NUMBERS", "").split(",") if c.strip() and c.strip().upper() != "NONE"]
GMAIL_OFFICIAL_ACCOUNTS = [c.strip().lower() for c in os.getenv("GMAIL_OFFICIAL_ACCOUNTS", "").split(",") if c.strip() and c.strip().upper() != "NONE"]
LOG_IGNORED_MESSAGES = os.getenv("LOG_IGNORED_MESSAGES", "true").lower() == "true"
REJECT_NON_OFFICIAL = os.getenv("REJECT_NON_OFFICIAL", "true").lower() == "true"

# Client filtering configuration (FALLBACK - deprecated)
CLIENT_FILTER_ENABLED = os.getenv("CLIENT_FILTER_ENABLED", "false").lower() == "true"  # Disabled by default
LINKEDIN_CLIENTS = [c.strip().lower() for c in os.getenv("LINKEDIN_CLIENTS", "").split(",") if c.strip()]
WHATSAPP_CLIENTS = [c.strip().lower() for c in os.getenv("WHATSAPP_CLIENTS", "").split(",") if c.strip()]
GMAIL_CLIENTS = [c.strip().lower() for c in os.getenv("GMAIL_CLIENTS", "").split(",") if c.strip()]

# Approval configuration
HUMAN_APPROVAL_REQUIRED = os.getenv("HUMAN_APPROVAL_REQUIRED", "true").lower() == "true"

VALID_EXTENSIONS = {'.md'}
IGNORED_EXTENSIONS = {'.tmp', '.part', '.swp', '.bak', '.crdownload'}

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Enums and Data Classes
# =============================================================================

class TaskStatus(Enum):
    """Task lifecycle states."""
    PENDING = "pending"
    STARTED = "started"
    IN_PROGRESS = "in_progress"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    UNCLASSIFIED = "unclassified"
    PENDING_APPROVAL = "pending_approval"


class ExecutionResult(Enum):
    """Execution outcome."""
    SUCCESS = "success"
    FAILED = "failed"
    SKILL_NOT_FOUND = "skill_not_found"
    PARTIAL = "partial"


@dataclass
class Task:
    """Represents a task to be executed."""
    filename: str
    file_path: Path
    content: str = ""
    metadata: Dict[str, str] = field(default_factory=dict)
    task_type: str = ""
    priority: str = "standard"
    source: str = ""
    sender: str = ""
    action_items: List[str] = field(default_factory=list)
    skill_required: str = ""
    skill_file: Optional[Path] = None
    status: TaskStatus = TaskStatus.PENDING
    execution_output: Dict[str, str] = field(default_factory=dict)
    ai_response: str = ""
    error_message: str = ""


# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging():
    """Configure logging to both file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"executor_{datetime.now().strftime('%Y-%m-%d')}.log"

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
# YAML Parser
# =============================================================================

def parse_yaml_frontmatter(content: str) -> Dict[str, str]:
    """Parse YAML frontmatter from markdown content."""
    metadata = {}

    if not content.strip().startswith('---'):
        return metadata

    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not frontmatter_match:
        return metadata

    frontmatter = frontmatter_match.group(1)

    for line in frontmatter.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            metadata[key.strip()] = value.strip()

    return metadata


def extract_action_items(content: str) -> List[str]:
    """Extract action items from task content."""
    action_items = []

    # Look for checklist items
    checklist_pattern = r'^-\s*\[\s*\]\s*(.+)$'
    for match in re.finditer(checklist_pattern, content, re.MULTILINE):
        action_items.append(match.group(1).strip())

    return action_items


# =============================================================================
# Client Filter
# =============================================================================

class ClientFilter:
    """Filters tasks based on official accounts list (PRIMARY) and client list (FALLBACK)."""

    @staticmethod
    def is_official_account_task(metadata: Dict[str, str]) -> bool:
        """
        Check if a task is from an official account.
        Returns True if OFFICIAL_FILTER_ENABLED is False or sender matches an official account.
        """
        if not OFFICIAL_FILTER_ENABLED:
            # Fallback to old client filter if official filter disabled
            if CLIENT_FILTER_ENABLED:
                return ClientFilter.is_client_task(metadata)
            return True

        source = metadata.get('source', '').lower()
        sender = metadata.get('sender', '').lower()

        # LinkedIn check
        if 'linkedin' in source:
            if not LINKEDIN_OFFICIAL_ACCOUNTS:
                logger.warning("[OFFICIAL_FILTER] LinkedIn official accounts empty - REJECTING ALL")
                return False
            for official in LINKEDIN_OFFICIAL_ACCOUNTS:
                if official in sender or sender in official:
                    return True
            if LOG_IGNORED_MESSAGES:
                logger.info(f"[OFFICIAL_FILTER] ⚠️  IGNORED non-official LinkedIn: {sender}")
                logger.info(f"[OFFICIAL_FILTER]   Official: {LINKEDIN_OFFICIAL_ACCOUNTS}")
            return False

        # WhatsApp check
        if 'whatsapp' in source:
            if not WHATSAPP_OFFICIAL_NUMBERS:
                logger.warning("[OFFICIAL_FILTER] WhatsApp official numbers empty - REJECTING ALL")
                return False
            sender_clean = sender.replace('whatsapp:', '')
            for official in WHATSAPP_OFFICIAL_NUMBERS:
                if official in sender_clean or sender_clean in official:
                    return True
            if LOG_IGNORED_MESSAGES:
                logger.info(f"[OFFICIAL_FILTER] ⚠️  IGNORED non-official WhatsApp: {sender}")
                logger.info(f"[OFFICIAL_FILTER]   Official: {WHATSAPP_OFFICIAL_NUMBERS}")
            return False

        # Gmail check
        if 'gmail' in source or 'email' in source:
            if not GMAIL_OFFICIAL_ACCOUNTS:
                logger.warning("[OFFICIAL_FILTER] Gmail official accounts empty - REJECTING ALL")
                return False
            for official in GMAIL_OFFICIAL_ACCOUNTS:
                if official.startswith('@'):
                    if official in sender:
                        return True
                elif official == sender or official in sender:
                    return True
            if LOG_IGNORED_MESSAGES:
                logger.info(f"[OFFICIAL_FILTER] ⚠️  IGNORED non-official Gmail: {sender}")
                logger.info(f"[OFFICIAL_FILTER]   Official: {GMAIL_OFFICIAL_ACCOUNTS}")
            return False

        # Unknown source - reject for security
        if LOG_IGNORED_MESSAGES:
            logger.warning(f"[OFFICIAL_FILTER] ⚠️  REJECTED unknown source type: {source}")
        return False

    @staticmethod
    def is_client_task(metadata: Dict[str, str]) -> bool:
        """Fallback client filter (deprecated - use official accounts)."""
        if not CLIENT_FILTER_ENABLED:
            return True

        source = metadata.get('source', '').lower()
        sender = metadata.get('sender', '').lower()

        # LinkedIn check
        if 'linkedin' in source:
            if not LINKEDIN_CLIENTS:
                return False
            for client in LINKEDIN_CLIENTS:
                if client in sender or sender in client:
                    return True
            return False

        # WhatsApp check
        if 'whatsapp' in source:
            if not WHATSAPP_CLIENTS:
                return False
            sender_clean = sender.replace('whatsapp:', '')
            for client in WHATSAPP_CLIENTS:
                if client in sender_clean or sender_clean in client:
                    return True
            return False

        # Gmail check
        if 'gmail' in source or 'email' in source:
            if not GMAIL_CLIENTS:
                return False
            for client in GMAIL_CLIENTS:
                if client.startswith('@'):
                    if client in sender:
                        return True
                elif client == sender or client in sender:
                    return True
            return False

        return False


# =============================================================================
# AI Response Generator
# =============================================================================

class AIResponseGenerator:
    """Generates AI responses based on source and task type."""

    @staticmethod
    def generate_response(task: Task) -> str:
        """Generate AI response based on source type."""
        source = task.source.lower()

        if 'linkedin' in source:
            return AIResponseGenerator._generate_linkedin_response(task)
        elif 'whatsapp' in source:
            return AIResponseGenerator._generate_whatsapp_response(task)
        elif 'gmail' in source or 'email' in source:
            return AIResponseGenerator._generate_email_response(task)
        else:
            return AIResponseGenerator._generate_generic_response(task)

    @staticmethod
    def _generate_linkedin_response(task: Task) -> str:
        """Generate LinkedIn response."""
        sender = task.sender or "Connection"
        task_type = task.task_type or "message"

        if task_type == 'connection_request':
            return f"""Hi {sender.split()[-1] if ' ' in sender else sender},

Thank you for the connection request! I'd be happy to connect and expand our professional networks.

I'm always interested in connecting with fellow professionals and exploring potential collaborations.

Best regards,
AI Employee Vault"""

        elif task_type == 'inmail':
            return f"""Hi {sender},

Thank you for reaching out via LinkedIn InMail. I appreciate you taking the time to contact me.

I've reviewed your message and would be happy to discuss further. Please feel free to share more details about how we might work together.

Looking forward to hearing from you.

Best regards,
AI Employee Vault"""

        elif task_type == 'job_posting':
            return f"""Dear Hiring Team,

Thank you for sharing this opportunity. The position sounds interesting and aligns well with professional growth goals.

I would appreciate more details about:
- Role responsibilities and expectations
- Team structure and culture
- Growth opportunities within the organization

Please let me know the next steps in the application process.

Best regards,
AI Employee Vault"""

        else:
            return f"""Hi {sender},

Thank you for reaching out on LinkedIn. I appreciate you taking the time to connect.

I'd be happy to learn more about your work and explore potential synergies between our professional networks.

Best regards,
AI Employee Vault"""

    @staticmethod
    def _generate_whatsapp_response(task: Task) -> str:
        """Generate WhatsApp response."""
        sender = task.sender or "Contact"
        message_content = ""

        # Extract message content from task
        if "## Message Content" in task.content:
            parts = task.content.split("## Message Content")
            if len(parts) > 1:
                message_section = parts[1].split("---")[0].strip()
                message_content = message_section.split("\n", 1)[-1].strip() if "\n" in message_section else message_section

        message_lower = message_content.lower() if message_content else ""
        contact_name = sender.split()[0] if ' ' in sender else sender

        if "urgent" in message_lower:
            return f"""Hi {contact_name},

I received your urgent message and understand the priority. I'm looking into this right now and will get back to you shortly with an update.

Best regards"""

        elif "status" in message_lower or "update" in message_lower:
            return f"""Hi {contact_name},

Thanks for reaching out. I'm preparing the status update you requested and will send it over as soon as it's ready.

I'll include all relevant details for your meeting.

Best regards"""

        elif "call" in message_lower or "phone" in message_lower:
            return f"""Hi {contact_name},

Got your message about calling. I'm available and will give you a call soon.

Is there a specific time that works best for you?

Best regards"""

        else:
            return f"""Hi {contact_name},

Thanks for your message. I appreciate you reaching out.

I'll get back to you with more details soon.

Best regards"""

    @staticmethod
    def _generate_email_response(task: Task) -> str:
        """Generate email response."""
        sender = task.sender or "Sender"
        subject = task.metadata.get('subject', task.metadata.get('title', 'No Subject'))

        sender_name = sender.split('@')[0] if '@' in sender else sender

        return f"""Dear {sender_name},

Thank you for your email. I appreciate you reaching out regarding "{subject}".

I've reviewed your message and wanted to follow up with you. Please let me know if you need any additional information or clarification from my end.

I look forward to hearing from you soon.

Best regards,
AI Employee Vault"""

    @staticmethod
    def _generate_generic_response(task: Task) -> str:
        """Generate generic response."""
        return f"""Thank you for your message.

I have received your request and will process it accordingly.

Best regards,
AI Employee Vault"""


# =============================================================================
# Skill Selector
# =============================================================================

class SkillSelector:
    """Selects appropriate skill based on task source and type."""

    @staticmethod
    def select_skill(task: Task) -> Tuple[str, Optional[Path]]:
        """
        Select skill based on task source.
        - LinkedIn/WhatsApp → social_handler (or task_processor as fallback)
        - Other → task_processor
        """
        source = task.source.lower()

        # LinkedIn or WhatsApp → social_handler
        if 'linkedin' in source or 'whatsapp' in source:
            # Try social_handler first
            social_handler_path = SKILLS_PATH / "social_handler.SKILL.md"
            if social_handler_path.exists():
                logger.info(f"Skill selected: social_handler (for {source})")
                return "social_handler", social_handler_path

            # Fallback to task_processor
            task_processor_path = SKILLS_PATH / "task_processor.SKILL.md"
            if task_processor_path.exists():
                logger.info(f"Skill selected: task_processor (fallback for {source})")
                return "task_processor", task_processor_path

        # Default → task_processor
        task_processor_path = SKILLS_PATH / "task_processor.SKILL.md"
        if task_processor_path.exists():
            logger.info(f"Skill selected: task_processor (default)")
            return "task_processor", task_processor_path

        logger.warning("No skill file found - using built-in execution")
        return "built_in", None


# =============================================================================
# Execution Engine
# =============================================================================

class ExecutionEngine:
    """Executes tasks with full workflow enforcement."""

    def __init__(self, in_progress_dir: Path, pending_approval_dir: Path):
        self.in_progress_dir = in_progress_dir
        self.pending_approval_dir = pending_approval_dir
        self.response_generator = AIResponseGenerator()
        self.skill_selector = SkillSelector()

    def execute_task(self, task: Task) -> ExecutionResult:
        """
        Execute a task with full workflow:
        1. Move to In_Progress/task_executor/
        2. Parse task content
        3. Select skill
        4. Execute skill logic
        5. Generate AI response
        6. Write execution result
        7. Move to Pending_Approval or Done
        """
        logger.info(f"=" * 60)
        logger.info(f"EXECUTION STARTED: {task.filename}")
        logger.info(f"=" * 60)

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task.status = TaskStatus.STARTED

        # STEP 1: Move to In_Progress/task_executor/
        logger.info(f"STEP 1/7: Moving to In_Progress/task_executor/")
        task_executor_dir = self.in_progress_dir / "task_executor"
        task_executor_dir.mkdir(parents=True, exist_ok=True)

        in_progress_file = task_executor_dir / task.filename
        try:
            shutil.copy2(task.file_path, in_progress_file)
            logger.info(f"  → Task moved to: {in_progress_file}")
        except Exception as e:
            task.error_message = f"Failed to move to In_Progress: {str(e)}"
            logger.error(f"  ✗ {task.error_message}")
            task.status = TaskStatus.FAILED
            return ExecutionResult.FAILED

        # STEP 2: Parse task content
        logger.info(f"STEP 2/7: Parsing task content")
        try:
            with open(task.file_path, 'r', encoding='utf-8') as f:
                task.content = f.read()
            task.metadata = parse_yaml_frontmatter(task.content)
            task.action_items = extract_action_items(task.content)
            task.task_type = task.metadata.get('notification_type', 
                            task.metadata.get('message_type', 
                            task.metadata.get('type', 'general')))
            task.priority = task.metadata.get('priority', 'standard')
            task.source = task.metadata.get('source', 'unknown')
            task.sender = task.metadata.get('sender', 'Unknown')
            logger.info(f"  → Source: {task.source}")
            logger.info(f"  → Type: {task.task_type}")
            logger.info(f"  → Sender: {task.sender}")
            logger.info(f"  → Action items: {len(task.action_items)}")
        except Exception as e:
            task.error_message = f"Failed to parse task content: {str(e)}"
            logger.error(f"  ✗ {task.error_message}")
            task.status = TaskStatus.FAILED
            return ExecutionResult.FAILED

        # STEP 3: Select skill
        logger.info(f"STEP 3/7: Selecting skill")
        skill_id, skill_file = self.skill_selector.select_skill(task)
        task.skill_required = skill_id
        task.skill_file = skill_file
        logger.info(f"  → Skill: {skill_id}")

        # STEP 4: Execute skill logic
        logger.info(f"STEP 4/7: Executing skill logic")
        task.status = TaskStatus.EXECUTING

        # Execute based on skill type
        if skill_id == 'social_handler':
            execution_output = self._execute_social_handler(task)
        elif skill_id == 'task_processor':
            execution_output = self._execute_task_processor(task)
        else:
            execution_output = self._execute_built_in(task)

        if not execution_output.get('success', False):
            task.error_message = execution_output.get('error', 'Unknown execution error')
            logger.error(f"  ✗ Execution failed: {task.error_message}")
            task.status = TaskStatus.FAILED
            task.execution_output = execution_output
            return ExecutionResult.FAILED

        task.execution_output = execution_output
        logger.info(f"  → {execution_output.get('action_taken', 'Action completed')}")

        # STEP 5: Generate AI response
        logger.info(f"STEP 5/7: Generating AI response")
        task.ai_response = self.response_generator.generate_response(task)
        logger.info(f"  → AI response generated ({len(task.ai_response)} chars)")

        # STEP 6: Write execution result
        logger.info(f"STEP 6/7: Writing execution result")
        updated_content = self._add_execution_result(task.content, task.execution_output, task.ai_response)

        try:
            with open(in_progress_file, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            logger.info(f"  → Execution result written")
        except Exception as e:
            task.error_message = f"Failed to write execution result: {str(e)}"
            logger.error(f"  ✗ {task.error_message}")
            task.status = TaskStatus.FAILED
            return ExecutionResult.FAILED

        # STEP 7: Move to Pending_Approval or Done
        logger.info(f"STEP 7/7: Moving to final destination")
        
        if HUMAN_APPROVAL_REQUIRED:
            # Move to Pending_Approval
            approval_file = self.pending_approval_dir / f"approval_{task.filename}"
            approval_content = self._create_approval_file(task)
            
            try:
                with open(approval_file, 'w', encoding='utf-8') as f:
                    f.write(approval_content)
                logger.info(f"  → Moved to Pending_Approval: approval_{task.filename}")
                logger.info(f"  → Awaiting human approval")
                task.status = TaskStatus.PENDING_APPROVAL
            except Exception as e:
                task.error_message = f"Failed to create approval file: {str(e)}"
                logger.error(f"  ✗ {task.error_message}")
                task.status = TaskStatus.FAILED
                return ExecutionResult.FAILED
        else:
            # Move directly to Done
            done_file = DONE_DIR / task.filename
            try:
                shutil.copy2(in_progress_file, done_file)
                in_progress_file.unlink()  # Remove from In_Progress
                task.file_path.unlink()  # Remove from Needs_Action
                logger.info(f"  → Moved to Done: {task.filename}")
                task.status = TaskStatus.COMPLETED
            except Exception as e:
                task.error_message = f"Failed to move to Done: {str(e)}"
                logger.error(f"  ✗ {task.error_message}")
                task.status = TaskStatus.FAILED
                return ExecutionResult.FAILED

        logger.info(f"=" * 60)
        logger.info(f"EXECUTION COMPLETED: {task.filename}")
        logger.info(f"  Status: {task.status.value}")
        logger.info(f"  Skill: {task.skill_required}")
        logger.info(f"  Timestamp: {timestamp}")
        logger.info(f"=" * 60)

        return ExecutionResult.SUCCESS

    def _execute_social_handler(self, task: Task) -> Dict[str, str]:
        """Execute social handler skill (LinkedIn/WhatsApp)."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return {
            'success': 'true',
            'action_taken': f"Processed {task.source} {task.task_type} from {task.sender}",
            'skill_used': 'social_handler',
            'timestamp': timestamp,
            'source': task.source,
            'sender': task.sender,
            'response_type': f"{task.source}_reply"
        }

    def _execute_task_processor(self, task: Task) -> Dict[str, str]:
        """Execute task processor skill."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return {
            'success': 'true',
            'action_taken': f"Processed task: {task.task_type} from {task.sender}",
            'skill_used': 'task_processor',
            'timestamp': timestamp,
            'action_items_count': len(task.action_items)
        }

    def _execute_built_in(self, task: Task) -> Dict[str, str]:
        """Execute built-in handler (no skill file)."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return {
            'success': 'true',
            'action_taken': f"Processed task using built-in handler",
            'skill_used': 'built_in',
            'timestamp': timestamp
        }

    def _add_execution_result(self, content: str, execution_output: Dict[str, str], ai_response: str) -> str:
        """Add execution result and AI response to task content."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Update frontmatter status
        content = re.sub(
            r'^(status:\s*).+$',
            r'\1in_progress',
            content,
            flags=re.MULTILINE
        )

        # Build execution result section
        execution_section = f"""
---

## Execution Result

**Status:** {execution_output.get('success', 'unknown')}
**Action Taken:** {execution_output.get('action_taken', 'N/A')}
**Skill Used:** {execution_output.get('skill_used', 'N/A')}
**Timestamp:** {execution_output.get('timestamp', timestamp)}

---

## AI Response

{ai_response}

---
"""

        # Add execution result
        if "## Execution Result" in content:
            content = re.sub(
                r'## Execution Result.*?(?=---|$)',
                execution_section.strip().replace('---\n\n## Execution Result', '## Execution Result'),
                content,
                flags=re.DOTALL
            )
        else:
            content = content.rstrip() + execution_section

        return content

    def _create_approval_file(self, task: Task) -> str:
        """Create approval file content."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        return f"""---
title: Approval Required - {task.filename}
status: pending_approval
priority: {task.priority}
created: {timestamp}
source: {task.source}
sender: {task.sender}
skill_used: {task.skill_required}
---

# Approval Required

**Original Task:** {task.filename}
**Submitted:** {timestamp}
**Source:** {task.source}
**Sender:** {task.sender}

---

## AI-Generated Response

{task.ai_response}

---

## Execution Details

**Skill Used:** {task.skill_required}
**Action Taken:** {task.execution_output.get('action_taken', 'N/A')}
**Timestamp:** {task.execution_output.get('timestamp', timestamp)}

---

## Approval Decision

- [ ] **APPROVE** - Send response and move to Done
- [ ] **REJECT** - Send to Rejected folder
- [ ] **MODIFY** - Edit response above and re-approve

---

## Original Task Content

{task.content[:3000]}{'...' if len(task.content) > 3000 else ''}
"""


# =============================================================================
# Task Processor
# =============================================================================

class TaskProcessor:
    """Processes tasks from Needs_Action with full workflow enforcement."""

    def __init__(self, needs_action_dir: Path, in_progress_dir: Path,
                 pending_approval_dir: Path, done_dir: Path, 
                 unclassified_dir: Path, skills_path: Path):
        self.needs_action_dir = needs_action_dir
        self.in_progress_dir = in_progress_dir
        self.pending_approval_dir = pending_approval_dir
        self.done_dir = done_dir
        self.unclassified_dir = unclassified_dir
        self.skills_path = skills_path
        self.task_queue: Dict[str, TaskStatus] = {}
        self.queue_lock = Lock()
        self.execution_engine = ExecutionEngine(in_progress_dir, pending_approval_dir)

        # Track processed files to avoid duplicates
        self.processed_files: set = set()

    def ensure_directories(self):
        """Ensure all required directories exist."""
        for directory in [self.needs_action_dir, self.in_progress_dir,
                          self.pending_approval_dir, self.done_dir, 
                          self.unclassified_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    def scan_for_tasks(self) -> List[Path]:
        """Scan Needs_Action directory for pending tasks."""
        pending_tasks = []

        if not self.needs_action_dir.exists():
            return pending_tasks

        try:
            for file_path in self.needs_action_dir.iterdir():
                # Skip directories
                if file_path.is_dir():
                    continue

                # Skip ignored extensions
                if file_path.suffix.lower() in IGNORED_EXTENSIONS:
                    continue

                # Skip markdown files only
                if file_path.suffix.lower() not in VALID_EXTENSIONS:
                    continue

                # Skip Unclassified subdirectory
                if file_path.parent == self.unclassified_dir:
                    continue

                filename = file_path.name

                # Skip already processed files
                if filename in self.processed_files:
                    continue

                with self.queue_lock:
                    if filename not in self.task_queue:
                        self.task_queue[filename] = TaskStatus.PENDING
                        pending_tasks.append(file_path)
                        logger.info(f"New task detected: {filename}")
        except Exception as e:
            logger.error(f"Error scanning directory: {str(e)}")

        return pending_tasks

    def process_task(self, file_path: Path) -> bool:
        """
        Process a single task file with FULL workflow enforcement.
        
        WORKFLOW:
        1. Client filter check
        2. Execute full pipeline
        3. Move to Pending_Approval or Done
        """
        filename = file_path.name
        logger.info(f"")
        logger.info(f"{'=' * 70}")
        logger.info(f"TASK DETECTED: {filename}")
        logger.info(f"{'=' * 70}")

        try:
            # Read file to get metadata
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse metadata for client check
            metadata = parse_yaml_frontmatter(content)

            # OFFICIAL ACCOUNTS FILTER: Check if sender is official
            if metadata and not ClientFilter.is_official_account_task(metadata):
                if REJECT_NON_OFFICIAL:
                    logger.info(f"[OFFICIAL_FILTER] ✗ REJECTED non-official account task: {filename}")
                    return False
                else:
                    logger.warning(f"[OFFICIAL_FILTER] ⚠️  FLAGGED non-official task (not rejected): {filename}")

            # Create task object
            task = Task(
                filename=filename,
                file_path=file_path
            )
            task.metadata = metadata

            # EXECUTE FULL WORKFLOW
            result = self.execution_engine.execute_task(task)

            # Mark as processed
            with self.queue_lock:
                self.task_queue[filename] = task.status
                self.processed_files.add(filename)

            if result == ExecutionResult.SUCCESS:
                logger.info(f"{'=' * 70}")
                logger.info(f"TASK COMPLETED SUCCESSFULLY: {filename}")
                logger.info(f"{'=' * 70}")
                return True
            else:
                logger.warning(f"Task execution returned: {result}")
                return False

        except Exception as e:
            logger.error(f"Error processing task {filename}: {str(e)}")
            logger.error(f"Errors: {str(e)}")
            return False


# =============================================================================
# Polling File Watcher
# =============================================================================

class PollingFileWatcher:
    """Polling-based file watcher for Needs_Action folder."""

    def __init__(self, processor: TaskProcessor, interval: float = 5.0):
        self.processor = processor
        self.interval = interval
        self.stop_event = Event()
        self.thread = None

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
        """Main polling loop."""
        while not self.stop_event.is_set():
            try:
                pending_tasks = self.processor.scan_for_tasks()

                if not pending_tasks:
                    self.stop_event.wait(self.interval)
                    continue

                for file_path in pending_tasks:
                    if self.stop_event.is_set():
                        break
                    success = self.processor.process_task(file_path)
                    if success:
                        logger.info(f"Task processed successfully: {file_path.name}")

                self.stop_event.wait(self.interval)

            except Exception as e:
                logger.error(f"Polling error: {str(e)}")
                self.stop_event.wait(self.interval)


# =============================================================================
# Main Execution
# =============================================================================

def main():
    """Main entry point for the task executor."""
    print("\n" + "=" * 70)
    print("AI Employee Task Executor - OFFICIAL ACCOUNTS ONLY")
    print("=" * 70)
    print(f"Base Directory: {BASE_DIR}")
    print(f"Monitoring: {NEEDS_ACTION_DIR}")
    print(f"Skills Path: {SKILLS_PATH}")
    print("")
    print("OFFICIAL ACCOUNTS FILTER:")
    print(f"  Status: {'ENABLED' if OFFICIAL_FILTER_ENABLED else 'DISABLED'}")
    print(f"  LinkedIn: {LINKEDIN_OFFICIAL_ACCOUNTS if LINKEDIN_OFFICIAL_ACCOUNTS else 'NONE (ALL REJECTED)'}")
    print(f"  WhatsApp: {WHATSAPP_OFFICIAL_NUMBERS if WHATSAPP_OFFICIAL_NUMBERS else 'NONE (ALL REJECTED)'}")
    print(f"  Gmail: {GMAIL_OFFICIAL_ACCOUNTS if GMAIL_OFFICIAL_ACCOUNTS else 'NONE (ALL REJECTED)'}")
    print("")
    print(f"Human Approval: {'REQUIRED' if HUMAN_APPROVAL_REQUIRED else 'NOT REQUIRED'}")
    print(f"Reject Non-Official: {'YES' if REJECT_NON_OFFICIAL else 'NO (FLAG ONLY)'}")
    print("")
    print("WORKFLOW:")
    print("  Watcher → Inbox → Needs_Action → task_executor → Skill → AI Response → Approval → Done")
    print("")
    print("⚠️  ONLY messages from official accounts will be processed.")
    print("⚠️  All other messages will be IGNORED and logged.")
    print("")
    print("Press Ctrl+C to stop")
    print("=" * 70)

    # Ensure directories exist
    for directory in [NEEDS_ACTION_DIR, IN_PROGRESS_DIR, PENDING_APPROVAL_DIR,
                      DONE_DIR, UNCLASSIFIED_DIR, LOGS_DIR, SKILLS_PATH]:
        directory.mkdir(parents=True, exist_ok=True)
        logger.info(f"Directory verified: {directory}")

    processor = TaskProcessor(
        needs_action_dir=NEEDS_ACTION_DIR,
        in_progress_dir=IN_PROGRESS_DIR,
        pending_approval_dir=PENDING_APPROVAL_DIR,
        done_dir=DONE_DIR,
        unclassified_dir=UNCLASSIFIED_DIR,
        skills_path=SKILLS_PATH
    )
    watcher = PollingFileWatcher(processor, interval=5.0)

    watcher.start()
    logger.info("Task executor started successfully")
    print("\n✅ Monitoring Needs_Action for tasks...")
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
