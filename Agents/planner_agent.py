#!/usr/bin/env python3
"""
Planner Agent - Gold Tier AI Employee

Reads tasks from Needs_Action folder, analyzes task markdown content,
generates execution plans, and breaks work into manageable steps.

Part of the Gold Tier multi-agent system.
"""

import os
import sys
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("PlannerAgent")


@dataclass
class TaskAnalysis:
    """Result of task analysis."""
    task_file: Path
    title: str
    description: str
    priority: str
    category: str
    keywords: List[str]
    estimated_complexity: str  # low, medium, high
    suggested_skill: str


@dataclass
class ExecutionPlan:
    """Generated execution plan for a task."""
    task_file: Path
    objective: str
    steps: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)
    skill_required: str = ""
    estimated_duration: str = ""
    dependencies: List[str] = field(default_factory=list)


class PlannerAgent:
    """
    Planner Agent for Gold Tier AI Employee.
    
    Responsibilities:
    - Read tasks from Needs_Action folder
    - Analyze task markdown content
    - Generate execution plans
    - Break work into steps
    - Suggest appropriate skill agent
    """
    
    # Category keywords for task classification
    CATEGORY_KEYWORDS = {
        'coding': ['code', 'function', 'api', 'script', 'implement', 'build', 
                   'develop', 'refactor', 'debug', 'test', 'endpoint', 'module',
                   '.py', '.js', '.ts', '.java', '.cpp', '.sh'],
        'research': ['research', 'analyze', 'investigate', 'explore', 'compare',
                     'evaluate', 'study', 'find', 'search', 'review', 'survey'],
        'documentation': ['document', 'write', 'readme', 'guide', 'tutorial',
                          'explain', 'describe', 'update docs', 'manual'],
        'planning': ['plan', 'strategy', 'roadmap', 'design', 'architecture',
                     'outline', 'structure', 'organize', 'project', 'timeline']
    }
    
    # Skill mapping
    SKILL_MAP = {
        'coding': 'task_processor',  # Routes to coding_agent
        'research': 'research',
        'documentation': 'documentation',
        'planning': 'planner'
    }
    
    def __init__(self, needs_action_dir: Path, logs_dir: Path):
        self.needs_action_dir = needs_action_dir
        self.logs_dir = logs_dir
        self.processed_tasks: set = set()
        
    def scan_for_tasks(self) -> List[Path]:
        """Scan Needs_Action for pending tasks."""
        pending_tasks = []
        
        if not self.needs_action_dir.exists():
            return pending_tasks
        
        for file_path in self.needs_action_dir.iterdir():
            if (file_path.is_file() and 
                file_path.suffix.lower() == '.md' and
                file_path.name not in self.processed_tasks):
                pending_tasks.append(file_path)
        
        return pending_tasks
    
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
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', text.lower())
        
        # Filter common stop words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                      'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                      'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                      'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                      'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                      'through', 'during', 'before', 'after', 'above', 'below',
                      'between', 'under', 'again', 'further', 'then', 'once',
                      'and', 'but', 'or', 'nor', 'so', 'yet', 'both', 'either',
                      'neither', 'not', 'only', 'own', 'same', 'than', 'too',
                      'very', 'just', 'also', 'now', 'task', 'file', 'this'}
        
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return list(set(keywords))[:20]  # Limit to top 20 unique keywords
    
    def classify_task(self, text: str, frontmatter: Dict) -> str:
        """Classify task into category based on content."""
        text_lower = text.lower()
        scores = {cat: 0 for cat in self.CATEGORY_KEYWORDS}
        
        # Check explicit skill hint in frontmatter
        if 'skill' in frontmatter:
            skill = frontmatter['skill'].lower()
            for category, keywords in self.CATEGORY_KEYWORDS.items():
                if category in skill or any(k in skill for k in keywords):
                    scores[category] += 10
        
        # Score based on keywords in content
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    scores[category] += 1
        
        # Return highest scoring category
        return max(scores, key=scores.get) if max(scores.values()) > 0 else 'planning'
    
    def estimate_complexity(self, text: str, keywords: List[str]) -> str:
        """Estimate task complexity based on content."""
        word_count = len(text.split())
        has_code = '```' in text
        has_checklist = '- [ ]' in text or '- [x]' in text
        has_multiple_requirements = text.count('- [ ]') > 3
        
        if word_count > 500 or (has_code and has_multiple_requirements):
            return 'high'
        elif word_count > 200 or has_code or has_checklist:
            return 'medium'
        else:
            return 'low'
    
    def analyze_task(self, file_path: Path) -> Optional[TaskAnalysis]:
        """Perform complete task analysis."""
        try:
            body, frontmatter = self.read_task(file_path)
            keywords = self.extract_keywords(body)
            category = self.classify_task(body, frontmatter)
            complexity = self.estimate_complexity(body, keywords)
            
            title = frontmatter.get('title', file_path.stem.replace('_', ' ').title())
            priority = frontmatter.get('priority', 'standard')
            
            return TaskAnalysis(
                task_file=file_path,
                title=title,
                description=body[:500] + '...' if len(body) > 500 else body,
                priority=priority,
                category=category,
                keywords=keywords,
                estimated_complexity=complexity,
                suggested_skill=self.SKILL_MAP.get(category, 'task_processor')
            )
        except Exception as e:
            logger.error(f"Failed to analyze task {file_path.name}: {e}")
            return None
    
    def generate_execution_plan(self, analysis: TaskAnalysis) -> ExecutionPlan:
        """Generate execution plan based on task analysis."""
        plan = ExecutionPlan(
            task_file=analysis.task_file,
            objective=f"Complete task: {analysis.title}",
            skill_required=analysis.suggested_skill
        )
        
        # Generate steps based on category
        if analysis.category == 'coding':
            plan.steps = [
                "1. Read and understand requirements",
                "2. Design solution approach",
                "3. Implement code",
                "4. Write tests",
                "5. Test implementation",
                "6. Document changes",
                "7. Verify completion"
            ]
            plan.deliverables = ["Working code", "Tests", "Documentation"]
            plan.estimated_duration = "30-60 minutes"
            
        elif analysis.category == 'research':
            plan.steps = [
                "1. Define research questions",
                "2. Gather information from sources",
                "3. Analyze findings",
                "4. Compare alternatives",
                "5. Formulate recommendation",
                "6. Document findings",
                "7. Verify completion"
            ]
            plan.deliverables = ["Research report", "Comparison matrix", "Recommendation"]
            plan.estimated_duration = "45-90 minutes"
            
        elif analysis.category == 'documentation':
            plan.steps = [
                "1. Understand target audience",
                "2. Gather source materials",
                "3. Create document outline",
                "4. Write content",
                "5. Add examples",
                "6. Review and refine",
                "7. Verify completion"
            ]
            plan.deliverables = ["Documentation file", "Examples", "Cross-references"]
            plan.estimated_duration = "30-60 minutes"
            
        else:  # planning
            plan.steps = [
                "1. Clarify goals and objectives",
                "2. Identify scope and constraints",
                "3. Break down into tasks",
                "4. Identify dependencies",
                "5. Create timeline",
                "6. Document plan",
                "7. Verify completion"
            ]
            plan.deliverables = ["Project plan", "Task breakdown", "Timeline"]
            plan.estimated_duration = "20-45 minutes"
        
        return plan
    
    def save_execution_plan(self, plan: ExecutionPlan, analysis: TaskAnalysis):
        """Save execution plan to task file."""
        try:
            # Read existing content
            with open(plan.task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check if execution plan already exists
            if '## Execution Plan' in content:
                logger.info(f"Execution plan already exists for {plan.task_file.name}")
                return
            
            # Generate plan markdown
            plan_md = f"""
---

## Execution Plan

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**Objective:** {plan.objective}

**Skill Required:** {plan.skill_required}

**Estimated Duration:** {plan.estimated_duration}

**Complexity:** {analysis.estimated_complexity}

### Steps

"""
            for step in plan.steps:
                plan_md += f"- {step}\n"
            
            plan_md += "\n### Deliverables\n\n"
            for deliverable in plan.deliverables:
                plan_md += f"- [ ] {deliverable}\n"
            
            # Append to content
            new_content = content + plan_md
            
            # Write back
            with open(plan.task_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"Execution plan saved for {plan.task_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to save execution plan: {e}")
    
    def process_task(self, file_path: Path) -> Optional[ExecutionPlan]:
        """Process a single task: analyze and generate plan."""
        logger.info(f"Analyzing task: {file_path.name}")
        
        analysis = self.analyze_task(file_path)
        if not analysis:
            return None
        
        logger.info(f"  Category: {analysis.category}")
        logger.info(f"  Skill: {analysis.suggested_skill}")
        logger.info(f"  Complexity: {analysis.estimated_complexity}")
        
        plan = self.generate_execution_plan(analysis)
        self.save_execution_plan(plan, analysis)
        
        self.processed_tasks.add(file_path.name)
        
        return plan
    
    def run(self):
        """Main processing loop."""
        logger.info("Planner Agent started")
        
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
                logger.info("Planner Agent stopping...")
                break
            except Exception as e:
                logger.error(f"Error in planner loop: {e}")
                time.sleep(5)


# Import time for the run loop
import time

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    agent = PlannerAgent(
        needs_action_dir=BASE_DIR / "Needs_Action",
        logs_dir=BASE_DIR / "Logs"
    )
    agent.run()
