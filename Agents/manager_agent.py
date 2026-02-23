#!/usr/bin/env python3
"""
Manager Agent - Gold Tier AI Employee (Skill-Based Execution)

Orchestrates task execution by triggering skill agents only.
Does not execute tasks directly - all work is delegated to skills.

Behavior:
- Read execution plan from task
- Extract required skill
- Trigger corresponding skill agent
- Monitor skill execution status
- Handle retries on failure

Skill Triggering:
task → skill name → skill agent → execution
"""

import os
import sys
import re
import logging
import importlib.util
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
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
logger = logging.getLogger("ManagerAgent")


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


@dataclass
class SkillConfig:
    """Configuration for a skill."""
    skill_id: str
    skill_file: str  # e.g., email.SKILL.md
    agent_file: str  # e.g., email_agent.py
    agent_class: str  # e.g., EmailAgent
    requires_approval: bool = False


class ManagerAgent:
    """
    Manager Agent - Skill-Based Task Orchestrator.
    
    Responsibilities:
    - Read execution plans from tasks
    - Extract required skill
    - Trigger appropriate skill agent
    - Monitor execution status
    - Handle retries
    - Route to approval if needed
    """
    
    # Skill registry - all available skills
    SKILLS: Dict[str, SkillConfig] = {
        'email': SkillConfig(
            skill_id='email',
            skill_file='email.SKILL.md',
            agent_file='email_agent.py',
            agent_class='EmailAgent',
            requires_approval=True
        ),
        'linkedin_marketing': SkillConfig(
            skill_id='linkedin_marketing',
            skill_file='linkedin_marketing.SKILL.md',
            agent_file='linkedin_agent.py',
            agent_class='LinkedInAgent',
            requires_approval=True
        ),
        'planner': SkillConfig(
            skill_id='planner',
            skill_file='planner.SKILL.md',
            agent_file='planner_agent.py',
            agent_class='PlannerAgent',
            requires_approval=False
        ),
        'coding': SkillConfig(
            skill_id='coding',
            skill_file='coding.SKILL.md',
            agent_file='coding_agent.py',
            agent_class='CodingAgent',
            requires_approval=False
        ),
        'research': SkillConfig(
            skill_id='research',
            skill_file='research.SKILL.md',
            agent_file='research_agent.py',
            agent_class='ResearchAgent',
            requires_approval=False
        ),
        'documentation': SkillConfig(
            skill_id='documentation',
            skill_file='documentation.SKILL.md',
            agent_file='documentation_agent.py',
            agent_class='DocumentationAgent',
            requires_approval=False
        ),
        'approval': SkillConfig(
            skill_id='approval',
            skill_file='approval.SKILL.md',
            agent_file='approval_agent.py',
            agent_class='ApprovalAgent',
            requires_approval=False
        ),
        'task_processor': SkillConfig(
            skill_id='task_processor',
            skill_file='task_processor.SKILL.md',
            agent_file='task_processor_agent.py',
            agent_class='TaskProcessorAgent',
            requires_approval=False
        )
    }
    
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    def __init__(self, needs_action_dir: Path, skills_dir: Path, 
                 agents_dir: Path, logs_dir: Path, needs_approval_dir: Optional[Path] = None):
        self.needs_action_dir = needs_action_dir
        self.skills_dir = skills_dir
        self.agents_dir = agents_dir
        self.logs_dir = logs_dir
        self.needs_approval_dir = needs_approval_dir or (needs_action_dir.parent / "Needs_Approval")
        
        self.task_status: Dict[str, TaskStatus] = {}
        self.loaded_agents: Dict[str, Any] = {}
        self.skill_execution_log: List[Dict] = []
        
        # Ensure directories exist
        self.needs_approval_dir.mkdir(parents=True, exist_ok=True)
    
    def load_skill_agent(self, skill_name: str) -> Optional[Callable]:
        """
        Dynamically load a skill agent class.
        
        This is the ONLY way the manager interacts with skills.
        """
        if skill_name not in self.SKILLS:
            logger.error(f"Unknown skill: {skill_name}")
            logger.info(f"Available skills: {list(self.SKILLS.keys())}")
            return None
        
        config = self.SKILLS[skill_name]
        agent_path = self.agents_dir / config.agent_file
        
        if not agent_path.exists():
            logger.error(f"Agent file not found: {agent_path}")
            return None
        
        try:
            # Load module dynamically
            spec = importlib.util.spec_from_file_location(
                config.agent_class,
                agent_path
            )
            
            if spec is None or spec.loader is None:
                logger.error(f"Failed to load spec for {config.agent_file}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Get agent class
            agent_class = getattr(module, config.agent_class, None)
            
            if agent_class is None:
                logger.error(f"Agent class not found: {config.agent_class}")
                return None
            
            logger.info(f"Loaded skill agent: {skill_name} → {config.agent_file}")
            return agent_class
            
        except Exception as e:
            logger.error(f"Failed to load agent {config.agent_file}: {e}")
            return None
    
    def read_task(self, file_path: Path) -> Tuple[str, Dict]:
        """Read task file and extract frontmatter + content."""
        with open(file_path, 'r', encoding='utf-8') as f:
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
        
        return body, frontmatter
    
    def read_execution_plan(self, task_file: Path) -> Optional[Dict]:
        """Read execution plan from task file."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find execution plan section
            plan_match = re.search(
                r'## Execution Plan\s*\n(.*?)(?=## |\Z)',
                content,
                re.DOTALL
            )
            
            if not plan_match:
                # No explicit plan - use skill from frontmatter
                content_fm, _ = self.read_task(task_file)
                return None
            
            plan_text = plan_match.group(1)
            
            # Extract skill required
            skill_match = re.search(r'\*\*Skill Required:\*\*\s*(\w+)', plan_text)
            skill = skill_match.group(1) if skill_match else None
            
            # If no skill in plan, check frontmatter
            if not skill:
                _, frontmatter = self.read_task(task_file)
                skill = frontmatter.get('skill', 'task_processor')
            
            return {
                'skill': skill,
                'raw': plan_text
            }
            
        except Exception as e:
            logger.error(f"Failed to read execution plan: {e}")
            return None
    
    def get_required_skill(self, task_file: Path) -> str:
        """
        Determine which skill is required for a task.
        
        Priority:
        1. Execution plan skill
        2. Frontmatter skill
        3. Content-based classification
        4. Default: task_processor
        """
        # Try execution plan first
        plan = self.read_execution_plan(task_file)
        if plan and plan.get('skill'):
            return plan['skill']
        
        # Try frontmatter
        _, frontmatter = self.read_task(task_file)
        if 'skill' in frontmatter:
            return frontmatter['skill']
        
        # Content-based classification
        with open(task_file, 'r', encoding='utf-8') as f:
            content = f.read().lower()
        
        # Check for skill indicators
        skill_indicators = {
            'email': ['send email', 'skill: email', 'smtp'],
            'linkedin_marketing': ['linkedin', 'skill: linkedin'],
            'coding': ['code', 'function', 'api', '.py', '.js'],
            'research': ['research', 'analyze', 'compare'],
            'documentation': ['document', 'readme', 'guide'],
            'planner': ['plan', 'roadmap', 'timeline'],
            'approval': ['approval', 'approve']
        }
        
        for skill, indicators in skill_indicators.items():
            for indicator in indicators:
                if indicator in content:
                    logger.info(f"Classified as {skill} based on content")
                    return skill
        
        return 'task_processor'  # Default
    
    def check_approval_required(self, skill_name: str, frontmatter: Dict) -> bool:
        """Check if skill requires approval before execution."""
        if skill_name not in self.SKILLS:
            return False
        
        config = self.SKILLS[skill_name]
        
        # Check skill config
        if config.requires_approval:
            return True
        
        # Check frontmatter override
        priority = frontmatter.get('priority', 'standard').lower()
        if priority in ['urgent', 'critical']:
            return True  # High priority may need approval
        
        return False
    
    def trigger_skill(self, skill_name: str, task_input: Dict) -> Dict:
        """
        Trigger a skill agent to execute a task.
        
        This is the CORE method - manager ONLY triggers skills, never executes directly.
        """
        logger.info(f"Triggering skill: {skill_name}")
        
        # Load skill agent
        agent_class = self.load_skill_agent(skill_name)
        
        if not agent_class:
            return {
                'success': False,
                'error': f'Could not load skill agent: {skill_name}',
                'skill': skill_name
            }
        
        try:
            # Instantiate agent with required directories
            agent = agent_class(
                needs_action_dir=self.needs_action_dir,
                logs_dir=self.logs_dir
            )
            
            # For agents that need additional directories
            if hasattr(agent, 'skills_dir'):
                agent.skills_dir = self.skills_dir
            if hasattr(agent, 'marketing_dir'):
                agent.marketing_dir = self.logs_dir / "Marketing"
            if hasattr(agent, 'needs_approval_dir'):
                agent.needs_approval_dir = self.needs_approval_dir
            
            # Execute task via skill
            result = agent.execute(task_input)
            
            # Log execution
            self.skill_execution_log.append({
                'timestamp': datetime.now().isoformat(),
                'skill': skill_name,
                'task': task_input.get('title', 'unknown'),
                'success': result.get('success', False)
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Skill execution failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'skill': skill_name
            }
    
    def move_to_approval(self, task_file: Path, skill_name: str) -> bool:
        """Move task to Needs_Approval folder."""
        try:
            import shutil
            
            # Create approval request
            approval_content = self._generate_approval_request(task_file, skill_name)
            approval_file = self.needs_approval_dir / f"approval_{task_file.stem}.md"
            
            with open(approval_file, 'w', encoding='utf-8') as f:
                f.write(approval_content)
            
            # Copy task to approval folder
            task_copy = self.needs_approval_dir / task_file.name
            shutil.copy2(task_file, task_copy)
            
            logger.info(f"Task moved to approval: {task_file.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move to approval: {e}")
            return False
    
    def _generate_approval_request(self, task_file: Path, skill_name: str) -> str:
        """Generate approval request markdown."""
        content, frontmatter = self.read_task(task_file)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return f"""---
title: Approval Required: {frontmatter.get('title', task_file.stem)}
original_task: {task_file.name}
skill: {skill_name}
status: pending_approval
created: {timestamp}
---

# Approval Required

**Skill:** {skill_name}

**Task:** {frontmatter.get('title', task_file.stem)}

---

## Action Required

This task requires approval before the {skill_name} skill can execute.

## Instructions

Add your decision:

```
APPROVED: YES

Approved by: [Your Name]
Date: {timestamp}
```

Or reject:

```
APPROVED: NO

Rejected by: [Your Name]
Reason: [Reason]
```

---

*Generated by Manager Agent*
"""
    
    def process_task(self, task_file: Path) -> bool:
        """
        Process a single task through skill-based execution.
        
        Flow:
        1. Read task
        2. Determine required skill
        3. Check if approval needed
        4. If approval needed → move to approval folder
        5. If approved → trigger skill
        6. Handle result
        """
        task_name = task_file.name
        
        # Check if already processed
        if self.task_status.get(task_name) == TaskStatus.COMPLETED:
            logger.info(f"Task already completed: {task_name}")
            return True
        
        # Read task
        content, frontmatter = self.read_task(task_file)
        
        # Determine required skill
        skill_name = self.get_required_skill(task_file)
        logger.info(f"Task: {task_name} → Skill: {skill_name}")
        
        # Check if skill exists
        if skill_name not in self.SKILLS:
            logger.error(f"Unknown skill: {skill_name}")
            self.task_status[task_name] = TaskStatus.FAILED
            return False
        
        # Check approval requirement
        if self.check_approval_required(skill_name, frontmatter):
            logger.info(f"Approval required for {skill_name}")
            
            # Check if already in approval
            approval_file = self.needs_approval_dir / f"approval_{task_file.stem}.md"
            if approval_file.exists():
                # Check for decision
                with open(approval_file, 'r', encoding='utf-8') as f:
                    approval_content = f.read()
                
                if 'APPROVED: YES' in approval_content:
                    logger.info(f"Task approved: {task_name}")
                    # Move back to needs action
                    self._move_from_approval(task_file, approval_file)
                elif 'APPROVED: NO' in approval_content:
                    logger.info(f"Task rejected: {task_name}")
                    self.task_status[task_name] = TaskStatus.FAILED
                    return False
                else:
                    logger.info(f"Waiting for approval: {task_name}")
                    self.task_status[task_name] = TaskStatus.WAITING_APPROVAL
                    return False
            else:
                # Move to approval
                self.move_to_approval(task_file, skill_name)
                self.task_status[task_name] = TaskStatus.WAITING_APPROVAL
                return False
        
        # Update status
        self.task_status[task_name] = TaskStatus.IN_PROGRESS
        
        # Prepare task input for skill
        task_input = {
            'title': frontmatter.get('title', task_file.stem),
            'priority': frontmatter.get('priority', 'standard'),
            'content': content,
            'frontmatter': frontmatter,
            'full_content': content,
            'task_file': task_file
        }
        
        # TRIGGER SKILL - This is the ONLY execution point
        result = self.trigger_skill(skill_name, task_input)
        
        # Handle result
        if result.get('success'):
            logger.info(f"Skill execution successful: {skill_name}")
            self.task_status[task_name] = TaskStatus.COMPLETED
            self._update_task_status(task_file, 'done')
            return True
        else:
            logger.error(f"Skill execution failed: {result.get('error', 'Unknown')}")
            self.task_status[task_name] = TaskStatus.FAILED
            self._log_error(task_file, result.get('error', 'Unknown'))
            return False
    
    def _move_from_approval(self, task_file: Path, approval_file: Path):
        """Move task from approval back to needs action."""
        import shutil
        
        try:
            # Update task with approval info
            content, frontmatter = self.read_task(task_file)
            
            # Add approval metadata
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            if 'approved: true' not in content:
                content = content.replace(
                    'status: needs_action',
                    f'status: needs_action\napproved: true\napproved_at: {timestamp}'
                )
            
            with open(task_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Clean up approval file
            approval_file.unlink()
            
            logger.info(f"Task moved from approval: {task_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to move from approval: {e}")
    
    def _update_task_status(self, task_file: Path, status: str):
        """Update task status in frontmatter."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Update status
            content = re.sub(
                r'(status:\s*)[^\n]+',
                f'\\1{status}',
                content,
                flags=re.MULTILINE
            )
            
            # Add completed timestamp if marking as done
            if status == 'done' and 'completed:' not in content:
                content = re.sub(
                    r'(status:\s*done)',
                    f'\\1\ncompleted: {timestamp}',
                    content
                )
            
            with open(task_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
    
    def _log_error(self, task_file: Path, error: str):
        """Log error to task file."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            error_md = f"""
---

## Error

**Time:** {timestamp}
**Error:** {error}

**Status:** FAILED
"""
            
            with open(task_file, 'w', encoding='utf-8') as f:
                f.write(content + error_md)
            
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
    
    def scan_for_tasks(self) -> List[Path]:
        """Scan Needs_Action for tasks ready for processing."""
        tasks = []
        
        if not self.needs_action_dir.exists():
            return tasks
        
        for file_path in self.needs_action_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.md':
                # Skip if already completed
                if self.task_status.get(file_path.name) == TaskStatus.COMPLETED:
                    continue
                
                # Skip if has error without retry
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if '## Error' in content and 'status: retry' not in content:
                    continue
                
                tasks.append(file_path)
        
        return tasks
    
    def get_status(self) -> Dict:
        """Get manager status."""
        return {
            'running': True,
            'tasks_total': len(self.task_status),
            'tasks_completed': sum(1 for s in self.task_status.values() if s == TaskStatus.COMPLETED),
            'tasks_pending': sum(1 for s in self.task_status.values() if s == TaskStatus.PENDING),
            'skills_available': list(self.SKILLS.keys()),
            'execution_log_count': len(self.skill_execution_log)
        }
    
    def run(self):
        """Main manager loop - skill-based orchestration."""
        logger.info("=" * 60)
        logger.info("Manager Agent started (Skill-Based Execution)")
        logger.info(f"Skills directory: {self.skills_dir}")
        logger.info(f"Agents directory: {self.agents_dir}")
        logger.info(f"Approval directory: {self.needs_approval_dir}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Registered skills:")
        for skill_name, config in self.SKILLS.items():
            approval = " (requires approval)" if config.requires_approval else ""
            logger.info(f"  - {skill_name}: {config.agent_file}{approval}")
        logger.info("")
        logger.info("Manager triggers skills only - no direct execution")
        logger.info("")
        
        while True:
            try:
                tasks = self.scan_for_tasks()
                
                if not tasks:
                    time.sleep(5)
                    continue
                
                for task_file in tasks:
                    self.process_task(task_file)
                
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("")
                logger.info("Manager Agent stopping...")
                break
            except Exception as e:
                logger.error(f"Error in manager loop: {e}")
                time.sleep(5)


# Import time for the run loop
import time

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    agent = ManagerAgent(
        needs_action_dir=BASE_DIR / "Needs_Action",
        skills_dir=BASE_DIR / "Skills",
        agents_dir=BASE_DIR / "Agents",
        logs_dir=BASE_DIR / "Logs"
    )
    agent.run()
