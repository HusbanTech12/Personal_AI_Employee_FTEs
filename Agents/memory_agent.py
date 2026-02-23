#!/usr/bin/env python3
"""
Memory Agent - Gold Tier AI Employee

Updates Logs, Dashboard.md, stores execution history, and maintains
system state across sessions.

Part of the Gold Tier multi-agent system.
"""

import os
import sys
import re
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MemoryAgent")


@dataclass
class ExecutionRecord:
    """Record of a task execution."""
    task_name: str
    skill_used: str
    started_at: str
    completed_at: str
    status: str  # success, failed, partial
    deliverables: List[str]
    retries: int


class MemoryAgent:
    """
    Memory Agent for Gold Tier AI Employee.
    
    Responsibilities:
    - Update Logs with execution history
    - Update Dashboard.md with metrics
    - Store execution history for future reference
    - Maintain system state
    """
    
    def __init__(self, logs_dir: Path, dashboard_file: Path, done_dir: Path):
        self.logs_dir = logs_dir
        self.dashboard_file = dashboard_file
        self.done_dir = done_dir
        self.execution_history: List[ExecutionRecord] = []
        self.history_file = logs_dir / "execution_history.json"
        
        # Load existing history
        self._load_history()
    
    def _load_history(self):
        """Load execution history from file."""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.execution_history = [
                        ExecutionRecord(**record) for record in data
                    ]
                logger.info(f"Loaded {len(self.execution_history)} execution records")
        except Exception as e:
            logger.error(f"Failed to load execution history: {e}")
    
    def _save_history(self):
        """Save execution history to file."""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(
                    [asdict(record) for record in self.execution_history],
                    f,
                    indent=2
                )
            logger.debug("Execution history saved")
        except Exception as e:
            logger.error(f"Failed to save execution history: {e}")
    
    def record_execution(self, record: ExecutionRecord):
        """Record a new task execution."""
        self.execution_history.append(record)
        self._save_history()
        logger.info(f"Recorded execution: {record.task_name}")
    
    def update_activity_log(self, task_name: str, skill: str, status: str):
        """Update the activity log with execution details."""
        try:
            log_file = self.logs_dir / "activity_log.md"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Create log file if doesn't exist
            if not log_file.exists():
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write("timestamp | action | file | status\n")
            
            # Write entry
            action = "executed" if status == "success" else "executed_partial"
            log_entry = f"{timestamp} | {action} | {task_name} | {skill}\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            logger.info("Activity log updated")
            
        except Exception as e:
            logger.error(f"Failed to update activity log: {e}")
    
    def update_dashboard(self, task_name: str, skill: str, status: str):
        """Update Dashboard.md with completion metrics."""
        try:
            if not self.dashboard_file.exists():
                logger.warning("Dashboard.md not found")
                return
            
            with open(self.dashboard_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Update Completed_Tasks section
            content = self._update_completed_tasks(content, task_name, timestamp)
            
            # Update Metrics section
            content = self._update_metrics(content, skill, timestamp)
            
            # Update Timestamp section
            content = self._update_timestamp(content, timestamp)
            
            # Write back
            with open(self.dashboard_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info("Dashboard updated")
            
        except Exception as e:
            logger.error(f"Failed to update dashboard: {e}")
    
    def _update_completed_tasks(self, content: str, task_name: str, timestamp: str) -> str:
        """Update the Completed_Tasks section."""
        start_marker = "<!-- AI_PARSE_START: Completed_Tasks -->"
        end_marker = "<!-- AI_PARSE_END: Completed_Tasks -->"
        
        if start_marker not in content or end_marker not in content:
            logger.warning("Dashboard markers not found for Completed_Tasks")
            return content
        
        new_entry = f"- [x] `{task_name}` - Completed: {timestamp}\n"
        
        start_idx = content.find(start_marker) + len(start_marker)
        end_idx = content.find(end_marker)
        
        current_content = content[start_idx:end_idx].strip()
        
        if "*No completed tasks" in current_content:
            updated_section = f"\n{new_entry}"
        else:
            updated_section = f"{current_content}\n{new_entry}"
        
        return content[:start_idx] + updated_section + content[end_idx:]
    
    def _update_metrics(self, content: str, skill: str, timestamp: str) -> str:
        """Update the Metrics section."""
        metrics_start = "<!-- AI_PARSE_START: Metrics -->"
        metrics_end = "<!-- AI_PARSE_END: Metrics -->"
        
        if metrics_start not in content or metrics_end not in content:
            logger.warning("Dashboard markers not found for Metrics")
            return content
        
        # Update Last Activity
        content = re.sub(
            r'\| Last Activity \| `[^`]*` \|',
            f'| Last Activity | `{timestamp}` |',
            content
        )
        
        # Increment Completed Tasks
        completed_match = re.search(r'\| Completed Tasks \| `(\d+)` \|', content)
        if completed_match:
            current_count = int(completed_match.group(1))
            content = re.sub(
                r'\| Completed Tasks \| `\d+` \|',
                f'| Completed Tasks | `{current_count + 1}` |',
                content
            )
        
        # Update Watcher Status
        content = re.sub(
            r'\| Watcher Status \| `[^`]*` \|',
            '| Watcher Status | `ACTIVE` |',
            content
        )
        
        return content
    
    def _update_timestamp(self, content: str, timestamp: str) -> str:
        """Update the Timestamp section."""
        ts_marker = "<!-- AI_PARSE_START: Timestamp -->"
        ts_end = "<!-- AI_PARSE_END: Timestamp -->"
        
        if ts_marker not in content or ts_end not in content:
            logger.warning("Dashboard markers not found for Timestamp")
            return content
        
        ts_content = f"\n**Timestamp:** `{timestamp}`\n"
        
        ts_start = content.find(ts_marker) + len(ts_marker)
        ts_end_idx = content.find(ts_end)
        
        return content[:ts_start] + ts_content + content[ts_end_idx:]
    
    def remove_from_pending(self, task_name: str):
        """Remove task from pending tasks list in Dashboard."""
        try:
            if not self.dashboard_file.exists():
                return
            
            with open(self.dashboard_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            pending_start = "<!-- AI_PARSE_START: Pending_Tasks -->"
            pending_end = "<!-- AI_PARSE_END: Pending_Tasks -->"
            
            if pending_start not in content or pending_end not in content:
                return
            
            p_start_idx = content.find(pending_start) + len(pending_start)
            p_end_idx = content.find(pending_end)
            
            pending_content = content[p_start_idx:p_end_idx]
            
            # Remove the task entry
            task_pattern = rf'- \[ \] `{re.escape(task_name)}`[^\n]*\n?'
            new_pending = re.sub(task_pattern, '', pending_content)
            
            # If empty, add placeholder
            if new_pending.strip() == '':
                new_pending = '\n*No pending tasks*\n'
            
            content = content[:p_start_idx] + new_pending + content[p_end_idx:]
            
            with open(self.dashboard_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Removed {task_name} from pending tasks")
            
        except Exception as e:
            logger.error(f"Failed to remove from pending: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        if not self.execution_history:
            return {
                'total_executions': 0,
                'success_rate': 0,
                'skills_used': {},
                'avg_retries': 0
            }
        
        total = len(self.execution_history)
        successes = sum(1 for r in self.execution_history if r.status == 'success')
        
        skills = {}
        total_retries = 0
        for record in self.execution_history:
            skills[record.skill_used] = skills.get(record.skill_used, 0) + 1
            total_retries += record.retries
        
        return {
            'total_executions': total,
            'success_rate': round(successes / total * 100, 1) if total > 0 else 0,
            'skills_used': skills,
            'avg_retries': round(total_retries / total, 2) if total > 0 else 0
        }
    
    def process_completed_task(self, task_name: str, skill: str, status: str, 
                                deliverables: List[str], retries: int = 0):
        """Process a completed task - full memory update."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Record execution
        record = ExecutionRecord(
            task_name=task_name,
            skill_used=skill,
            started_at=timestamp,
            completed_at=timestamp,
            status=status,
            deliverables=deliverables,
            retries=retries
        )
        self.record_execution(record)
        
        # Update activity log
        self.update_activity_log(task_name, skill, status)
        
        # Update dashboard
        self.update_dashboard(task_name, skill, status)
        
        # Remove from pending
        self.remove_from_pending(task_name)
        
        logger.info(f"Memory updated for task: {task_name}")
    
    def scan_done_folder(self) -> List[Path]:
        """Scan Done folder for unrecorded completions."""
        completed = []
        
        if not self.done_dir.exists():
            return completed
        
        # Get recorded task names
        recorded_names = {r.task_name for r in self.execution_history}
        
        for file_path in self.done_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.md':
                if file_path.name not in recorded_names:
                    completed.append(file_path)
        
        return completed
    
    def run(self):
        """Main memory agent loop."""
        logger.info("Memory Agent started")
        
        while True:
            try:
                # Check for new completions in Done folder
                completed_tasks = self.scan_done_folder()
                
                for task_file in completed_tasks:
                    # Extract info from task file
                    try:
                        with open(task_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        # Get skill from execution plan
                        skill_match = re.search(r'\*\*Skill Required:\*\*\s*(\w+)', content)
                        skill = skill_match.group(1) if skill_match else 'unknown'
                        
                        # Get deliverables
                        deliverables = []
                        deliv_matches = re.findall(r'- \[x\] (.+)$', content, re.MULTILINE)
                        deliverables = deliv_matches[:5]  # Limit to 5
                        
                        # Record in memory
                        self.process_completed_task(
                            task_name=task_file.name,
                            skill=skill,
                            status='success',
                            deliverables=deliverables
                        )
                        
                        logger.info(f"Recorded historical completion: {task_file.name}")
                        
                    except Exception as e:
                        logger.error(f"Failed to process {task_file.name}: {e}")
                
                time.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                logger.info("Memory Agent stopping...")
                break
            except Exception as e:
                logger.error(f"Error in memory loop: {e}")
                time.sleep(10)


# Import time for the run loop
import time

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    agent = MemoryAgent(
        logs_dir=BASE_DIR / "Logs",
        dashboard_file=BASE_DIR / "Dashboard.md",
        done_dir=BASE_DIR / "Done"
    )
    agent.run()
