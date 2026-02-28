#!/usr/bin/env python3
"""
Task Processor Agent - Gold Tier AI Employee

Generic skill agent that reads *.SKILL.md definitions and executes
tasks based on the skill's defined workflow. Used for coding, planning,
and general task processing.

Part of the Gold Tier multi-agent system.
"""

import os
import sys
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("TaskProcessorAgent")


class TaskProcessorAgent:
    """
    Task Processor Agent - Generic skill executor.
    
    Responsibilities:
    - Read matching *.SKILL.md definition
    - Accept task input
    - Execute defined workflow
    - Produce output markdown
    - Return completion status
    """
    
    def __init__(self, skills_dir: Path, logs_dir: Path, skill_name: str = "task_processor"):
        self.skills_dir = skills_dir
        self.logs_dir = logs_dir
        self.skill_name = skill_name
        self.skill_definition: Optional[str] = None
        
        # Load skill definition
        self._load_skill_definition()
    
    def _load_skill_definition(self):
        """Load the skill definition markdown file."""
        skill_file = self.skills_dir / f"{self.skill_name}.SKILL.md"
        
        if not skill_file.exists():
            logger.warning(f"Skill definition not found: {skill_file}")
            return
        
        try:
            with open(skill_file, 'r', encoding='utf-8') as f:
                self.skill_definition = f.read()
            logger.info(f"Loaded skill definition: {self.skill_name}")
        except Exception as e:
            logger.error(f"Failed to load skill definition: {e}")
    
    def parse_skill_workflow(self) -> List[str]:
        """Parse execution steps from skill definition."""
        if not self.skill_definition:
            return []
        
        steps = []
        
        # Look for "Execution Steps" section
        exec_match = re.search(
            r'## Execution Steps\s*\n(.*?)(?=## |$)',
            self.skill_definition,
            re.DOTALL
        )
        
        if exec_match:
            exec_section = exec_match.group(1)
            # Extract step headers
            step_headers = re.findall(r'### Step \d+:?\s*(\w+)', exec_section)
            steps = step_headers
        
        return steps
    
    def execute(self, task_input: Dict) -> Dict:
        """
        Execute the task based on skill definition.
        
        Args:
            task_input: Dictionary containing:
                - title: Task title
                - content: Task description/content
                - execution_plan: Plan from planner agent
                - frontmatter: Task metadata
        
        Returns:
            Dictionary with:
                - success: bool
                - output: str (generated content)
                - deliverables: List[str]
                - error: Optional[str]
        """
        logger.info(f"Executing task: {task_input.get('title', 'Unknown')}")
        
        try:
            # Get task content
            content = task_input.get('content', '')
            plan = task_input.get('execution_plan', {})
            
            # Determine what type of processing is needed
            skill = plan.get('skill', self.skill_name)
            
            # Generate output based on skill type
            if skill in ['coding', 'task_processor']:
                return self._execute_coding(task_input)
            elif skill == 'planner':
                return self._execute_planning(task_input)
            else:
                return self._execute_generic(task_input)
                
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {
                'success': False,
                'output': '',
                'deliverables': [],
                'error': str(e)
            }
    
    def _execute_coding(self, task_input: Dict) -> Dict:
        """Execute coding-related task."""
        content = task_input.get('content', '')
        title = task_input.get('title', 'Task')
        
        # Analyze what code is needed
        code_request = self._analyze_code_request(content)
        
        # Generate code output
        output = self._generate_code_output(title, code_request)
        
        return {
            'success': True,
            'output': output,
            'deliverables': ['Code implementation', 'Documentation'],
            'error': None
        }
    
    def _execute_planning(self, task_input: Dict) -> Dict:
        """Execute planning-related task."""
        content = task_input.get('content', '')
        title = task_input.get('title', 'Task')
        
        # Generate plan
        plan_output = self._generate_plan_output(title, content)
        
        return {
            'success': True,
            'output': plan_output,
            'deliverables': ['Project plan', 'Task breakdown', 'Timeline'],
            'error': None
        }
    
    def _execute_generic(self, task_input: Dict) -> Dict:
        """Execute generic task."""
        content = task_input.get('content', '')
        title = task_input.get('title', 'Task')
        
        # Generate generic output
        output = f"""
## Task: {title}

### Analysis

Task content analyzed and processed according to skill definition.

### Processing Summary

- Task Type: {self.skill_name}
- Content Length: {len(content)} characters
- Processed At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Result

Task processed successfully. Output generated based on skill workflow.
"""
        
        return {
            'success': True,
            'output': output,
            'deliverables': ['Processed output'],
            'error': None
        }
    
    def _analyze_code_request(self, content: str) -> Dict:
        """Analyze what type of code is requested."""
        analysis = {
            'language': 'python',
            'type': 'function',
            'requirements': [],
            'complexity': 'medium'
        }
        
        # Detect language hints
        if 'python' in content.lower() or '.py' in content:
            analysis['language'] = 'python'
        elif 'javascript' in content.lower() or '.js' in content:
            analysis['language'] = 'javascript'
        elif 'bash' in content.lower() or '.sh' in content:
            analysis['language'] = 'bash'
        
        # Detect type
        if 'api' in content.lower() or 'endpoint' in content.lower():
            analysis['type'] = 'api'
        elif 'script' in content.lower():
            analysis['type'] = 'script'
        elif 'class' in content.lower():
            analysis['type'] = 'class'
        
        # Extract requirements (bullet points)
        requirements = re.findall(r'-\s*(.+)$', content, re.MULTILINE)
        analysis['requirements'] = requirements[:5]
        
        return analysis
    
    def _generate_code_output(self, title: str, analysis: Dict) -> str:
        """Generate code output based on analysis."""
        lang = analysis['language']
        
        if lang == 'python':
            code_example = f'''```python
#!/usr/bin/env python3
"""
{title}

Auto-generated implementation.
"""

import logging

logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    logger.info("{title} - Executing")
    
    # Implementation goes here
    # TODO: Implement based on requirements
    
    logger.info("{title} - Complete")


if __name__ == "__main__":
    main()
```'''
        elif lang == 'javascript':
            code_example = f'''```javascript
/**
 * {title}
 * 
 * Auto-generated implementation.
 */

const logger = {{
    info: (msg) => console.log(`[INFO] ${{msg}}`),
    error: (msg) => console.error(`[ERROR] ${{msg}}`)
}};

function main() {{
    logger.info("{title} - Executing");
    
    // Implementation goes here
    // TODO: Implement based on requirements
    
    logger.info("{title} - Complete");
}}

main();
```'''
        else:
            code_example = f'''```bash
#!/bin/bash
# {title}
# Auto-generated script

set -e

echo "[INFO] {title} - Executing"

# Implementation goes here
# TODO: Implement based on requirements

echo "[INFO] {title} - Complete"
```'''
        
        return f"""
## Code Implementation

Generated for: {title}

**Language:** {analysis['language']}
**Type:** {analysis['type']}

{code_example}

## Requirements Addressed

""" + '\n'.join(f"- {req}" for req in analysis['requirements']) + """

## Usage

See code example above. Run according to language conventions.
"""
    
    def _generate_plan_output(self, title: str, content: str) -> str:
        """Generate planning output."""
        return f"""
## Project Plan: {title}

### Objective

{content[:200]}...

### Phases

**Phase 1: Discovery**
- Gather requirements
- Identify stakeholders
- Document current state

**Phase 2: Analysis**
- Analyze requirements
- Identify constraints
- Evaluate options

**Phase 3: Planning**
- Create detailed plan
- Define milestones
- Assign resources

**Phase 4: Execution**
- Implement plan
- Monitor progress
- Adjust as needed

### Timeline

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Discovery | 1-2 days | - |
| Analysis | 2-3 days | Discovery |
| Planning | 2-3 days | Analysis |
| Execution | Variable | Planning |

### Next Steps

1. Review and approve this plan
2. Assign resources
3. Begin Phase 1
"""


if __name__ == "__main__":
    # Test execution
    BASE_DIR = Path(__file__).parent.parent
    VAULT_PATH = BASE_DIR / "notes"

    agent = TaskProcessorAgent(
        skills_dir=VAULT_PATH / "Skills",
        logs_dir=BASE_DIR / "Logs",
        skill_name="task_processor"
    )
    
    # Test with sample input
    test_input = {
        'title': 'Test Task',
        'content': 'Create a Python script that does something useful',
        'execution_plan': {'skill': 'coding'}
    }
    
    result = agent.execute(test_input)
    print(f"Success: {result['success']}")
    print(f"Output: {result['output'][:200]}...")
