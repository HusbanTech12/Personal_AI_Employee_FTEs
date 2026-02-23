#!/usr/bin/env python3
"""
Reasoning Agent - Silver Tier AI Employee

Monitors Needs_Action folder for new tasks and generates detailed reasoning plans.
Creates Plan.md files beside each task with step-by-step analysis.

Behavior:
- Continuously monitors Needs_Action folder
- Reads task markdown content
- Thinks step-by-step using chain-of-thought reasoning
- Generates Plan.md with goal, steps, skill, risk, and approval requirements
- Stores Plan.md beside the original task file

Requirements:
    None (standard library only)

Usage:
    python reasoning_agent.py

Stop:
    Press Ctrl+C to gracefully stop monitoring
"""

import os
import sys
import time
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
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
logger = logging.getLogger("ReasoningAgent")


class RiskLevel(Enum):
    """Risk assessment levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ReasoningPlan:
    """Generated reasoning plan for a task."""
    task_file: Path
    goal: str
    steps: List[str]
    required_skill: str
    risk_level: RiskLevel
    approval_needed: bool
    reasoning: str
    alternatives: List[str]
    success_criteria: List[str]


class ReasoningAgent:
    """
    Reasoning Agent for AI Employee Vault.
    
    Continuously monitors Needs_Action folder and generates
    detailed reasoning plans for each task.
    """
    
    # Keywords for skill classification
    SKILL_KEYWORDS = {
        'coding': ['code', 'function', 'api', 'script', 'implement', 'build', 
                   'develop', 'refactor', 'debug', 'test', 'endpoint', 'module',
                   'program', 'software', 'application', '.py', '.js', '.ts'],
        'research': ['research', 'analyze', 'investigate', 'explore', 'compare',
                     'evaluate', 'study', 'find', 'search', 'review', 'survey'],
        'documentation': ['document', 'write', 'readme', 'guide', 'tutorial',
                          'explain', 'describe', 'manual', 'documentation'],
        'planning': ['plan', 'strategy', 'roadmap', 'design', 'architecture',
                     'outline', 'structure', 'organize', 'project', 'timeline'],
        'communication': ['email', 'message', 'respond', 'reply', 'contact',
                          'notify', 'inform', 'meeting', 'call'],
        'review': ['review', 'check', 'verify', 'audit', 'inspect', 'examine']
    }
    
    # Risk indicators
    RISK_INDICATORS = {
        RiskLevel.CRITICAL: ['production', 'live', 'critical', 'emergency', 
                             'database', 'security', 'financial', 'legal'],
        RiskLevel.HIGH: ['deploy', 'release', 'migration', 'breaking change',
                         'api change', 'schema'],
        RiskLevel.MEDIUM: ['update', 'modify', 'refactor', 'upgrade'],
        RiskLevel.LOW: ['fix', 'add', 'create', 'write', 'document']
    }
    
    # Approval triggers
    APPROVAL_TRIGGERS = [
        'approval', 'permission', 'sign-off', 'authorize', 'confirm',
        'budget', 'expense', 'purchase', 'contract', 'agreement',
        'policy change', 'terms', 'legal'
    ]
    
    def __init__(self, needs_action_dir: Path, logs_dir: Path):
        self.needs_action_dir = needs_action_dir
        self.logs_dir = logs_dir
        self.processed_tasks: Set[str] = set()
        self.plan_cache: Dict[str, ReasoningPlan] = {}
        
        # Ensure directories exist
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def scan_for_tasks(self) -> List[Path]:
        """Scan Needs_Action for tasks without Plan.md."""
        tasks_without_plan = []
        
        if not self.needs_action_dir.exists():
            return tasks_without_plan
        
        for file_path in self.needs_action_dir.iterdir():
            if (file_path.is_file() and 
                file_path.suffix.lower() == '.md' and
                file_path.name != 'Plan.md'):
                
                # Check if Plan.md exists beside this task
                plan_file = file_path.parent / f"Plan_{file_path.stem}.md"
                
                if (not plan_file.exists() and 
                    file_path.name not in self.processed_tasks):
                    tasks_without_plan.append(file_path)
        
        return tasks_without_plan
    
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
    
    def classify_skill(self, content: str, frontmatter: Dict) -> str:
        """Classify task into skill category."""
        content_lower = content.lower()
        scores = {skill: 0 for skill in self.SKILL_KEYWORDS}
        
        # Check explicit skill hint in frontmatter
        if 'skill' in frontmatter:
            skill_hint = frontmatter['skill'].lower()
            for skill, keywords in self.SKILL_KEYWORDS.items():
                if skill in skill_hint:
                    scores[skill] += 10
        
        # Score based on keywords in content
        for skill, keywords in self.SKILL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in content_lower:
                    scores[skill] += 1
        
        # Return highest scoring skill
        max_score = max(scores.values())
        if max_score > 0:
            return max(scores, key=scores.get)
        
        return 'planning'  # Default
    
    def assess_risk(self, content: str, frontmatter: Dict) -> RiskLevel:
        """Assess task risk level."""
        content_lower = content.lower()
        
        # Check each risk level
        for risk_level, indicators in sorted(
            self.RISK_INDICATORS.items(),
            key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}[x[0].value]
        ):
            for indicator in indicators:
                if indicator in content_lower:
                    return risk_level
        
        return RiskLevel.LOW  # Default
    
    def check_approval_needed(self, content: str, frontmatter: Dict) -> bool:
        """Check if task requires approval."""
        content_lower = content.lower()
        
        for trigger in self.APPROVAL_TRIGGERS:
            if trigger in content_lower:
                return True
        
        # Check priority - high priority may need approval
        priority = frontmatter.get('priority', 'standard').lower()
        if priority in ['urgent', 'high']:
            return True
        
        return False
    
    def extract_goal(self, content: str, frontmatter: Dict) -> str:
        """Extract the primary goal from task."""
        # Try to get from title first
        title = frontmatter.get('title', '')
        if title:
            return f"Complete: {title}"
        
        # Extract from first meaningful line
        lines = content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and len(line) > 10:
                return f"Achieve: {line[:100]}"
        
        return "Complete the task as specified"
    
    def generate_steps(self, content: str, skill: str, goal: str) -> List[str]:
        """Generate step-by-step plan using chain-of-thought reasoning."""
        steps = []
        
        # Base reasoning steps
        steps.append("1. Read and understand task requirements")
        steps.append("2. Identify key constraints and dependencies")
        
        # Skill-specific steps
        if skill == 'coding':
            steps.extend([
                "3. Design solution approach",
                "4. Set up development environment",
                "5. Implement code following best practices",
                "6. Write unit tests",
                "7. Test implementation thoroughly",
                "8. Document code and usage",
                "9. Review and verify completion"
            ])
        elif skill == 'research':
            steps.extend([
                "3. Identify information sources",
                "4. Gather relevant data and information",
                "5. Analyze and synthesize findings",
                "6. Compare alternatives if applicable",
                "7. Formulate evidence-based recommendation",
                "8. Document research with citations",
                "9. Review and verify completeness"
            ])
        elif skill == 'documentation':
            steps.extend([
                "3. Identify target audience",
                "4. Gather source materials",
                "5. Create document outline",
                "6. Write clear and concise content",
                "7. Add examples and code snippets",
                "8. Review for accuracy and clarity",
                "9. Finalize and publish"
            ])
        elif skill == 'planning':
            steps.extend([
                "3. Clarify goals and objectives",
                "4. Identify scope and constraints",
                "5. Break down into manageable tasks",
                "6. Identify dependencies",
                "7. Create timeline with milestones",
                "8. Document the plan",
                "9. Review and get stakeholder alignment"
            ])
        elif skill == 'communication':
            steps.extend([
                "3. Determine key message",
                "4. Identify appropriate tone and format",
                "5. Draft the communication",
                "6. Review for clarity and completeness",
                "7. Send/deliver the communication",
                "8. Follow up if needed"
            ])
        else:
            steps.extend([
                "3. Plan approach",
                "4. Execute the task",
                "5. Verify results",
                "6. Document outcomes",
                "7. Review completion"
            ])
        
        return steps
    
    def generate_reasoning(self, content: str, frontmatter: Dict, skill: str,
                          risk: RiskLevel, goal: str) -> str:
        """Generate chain-of-thought reasoning."""
        reasoning = f"""## Reasoning Process

