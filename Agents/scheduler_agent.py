#!/usr/bin/env python3
"""
Scheduler Agent - Silver Tier AI Employee

Runs periodic tasks based on schedule.md configuration.
Supports both cron expressions and interval-based scheduling.
Compatible with cron (Linux/Mac) and Windows Task Scheduler.

Capabilities:
- Run periodic tasks based on schedule
- Cron expression parsing
- Interval-based scheduling
- Task execution tracking
- Skip handling for holidays/exceptions
- Logging and notifications

Usage:
    python scheduler_agent.py

Stop:
    Press Ctrl+C to gracefully stop

Windows Task Scheduler Setup:
    schtasks /Create /TN "AI_Employee_Scheduler" /TR "python scheduler_agent.py" /SC ONSTART /RL HIGHEST

Linux Cron Setup:
    @reboot python /path/to/scheduler_agent.py
"""

import os
import sys
import re
import json
import logging
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SchedulerAgent")


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ScheduledTask:
    """Represents a scheduled task."""
    name: str
    schedule: str
    task_type: str  # 'cron' or 'interval'
    action: str
    enabled: bool
    description: str
    task_template: Optional[str] = None
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0
    fail_count: int = 0


class CronParser:
    """Parse and evaluate cron expressions."""
    
    @staticmethod
    def parse_field(field: str, min_val: int, max_val: int) -> List[int]:
        """Parse a single cron field."""
        values = set()
        
        for part in field.split(','):
            if part == '*':
                values.update(range(min_val, max_val + 1))
            elif '/' in part:
                base, step = part.split('/')
                step = int(step)
                if base == '*':
                    start = min_val
                else:
                    start = int(base)
                values.update(range(start, max_val + 1, step))
            elif '-' in part:
                start, end = map(int, part.split('-'))
                values.update(range(start, end + 1))
            else:
                values.add(int(part))
        
        return sorted(v for v in values if min_val <= v <= max_val)
    
    @staticmethod
    def matches(expression: str, dt: datetime) -> bool:
        """Check if datetime matches cron expression."""
        parts = expression.split()
        if len(parts) != 5:
            return False
        
        minute, hour, day, month, weekday = parts
        
        return (
            dt.minute in CronParser.parse_field(minute, 0, 59) and
            dt.hour in CronParser.parse_field(hour, 0, 23) and
            dt.day in CronParser.parse_field(day, 1, 31) and
            dt.month in CronParser.parse_field(month, 1, 12) and
            dt.weekday() in CronParser.parse_field(weekday, 0, 6)
        )
    
    @staticmethod
    def next_run(expression: str, after: Optional[datetime] = None) -> datetime:
        """Calculate next run time for cron expression."""
        if after is None:
            after = datetime.now()
        
        # Start from next minute
        dt = after.replace(second=0, microsecond=0) + timedelta(minutes=1)
        
        # Search for next matching time (max 1 year)
        max_iterations = 366 * 24 * 60
        for _ in range(max_iterations):
            if CronParser.matches(expression, dt):
                return dt
            dt += timedelta(minutes=1)
        
        raise ValueError(f"Could not find next run time for: {expression}")


