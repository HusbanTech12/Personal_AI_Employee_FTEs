#!/usr/bin/env python3
"""
Validator Agent - Gold Tier AI Employee

Confirms task completion, verifies outputs exist, approves completion,
and moves tasks to Done folder.

Part of the Gold Tier multi-agent system.
"""

import os
import sys
import re
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ValidatorAgent")


class ValidationStatus(Enum):
    """Validation result status."""
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    PENDING = "pending"


@dataclass
class ValidationResult:
    """Result of task validation."""
    status: ValidationStatus
    checks_passed: int
    checks_total: int
    deliverables_verified: List[str]
    missing_items: List[str]
    recommendation: str  # "complete", "retry", "manual_review"


class ValidatorAgent:
    """
    Validator Agent for Gold Tier AI Employee.
    
    Responsibilities:
    - Confirm task completion
    - Verify outputs exist
    - Approve completion
    - Move task to Done folder
    """
    
    # Completion criteria by skill type
    COMPLETION_CRITERIA = {
        'coding': ['Working code', 'Tests', 'Documentation'],
        'research': ['Research report', 'Comparison matrix', 'Recommendation'],
        'documentation': ['Documentation file', 'Examples', 'Cross-references'],
        'planning': ['Project plan', 'Task breakdown', 'Timeline'],
        'default': ['Deliverable completed', 'Output generated']
    }
    
    def __init__(self, needs_action_dir: Path, done_dir: Path, logs_dir: Path, dashboard_file: Path):
        self.needs_action_dir = needs_action_dir
        self.done_dir = done_dir
        self.logs_dir = logs_dir
        self.dashboard_file = dashboard_file
        self.validated_tasks: set = set()
        
    def check_execution_results(self, task_file: Path) -> bool:
        """Check if task has execution results section."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return '## Execution Results' in content
        except Exception as e:
            logger.error(f"Failed to check execution results: {e}")
            return False
    
    def check_deliverables(self, task_file: Path) -> Tuple[List[str], List[str]]:
        """Check which deliverables are completed."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            completed = []
            pending = []
            
            # Find deliverables in execution plan
            plan_match = re.search(r'### Deliverables\s*\n(.*?)(?=### |\Z)', content, re.DOTALL)
            if plan_match:
                deliverables_text = plan_match.group(1)
                
                # Check completed items
                completed_matches = re.findall(r'- \[x\] (.+)$', deliverables_text, re.MULTILINE)
                pending_matches = re.findall(r'- \[ \] (.+)$', deliverables_text, re.MULTILINE)
                
                completed.extend(completed_matches)
                pending.extend(pending_matches)
            
            # Also check execution results section
            results_match = re.search(r'### Deliverables Generated\s*\n(.*?)(?=### |\Z)', content, re.DOTALL)
            if results_match:
                results_text = results_match.group(1)
                completed_matches = re.findall(r'- \[x\] (.+)$', results_text, re.MULTILINE)
                completed.extend(completed_matches)
            
            return completed, pending
        except Exception as e:
            logger.error(f"Failed to check deliverables: {e}")
            return [], []
    
    def check_output_quality(self, task_file: Path) -> bool:
        """Check if output has meaningful content."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for output section
            output_match = re.search(r'### Output\s*\n(.*?)(?=### |\Z)', content, re.DOTALL)
            if not output_match:
                return False
            
            output_text = output_match.group(1).strip()
            
            # Check output has substance (not just "done" or empty)
            if len(output_text) < 20:
                return False
            
            # Check for common failure indicators
            failure_indicators = ['error', 'failed', 'could not', 'unable to']
            for indicator in failure_indicators:
                if indicator.lower() in output_text.lower():
                    # But allow if it's part of a success message
                    if 'no error' not in output_text.lower() and 'without error' not in output_text.lower():
                        return False
            
            return True
        except Exception as e:
            logger.error(f"Failed to check output quality: {e}")
            return False
    
    def check_error_log(self, task_file: Path) -> bool:
        """Check if task has error log (indicates failure)."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for error section without resolution
            if '## Error Log' in content:
                if '## Execution Results' not in content:
                    return True  # Has error but no results = failed
            
            return False
        except Exception as e:
            logger.error(f"Failed to check error log: {e}")
            return False
    
    def validate_task(self, task_file: Path) -> ValidationResult:
        """Perform complete validation of a task."""
        checks_passed = 0
        checks_total = 4
        deliverables_verified = []
        missing_items = []
        
        # Check 1: Has execution results
        has_results = self.check_execution_results(task_file)
        if has_results:
            checks_passed += 1
            deliverables_verified.append("Execution results present")
        else:
            missing_items.append("Execution results section")
        
        # Check 2: Deliverables completed
        completed, pending = self.check_deliverables(task_file)
        if completed and not pending:
            checks_passed += 1
            deliverables_verified.extend(completed)
        elif completed:
            checks_passed += 0.5
            deliverables_verified.extend(completed)
            missing_items.extend(pending)
        else:
            missing_items.append("Completed deliverables")
        
        # Check 3: Output quality
        has_quality_output = self.check_output_quality(task_file)
        if has_quality_output:
            checks_passed += 1
            deliverables_verified.append("Quality output generated")
        else:
            missing_items.append("Quality output")
        
        # Check 4: No unresolved errors
        has_errors = self.check_error_log(task_file)
        if not has_errors:
            checks_passed += 1
        else:
            missing_items.append("Unresolved errors")
        
        # Determine status
        if checks_passed == checks_total:
            status = ValidationStatus.PASSED
            recommendation = "complete"
        elif checks_passed >= checks_total - 1:
            status = ValidationStatus.PARTIAL
            recommendation = "complete"  # Allow minor issues
        elif checks_passed >= checks_total / 2:
            status = ValidationStatus.PARTIAL
            recommendation = "retry"
        else:
            status = ValidationStatus.FAILED
            recommendation = "manual_review"
        
        return ValidationResult(
            status=status,
            checks_passed=int(checks_passed),
            checks_total=checks_total,
            deliverables_verified=deliverables_verified,
            missing_items=missing_items,
            recommendation=recommendation
        )
    
    def update_frontmatter(self, task_file: Path):
        """Update task frontmatter to status: done."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update status in frontmatter
            def replace_status(match):
                fm_content = match.group(1)
                if 'status:' in fm_content:
                    new_fm = re.sub(r'^status:\s*.*$', 'status: done', fm_content, flags=re.MULTILINE)
                else:
                    new_fm = fm_content + 'status: done\n'
                return f'---\n{new_fm}---'
            
            new_content = re.sub(r'^---\s*\n(.*?)\n---\s*\n', replace_status, content, flags=re.DOTALL)
            
            # Add completed timestamp if not present
            if 'completed:' not in new_content:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                new_content = re.sub(
                    r'(status:\s*done)',
                    f'\\1\ncompleted: {timestamp}',
                    new_content
                )
            
            with open(task_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"Frontmatter updated for {task_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to update frontmatter: {e}")
    
    def move_to_done(self, task_file: Path) -> bool:
        """Move task file to Done folder."""
        try:
            destination = self.done_dir / task_file.name
            
            # Check if destination already exists
            if destination.exists():
                # Create unique name
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                stem = task_file.stem
                suffix = task_file.suffix
                destination = self.done_dir / f"{stem}_{timestamp}{suffix}"
            
            # Move file
            shutil.copy2(task_file, destination)
            task_file.unlink()
            
            logger.info(f"Moved to Done: {destination.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move file to Done: {e}")
            return False
    
    def write_activity_log(self, task_name: str, validation: ValidationResult):
        """Write validation entry to activity log."""
        try:
            log_file = self.logs_dir / "activity_log.md"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Create log file if doesn't exist
            if not log_file.exists():
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write("timestamp | action | file | status\n")
            
            # Write entry
            status_str = "validated" if validation.status == ValidationStatus.PASSED else "validated_partial"
            log_entry = f"{timestamp} | {status_str} | {task_name} | ready_for_done\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            logger.info("Activity log updated")
            
        except Exception as e:
            logger.error(f"Failed to write activity log: {e}")
    
    def process_task(self, task_file: Path) -> bool:
        """Process a single task for validation."""
        task_name = task_file.name
        
        # Skip if already validated
        if task_name in self.validated_tasks:
            logger.info(f"Task already validated: {task_name}")
            return True
        
        logger.info(f"Validating task: {task_name}")
        
        # Perform validation
        validation = self.validate_task(task_file)
        
        logger.info(f"  Status: {validation.status.value}")
        logger.info(f"  Checks: {validation.checks_passed}/{validation.checks_total}")
        logger.info(f"  Recommendation: {validation.recommendation}")
        
        if validation.recommendation == "manual_review":
            logger.warning(f"Task requires manual review: {task_name}")
            return False
        
        if validation.recommendation == "retry":
            logger.warning(f"Task needs retry: {task_name}")
            return False
        
        # Update frontmatter
        self.update_frontmatter(task_file)
        
        # Write activity log
        self.write_activity_log(task_name, validation)
        
        # Move to Done
        if self.move_to_done(task_file):
            self.validated_tasks.add(task_name)
            logger.info(f"Task completed and moved to Done: {task_name}")
            return True
        
        return False
    
    def scan_for_validation(self) -> List[Path]:
        """Scan for tasks ready for validation."""
        tasks = []
        
        if not self.needs_action_dir.exists():
            return tasks
        
        for file_path in self.needs_action_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.md':
                # Check if has execution results and not already done
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if '## Execution Results' in content and 'status: done' not in content:
                    if file_path.name not in self.validated_tasks:
                        tasks.append(file_path)
        
        return tasks
    
    def run(self):
        """Main validator loop."""
        logger.info("Validator Agent started")
        
        while True:
            try:
                tasks = self.scan_for_validation()
                
                if not tasks:
                    time.sleep(5)
                    continue
                
                for task_file in tasks:
                    self.process_task(task_file)
                
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("Validator Agent stopping...")
                break
            except Exception as e:
                logger.error(f"Error in validator loop: {e}")
                time.sleep(5)


# Import time for the run loop
import time

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    agent = ValidatorAgent(
        needs_action_dir=BASE_DIR / "Needs_Action",
        done_dir=BASE_DIR / "Done",
        logs_dir=BASE_DIR / "Logs",
        dashboard_file=BASE_DIR / "Dashboard.md"
    )
    agent.run()