### Understanding the Task

The task requires {skill} work. Let me analyze what needs to be done:

1. **Goal Analysis**: {goal}

2. **Content Analysis**:
   - Task length: {len(content)} characters
   - Has frontmatter: {'Yes' if frontmatter else 'No'}
   - Priority: {frontmatter.get('priority', 'standard')}

3. **Skill Determination**:
   Based on keyword analysis, this task falls under the '{skill}' category.
   This means I should follow {skill} best practices and workflows.

4. **Risk Assessment**:
   Risk Level: {risk.value.upper()}
   - This indicates the level of caution needed during execution
   - Higher risk tasks require more thorough testing and review

5. **Key Considerations**:
   - Ensure all requirements are understood before starting
   - Identify any blockers or dependencies early
   - Plan for edge cases and error handling
   - Document decisions and rationale

6. **Execution Strategy**:
   - Follow the step-by-step plan outlined above
   - Check progress at each milestone
   - Adjust approach if obstacles are encountered
   - Verify completion against success criteria
"""
        return reasoning
    
    def generate_alternatives(self, skill: str) -> List[str]:
        """Generate alternative approaches."""
        alternatives_map = {
            'coding': [
                'Manual implementation',
                'Use existing library/framework',
                'Generate with AI assistance',
                'Outsource to specialist'
            ],
            'research': [
                'Primary research (surveys, interviews)',
                'Secondary research (existing sources)',
                'Expert consultation',
                'Data analysis'
            ],
            'documentation': [
                'Write from scratch',
                'Adapt existing documentation',
                'Use documentation generator',
                'Collaborative documentation'
            ],
            'planning': [
                'Top-down planning',
                'Bottom-up planning',
                'Agile/iterative planning',
                'Template-based planning'
            ]
        }
        
        return alternatives_map.get(skill, ['Standard approach', 'Custom approach'])
    
    def generate_success_criteria(self, skill: str, goal: str) -> List[str]:
        """Generate success criteria for the task."""
        base_criteria = [
            'All requirements from task description are met',
            'Output is reviewed for quality',
            'Documentation is complete'
        ]
        
        skill_criteria = {
            'coding': [
                'Code passes all tests',
                'No linting errors',
                'Code is documented'
            ],
            'research': [
                'Sources are cited',
                'Analysis is evidence-based',
                'Recommendation is clear and actionable'
            ],
            'documentation': [
                'Content is accurate',
                'Examples are working',
                'Document is well-organized'
            ],
            'planning': [
                'Plan is realistic',
                'Dependencies are identified',
                'Timeline is achievable'
            ]
        }
        
        return base_criteria + skill_criteria.get(skill, [])
    
    def create_plan_markdown(self, plan: ReasoningPlan) -> str:
        """Create Plan.md markdown content."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        content = f"""---