class SchedulerAgent:
    """
    Scheduler Agent for AI Employee Vault.
    
    Reads schedule.md and executes tasks at configured times.
    """
    
    def __init__(self, base_dir: Path, vault_path: Optional[Path] = None, schedule_file: Optional[Path] = None):
        self.base_dir = base_dir
        self.vault_path = vault_path or (base_dir / "notes")
        self.schedule_file = schedule_file or (base_dir / "schedule.md")
        self.logs_dir = base_dir / "Logs"
        self.needs_action_dir = self.vault_path / "Needs_Action"
        self.state_file = self.logs_dir / "scheduler_state.json"
        
        self.tasks: Dict[str, ScheduledTask] = {}
        self.exceptions: List[Dict] = []
        self.timezone: str = "UTC"
        self.notifications: Dict = {}
        
        self.running = False
        
        # Ensure directories exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)
        
        # Load state
        self._load_state()
    
    def _load_state(self):
        """Load scheduler state from file."""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    logger.info(f"Loaded scheduler state: {len(state.get('tasks', {}))} tasks")
                    return state
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
        return {'tasks': {}, 'exceptions': []}
    
    def _save_state(self):
        """Save scheduler state to file."""
        try:
            state = {
                'tasks': {name: asdict(task) for name, task in self.tasks.items()},
                'exceptions': self.exceptions,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
            logger.debug("Scheduler state saved")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def parse_schedule_md(self) -> bool:
        """Parse schedule.md configuration file."""
        if not self.schedule_file.exists():
            logger.warning(f"Schedule file not found: {self.schedule_file}")
            logger.info("Creating default schedule.md...")
            self._create_default_schedule()
            return False
        
        try:
            with open(self.schedule_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse YAML-like blocks
            current_task = None
            current_data = {}
            
            for line in content.split('\n'):
                line = line.rstrip()
                
                # Skip comments and empty lines
                if not line or line.strip().startswith('#'):
                    continue
                
                # Check for task name (no leading whitespace, ends with :)
                if not line.startswith(' ') and not line.startswith('\t') and ':' in line:
                    # Save previous task
                    if current_task and current_data:
                        self._add_task(current_task, current_data)
                    
                    # Start new task
                    key = line.split(':')[0].strip()
                    if key not in ['schedule', 'type', 'action', 'enabled', 'description', 
                                   'task_template', 'last_run', 'next_run', 'timezone',
                                   'on_success', 'on_failure', 'on_skip', 'channel',
                                   'date', 'reason']:
                        current_task = key
                        current_data = {}
                    elif current_task:
                        # This is a property
                        value = line.split(':', 1)[1].strip()
                        current_data[current_task.split('.')[-1]] = value
                
                # Check for indented property
                elif (line.startswith('  ') or line.startswith('\t')) and current_task:
                    line = line.strip()
                    if ':' in line:
                        key, value = line.split(':', 1)
                        current_data[key.strip()] = value.strip()
            
            # Don't forget the last task
            if current_task and current_data:
                self._add_task(current_task, current_data)
            
            # Parse exceptions
            self._parse_exceptions(content)
            
            logger.info(f"Parsed {len(self.tasks)} scheduled tasks")
            return True
            
        except Exception as e:
            logger.error(f"Failed to parse schedule.md: {e}")
            return False
    
    def _add_task(self, name: str, data: Dict):
        """Add a task to the scheduler."""
        if not data.get('schedule') or not data.get('action'):
            return
        
        task = ScheduledTask(
            name=name,
            schedule=data.get('schedule', ''),
            task_type=data.get('type', 'cron'),
            action=data.get('action', ''),
            enabled=data.get('enabled', 'true').lower() == 'true',
            description=data.get('description', ''),
            task_template=data.get('task_template'),
            last_run=data.get('last_run'),
            next_run=data.get('next_run'),
            run_count=int(data.get('run_count', 0)),
            fail_count=int(data.get('fail_count', 0))
        )
        
        # Calculate next run if not set
        if not task.next_run and task.enabled:
            try:
                if task.task_type == 'cron':
                    next_dt = CronParser.next_run(task.schedule)
                    task.next_run = next_dt.strftime('%Y-%m-%d %H:%M:%S')
                elif task.task_type == 'interval':
                    seconds = int(task.schedule)
                    next_dt = datetime.now() + timedelta(seconds=seconds)
                    task.next_run = next_dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception as e:
                logger.error(f"Failed to calculate next run for {name}: {e}")
        
        self.tasks[name] = task
        logger.debug(f"Added task: {name} ({task.schedule})")
    
    def _parse_exceptions(self, content: str):
        """Parse exception dates from schedule."""
        # Simple parsing for exception dates
        exception_pattern = r'-\s*date:\s*"(\d{4}-\d{2}-\d{2})"\s*\n\s*action:\s*(\w+)\s*\n\s*reason:\s*(.+)'
        matches = re.findall(exception_pattern, content)
        
        for match in matches:
            self.exceptions.append({
                'date': match[0],
                'action': match[1],
                'reason': match[2].strip()
            })
    
    def _create_default_schedule(self):
        """Create default schedule.md file."""
        default_content = """# AI Employee Schedule Configuration

## Daily Tasks

daily_inbox_scan:
  schedule: "0 */2 * * *"
  type: "cron"
  action: "inbox_scan"
  enabled: true
  description: "Scan inbox for new files every 2 hours"

daily_digest:
  schedule: "0 17 * * *"
  type: "cron"
  action: "generate_digest"
  enabled: true
  description: "Generate daily activity digest at 5 PM"

## Weekly Tasks

weekly_report:
  schedule: "0 9 * * 1"
  type: "cron"
  action: "weekly_report"
  enabled: true
  description: "Generate weekly report every Monday at 9 AM"

## Interval Tasks

health_check:
  schedule: "300"
  type: "interval"
  action: "health_check"
  enabled: true
  description: "Check system health every 5 minutes"
"""
        
        with open(self.schedule_file, 'w', encoding='utf-8') as f:
            f.write(default_content)
        
        logger.info(f"Created default schedule: {self.schedule_file}")
    
    def is_exception_date(self, date: datetime) -> Tuple[bool, Optional[Dict]]:
        """Check if date is an exception (holiday, etc.)."""
        date_str = date.strftime('%Y-%m-%d')
        
        for exception in self.exceptions:
            if exception['date'] == date_str:
                return True, exception
        
        return False, None
    
    def should_run_task(self, task: ScheduledTask) -> bool:
        """Check if a task should run now."""
        if not task.enabled:
            return False
        
        if not task.next_run:
            return False
        
        try:
            next_run = datetime.strptime(task.next_run, '%Y-%m-%d %H:%M:%S')
            
            # Check if it's an exception date
            is_exception, exception = self.is_exception_date(next_run)
            if is_exception:
                logger.info(f"Skipping {task.name} - Exception: {exception['reason']}")
                return False
            
            # Check if it's time to run
            return datetime.now() >= next_run
            
        except Exception as e:
            logger.error(f"Error checking task {task.name}: {e}")
            return False
    
    def execute_task(self, task: ScheduledTask) -> bool:
        """Execute a scheduled task."""
        logger.info(f"Executing task: {task.name} ({task.action})")
        
        try:
            # Map action to execution
            action_handlers = {
                'inbox_scan': self._run_inbox_scan,
                'linkedin_post': self._run_linkedin_post,
                'weekly_report': self._run_weekly_report,
                'generate_digest': self._run_digest,
                'health_check': self._run_health_check,
                'cleanup_logs': self._run_cleanup,
                'monthly_analytics': self._run_analytics,
                'process_queue': self._run_queue_processor,
            }
            
            handler = action_handlers.get(task.action)
            
            if handler:
                success = handler(task)
            else:
                logger.warning(f"Unknown action: {task.action}")
                success = False
            
            # Update task state
            task.last_run = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            task.run_count += 1
            
            if success:
                # Calculate next run
                self._calculate_next_run(task)
                self._log_task_execution(task, "COMPLETED")
            else:
                task.fail_count += 1
                self._log_task_execution(task, "FAILED")
            
            self._save_state()
            return success
            
        except Exception as e:
            logger.error(f"Task {task.name} failed: {e}")
            task.fail_count += 1
            self._save_state()
            return False
    
    def _calculate_next_run(self, task: ScheduledTask):
        """Calculate next run time for a task."""
        try:
            if task.task_type == 'cron':
                next_dt = CronParser.next_run(task.schedule)
                task.next_run = next_dt.strftime('%Y-%m-%d %H:%M:%S')
            elif task.task_type == 'interval':
                seconds = int(task.schedule)
                next_dt = datetime.now() + timedelta(seconds=seconds)
                task.next_run = next_dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.error(f"Failed to calculate next run for {task.name}: {e}")
    
    # Action Handlers
    
    def _run_inbox_scan(self, task: ScheduledTask) -> bool:
        """Run inbox scan."""
        logger.info("Running inbox scan...")
        # Trigger filesystem watcher logic
        return True
    
    def _run_linkedin_post(self, task: ScheduledTask) -> bool:
        """Trigger LinkedIn post creation."""
        logger.info("Creating LinkedIn post task...")
        
        # Create task file
        task_content = f"""---
title: Scheduled LinkedIn Post - {datetime.now().strftime('%Y-%m-%d')}
status: needs_action
skill: linkedin_marketing
topic: Daily Business Update
audience: Business professionals
scheduled: true
---

## Content Brief

Generate and publish a LinkedIn post for today.

Key points:
- Industry insights
- Company updates
- Thought leadership

---

*Generated by Scheduler Agent*
"""
        
        task_file = self.needs_action_dir / f"linkedin_scheduled_{datetime.now().strftime('%Y%m%d')}.md"
        
        try:
            with open(task_file, 'w', encoding='utf-8') as f:
                f.write(task_content)
            logger.info(f"Created LinkedIn task: {task_file.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create LinkedIn task: {e}")
            return False
    
    def _run_weekly_report(self, task: ScheduledTask) -> bool:
        """Generate weekly report."""
        logger.info("Generating weekly report...")
        
        report_content = f"""---
title: Weekly Report - Week {datetime.now().isocalendar()[1]}
status: needs_action
skill: documentation
generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
---

# Weekly Report

**Week:** {datetime.now().isocalendar()[1]}
**Period:** {datetime.now().strftime('%Y-%m-%d')}

---

## Summary

This is an automated weekly report generated by the AI Employee system.

## Tasks Completed

- Review activity logs for completed tasks
- Count tasks moved to Done folder

## Tasks Pending

- Review Needs_Action folder
- Check for blocked tasks

## Key Achievements

*To be filled by AI Employee*

## Next Week Goals

*To be filled by AI Employee*

---

*Generated by Scheduler Agent*
"""
        
        report_file = self.needs_action_dir / f"weekly_report_{datetime.now().strftime('%Y%m%d')}.md"
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            logger.info(f"Created weekly report: {report_file.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create weekly report: {e}")
            return False
    
    def _run_digest(self, task: ScheduledTask) -> bool:
        """Generate daily digest."""
        logger.info("Generating daily digest...")
        return True
    
    def _run_health_check(self, task: ScheduledTask) -> bool:
        """Run system health check."""
        logger.debug("Running health check...")
        
        # Check directories
        checks = {
            'Inbox': self.base_dir / 'Inbox',
            'Needs_Action': self.base_dir / 'Needs_Action',
            'Done': self.base_dir / 'Done',
            'Logs': self.logs_dir
        }
        
        all_ok = True
        for name, path in checks.items():
            if not path.exists():
                logger.warning(f"Directory missing: {name}")
                all_ok = False
        
        return all_ok
    
    def _run_cleanup(self, task: ScheduledTask) -> bool:
        """Clean up old logs."""
        logger.info("Running log cleanup...")
        return True
    
    def _run_analytics(self, task: ScheduledTask) -> bool:
        """Generate monthly analytics."""
        logger.info("Generating monthly analytics...")
        return True
    
    def _run_queue_processor(self, task: ScheduledTask) -> bool:
        """Process task queue."""
        logger.debug("Processing task queue...")
        return True
    
    def _log_task_execution(self, task: ScheduledTask, status: str):
        """Log task execution to file."""
        log_file = self.logs_dir / "scheduler_log.md"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            if not log_file.exists():
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write("# Scheduler Execution Log\n\n")
                    f.write("| Timestamp | Task | Action | Status |\n")
                    f.write("|-----------|------|--------|--------|\n")
            
            entry = f"| {timestamp} | {task.name} | {task.action} | {status} |\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(entry)
            
            logger.debug(f"Logged task execution: {task.name} - {status}")
            
        except Exception as e:
            logger.error(f"Failed to log task execution: {e}")
    
    def get_status(self) -> Dict:
        """Get scheduler status."""
        return {
            'running': self.running,
            'tasks_total': len(self.tasks),
            'tasks_enabled': sum(1 for t in self.tasks.values() if t.enabled),
            'exceptions': len(self.exceptions),
            'next_runs': {
                name: task.next_run 
                for name, task in sorted(
                    self.tasks.items(),
                    key=lambda x: x[1].next_run or '9999'
                )[:5]
            }
        }
    
    def run(self):
        """Main scheduler loop."""
        logger.info("=" * 60)
        logger.info("Scheduler Agent started")
        logger.info(f"Schedule file: {self.schedule_file}")
        logger.info(f"State file: {self.state_file}")
        logger.info("=" * 60)
        
        # Parse schedule
        self.parse_schedule_md()
        
        # Log status
        status = self.get_status()
        logger.info(f"Total tasks: {status['tasks_total']}")
        logger.info(f"Enabled tasks: {status['tasks_enabled']}")
        logger.info("")
        logger.info("Next scheduled runs:")
        for name, next_run in status['next_runs'].items():
            if next_run:
                logger.info(f"  {name}: {next_run}")
        logger.info("")
        
        self.running = True
        
        while self.running:
            try:
                # Check each task
                for task in self.tasks.values():
                    if self.should_run_task(task):
                        self.execute_task(task)
                
                # Save state periodically
                self._save_state()
                
                # Wait before next check
                time.sleep(30)  # Check every 30 seconds
                
            except KeyboardInterrupt:
                logger.info("")
                logger.info("Scheduler Agent stopping...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                time.sleep(30)


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent
    VAULT_PATH = BASE_DIR / "notes"
    agent = SchedulerAgent(base_dir=BASE_DIR, vault_path=VAULT_PATH)
    agent.run()