title: Plan for {plan.task_file.name}
generated: {timestamp}
skill: {plan.required_skill}
risk: {plan.risk_level.value}
approval_needed: {str(plan.approval_needed).lower()}
---

# Execution Plan: {plan.task_file.stem}

**Generated:** {timestamp}

**Status:** Pending Review

---

## Goal

{plan.goal}

---

## Required Skill

**Primary Skill:** {plan.required_skill.title()}

This task has been classified as requiring **{plan.required_skill}** expertise.
The execution should follow best practices for this skill domain.

---

## Risk Assessment

**Risk Level:** {plan.risk_level.value.upper()}

"""
        
        # Add risk guidance
        if plan.risk_level == RiskLevel.CRITICAL:
            content += """⚠️ **CRITICAL RISK** - This task requires:
- Senior review before execution
- Comprehensive testing plan
- Rollback strategy
- Stakeholder notification
- Change management approval

"""
        elif plan.risk_level == RiskLevel.HIGH:
            content += """⚠️ **HIGH RISK** - This task requires:
- Peer review
- Testing in staging environment
- Backup before changes
- Documentation of changes

"""
        elif plan.risk_level == RiskLevel.MEDIUM:
            content += """⚠️ **MEDIUM RISK** - This task requires:
- Standard testing
- Documentation of approach
- Progress checkpoints

"""
        else:
            content += """✅ **LOW RISK** - This task can proceed with:
- Standard execution
- Basic verification
- Normal documentation

"""
        
        content += """---

## Approval Required

"""
        
        if plan.approval_needed:
            content += """**Status:** ⚠️ APPROVAL NEEDED

This task requires approval before proceeding.

**Approver:** [To be assigned]

**Approval Criteria:**
- Review the plan above
- Confirm risk assessment is accurate
- Verify resources are available
- Approve timeline and approach

"""
        else:
            content += """**Status:** ✅ No approval required

This task can proceed without additional approval.

"""
        
        content += """---

## Step-by-Step Plan

"""
        
        for step in plan.steps:
            content += f"- [ ] {step}\n"
        
        content += f"""
---

## Reasoning

{plan.reasoning}

---

## Alternative Approaches

Consider these alternatives if the primary approach encounters obstacles:

"""
        
        for alt in plan.alternatives:
            content += f"- {alt}\n"
        
        content += """
---

## Success Criteria

Task is considered complete when ALL criteria are met:

"""
        
        for criterion in plan.success_criteria:
            content += f"- [ ] {criterion}\n"
        
        content += """
---

## Notes

- This plan was auto-generated by the Reasoning Agent
- Review and adjust steps as needed during execution
- Update this plan if requirements change
- Mark steps as complete as you progress

---

*Plan generated by AI Employee Reasoning Agent*
"""
        
        return content
    
    def save_plan(self, plan: ReasoningPlan):
        """Save Plan.md beside the task file."""
        plan_file = plan.task_file.parent / f"Plan_{plan.task_file.stem}.md"
        
        content = self.create_plan_markdown(plan)
        
        with open(plan_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Plan saved: {plan_file.name}")
        return plan_file
    
    def reason_about_task(self, file_path: Path) -> Optional[ReasoningPlan]:
        """Perform complete reasoning about a task."""
        logger.info(f"Reasoning about task: {file_path.name}")
        
        try:
            # Read task
            content, frontmatter = self.read_task(file_path)
            
            # Analyze task
            skill = self.classify_skill(content, frontmatter)
            risk = self.assess_risk(content, frontmatter)
            approval = self.check_approval_needed(content, frontmatter)
            goal = self.extract_goal(content, frontmatter)
            
            logger.info(f"  Skill: {skill}")
            logger.info(f"  Risk: {risk.value}")
            logger.info(f"  Approval needed: {approval}")
            
            # Generate plan components
            steps = self.generate_steps(content, skill, goal)
            reasoning = self.generate_reasoning(content, frontmatter, skill, risk, goal)
            alternatives = self.generate_alternatives(skill)
            success_criteria = self.generate_success_criteria(skill, goal)
            
            # Create plan
            plan = ReasoningPlan(
                task_file=file_path,
                goal=goal,
                steps=steps,
                required_skill=skill,
                risk_level=risk,
                approval_needed=approval,
                reasoning=reasoning,
                alternatives=alternatives,
                success_criteria=success_criteria
            )
            
            # Save plan
            self.save_plan(plan)
            
            # Cache and mark as processed
            self.plan_cache[file_path.name] = plan
            self.processed_tasks.add(file_path.name)
            
            return plan
            
        except Exception as e:
            logger.error(f"Failed to reason about task {file_path.name}: {e}")
            return None
    
    def run(self):
        """Main reasoning loop - continuously monitors for new tasks."""
        logger.info("=" * 60)
        logger.info("Reasoning Agent started")
        logger.info(f"Monitoring: {self.needs_action_dir}")
        logger.info(f"Poll interval: 5 seconds")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Waiting for tasks in Needs_Action folder...")
        logger.info("When tasks appear, I will:")
        logger.info("  1. Read and analyze the task")
        logger.info("  2. Think step-by-step")
        logger.info("  3. Generate Plan.md with reasoning")
        logger.info("  4. Store Plan.md beside the task")
        logger.info("")
        
        while True:
            try:
                # Scan for tasks without plans
                tasks = self.scan_for_tasks()
                
                if tasks:
                    logger.info(f"Found {len(tasks)} task(s) needing reasoning...")
                    
                    for task_file in tasks:
                        self.reason_about_task(task_file)
                    
                    logger.info(f"Reasoning complete. Waiting for more tasks...")
                else:
                    # No tasks - wait before next check
                    time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("")
                logger.info("Reasoning Agent stopping...")
                break
            except Exception as e:
                logger.error(f"Error in reasoning loop: {e}")
                time.sleep(5)


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    agent = ReasoningAgent(
        needs_action_dir=BASE_DIR / "Needs_Action",
        logs_dir=BASE_DIR / "Logs"
    )
    agent.run()
