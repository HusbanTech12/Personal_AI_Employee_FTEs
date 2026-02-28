#!/usr/bin/env python3
"""
Coding Agent - Gold Tier AI Employee

Specialized skill agent for coding tasks. Reads coding.SKILL.md,
generates code, writes tests, and documents implementations.

Part of the Gold Tier multi-agent system.
"""

import os
import sys
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("CodingAgent")


class CodingAgent:
    """
    Coding Agent - Specialized skill executor for code tasks.
    
    Responsibilities:
    - Read coding.SKILL.md definition
    - Accept coding task input
    - Generate code implementations
    - Write tests
    - Document code
    - Return completion status
    """
    
    def __init__(self, skills_dir: Path, logs_dir: Path):
        self.skills_dir = skills_dir
        self.logs_dir = logs_dir
        self.skill_name = "coding"
        self.skill_definition: Optional[str] = None
        
        # Load skill definition
        self._load_skill_definition()
    
    def _load_skill_definition(self):
        """Load the coding skill definition markdown file."""
        skill_file = self.skills_dir / f"{self.skill_name}.SKILL.md"
        
        if not skill_file.exists():
            logger.warning(f"Coding skill definition not found: {skill_file}")
            return
        
        try:
            with open(skill_file, 'r', encoding='utf-8') as f:
                self.skill_definition = f.read()
            logger.info(f"Loaded coding skill definition")
        except Exception as e:
            logger.error(f"Failed to load coding skill definition: {e}")
    
    def execute(self, task_input: Dict) -> Dict:
        """
        Execute a coding task.
        
        Args:
            task_input: Dictionary containing:
                - title: Task title
                - content: Task description/content
                - execution_plan: Plan from planner agent
                - frontmatter: Task metadata
        
        Returns:
            Dictionary with:
                - success: bool
                - output: str (generated code)
                - deliverables: List[str]
                - error: Optional[str]
        """
        logger.info(f"Coding Agent executing: {task_input.get('title', 'Unknown')}")
        
        try:
            content = task_input.get('content', '')
            title = task_input.get('title', 'Task')
            frontmatter = task_input.get('frontmatter', {})
            
            # Analyze the coding request
            analysis = self._analyze_request(content)
            
            # Generate code based on analysis
            code_output = self._generate_code(title, content, analysis)
            
            # Generate tests
            tests = self._generate_tests(title, analysis)
            
            # Generate documentation
            docs = self._generate_documentation(title, analysis)
            
            # Combine output
            output = self._combine_output(code_output, tests, docs, analysis)
            
            deliverables = [
                f"Code implementation ({analysis['language']})",
                "Unit tests",
                "Documentation"
            ]
            
            return {
                'success': True,
                'output': output,
                'deliverables': deliverables,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Coding task execution failed: {e}")
            return {
                'success': False,
                'output': '',
                'deliverables': [],
                'error': str(e)
            }
    
    def _analyze_request(self, content: str) -> Dict:
        """Analyze coding request to determine requirements."""
        analysis = {
            'language': self._detect_language(content),
            'type': self._detect_type(content),
            'framework': self._detect_framework(content),
            'requirements': self._extract_requirements(content),
            'inputs': [],
            'outputs': [],
            'complexity': 'medium'
        }
        
        # Detect complexity
        if len(analysis['requirements']) > 5:
            analysis['complexity'] = 'high'
        elif len(analysis['requirements']) <= 2:
            analysis['complexity'] = 'low'
        
        return analysis
    
    def _detect_language(self, content: str) -> str:
        """Detect programming language from request."""
        content_lower = content.lower()
        
        if 'python' in content_lower or '.py' in content:
            return 'python'
        elif 'javascript' in content_lower or '.js' in content_lower or 'node' in content_lower:
            return 'javascript'
        elif 'typescript' in content_lower or '.ts' in content:
            return 'typescript'
        elif 'java' in content_lower and 'javascript' not in content_lower:
            return 'java'
        elif 'bash' in content_lower or 'shell' in content_lower or '.sh' in content:
            return 'bash'
        elif 'go' in content_lower and 'lang' not in content_lower:
            return 'go'
        elif 'rust' in content_lower:
            return 'rust'
        
        return 'python'  # Default
    
    def _detect_type(self, content: str) -> str:
        """Detect code type from request."""
        content_lower = content.lower()
        
        if any(x in content_lower for x in ['api', 'endpoint', 'rest', 'http']):
            return 'api'
        elif any(x in content_lower for x in ['function', 'method', 'def ']):
            return 'function'
        elif any(x in content_lower for x in ['class', 'object', 'struct']):
            return 'class'
        elif any(x in content_lower for x in ['script', 'automation', 'batch']):
            return 'script'
        elif any(x in content_lower for x in ['test', 'spec', 'unit']):
            return 'test'
        elif any(x in content_lower for x in ['module', 'package', 'library']):
            return 'module'
        
        return 'function'  # Default
    
    def _detect_framework(self, content: str) -> Optional[str]:
        """Detect framework from request."""
        content_lower = content.lower()
        
        frameworks = {
            'flask': 'flask',
            'django': 'django',
            'fastapi': 'fastapi',
            'react': 'react',
            'vue': 'vue',
            'angular': 'angular',
            'express': 'express',
            'spring': 'spring',
            'pytest': 'pytest',
            'unittest': 'unittest'
        }
        
        for key, framework in frameworks.items():
            if key in content_lower:
                return framework
        
        return None
    
    def _extract_requirements(self, content: str) -> List[str]:
        """Extract requirements from request."""
        requirements = []
        
        # Extract bullet points
        bullets = re.findall(r'^[-*•]\s*(.+)$', content, re.MULTILINE)
        requirements.extend([b.strip() for b in bullets if b.strip()])
        
        # Extract checkbox items
        checkboxes = re.findall(r'^-\s*\[[ x]\]\s*(.+)$', content, re.MULTILINE)
        requirements.extend([c.strip() for c in checkboxes if c.strip()])
        
        # Limit to top 10
        return requirements[:10]
    
    def _generate_code(self, title: str, content: str, analysis: Dict) -> str:
        """Generate code implementation."""
        lang = analysis['language']
        code_type = analysis['type']
        
        if lang == 'python':
            return self._generate_python_code(title, content, analysis)
        elif lang in ['javascript', 'typescript']:
            return self._generate_js_code(title, content, analysis)
        elif lang == 'bash':
            return self._generate_bash_code(title, content, analysis)
        else:
            return self._generate_generic_code(title, content, analysis)
    
    def _generate_python_code(self, title: str, content: str, analysis: Dict) -> str:
        """Generate Python code."""
        framework = analysis.get('framework', '')
        
        if framework == 'flask':
            code = f'''#!/usr/bin/env python3
"""
{title}

Flask API implementation.
"""

from flask import Flask, request, jsonify
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route('/api/endpoint', methods=['GET'])
def get_endpoint():
    """Handle GET request."""
    logger.info("GET /api/endpoint")
    return jsonify({{'status': 'success', 'data': []}})


@app.route('/api/endpoint', methods=['POST'])
def post_endpoint():
    """Handle POST request."""
    data = request.get_json()
    logger.info(f"POST /api/endpoint with data: {{data}}")
    
    # TODO: Implement business logic
    
    return jsonify({{'status': 'success', 'id': 1}}), 201


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
'''
        elif framework == 'fastapi':
            code = f'''#!/usr/bin/env python3
"""
{title}

FastAPI implementation.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="{title}")


class Item(BaseModel):
    name: str
    value: Optional[str] = None


@app.get("/api/items")
async def get_items():
    """Get all items."""
    logger.info("GET /api/items")
    return {{"items": []}}


@app.post("/api/items")
async def create_item(item: Item):
    """Create a new item."""
    logger.info(f"POST /api/items: {{item}}")
    return {{"id": 1, **item.dict()}}


@app.get("/api/items/{{item_id}}")
async def get_item(item_id: int):
    """Get item by ID."""
    logger.info(f"GET /api/items/{{item_id}}")
    return {{"id": item_id, "name": "Example"}}
'''
        else:
            code = f'''#!/usr/bin/env python3
"""
{title}

Auto-generated Python implementation.
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Result:
    """Result container."""
    success: bool
    data: Any
    error: Optional[str] = None


def main() -> Result:
    """
    Main entry point.
    
    Returns:
        Result object with success status and data
    """
    logger.info("{title} - Starting execution")
    
    try:
        # TODO: Implement main logic here
        result_data = {{}}
        
        logger.info("{title} - Execution complete")
        return Result(success=True, data=result_data)
        
    except Exception as e:
        logger.error(f"{{title}} - Error: {{e}}")
        return Result(success=False, data=None, error=str(e))


def process_item(item: str) -> Dict[str, Any]:
    """
    Process a single item.
    
    Args:
        item: Item to process
        
    Returns:
        Dictionary with processed result
    """
    logger.debug(f"Processing item: {{item}}")
    return {{"item": item, "processed": True}}


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    result = main()
    
    if result.success:
        print(f"Success: {{result.data}}")
    else:
        print(f"Error: {{result.error}}")
'''
        
        return f"```python\n{code}\n```"
    
    def _generate_js_code(self, title: str, content: str, analysis: Dict) -> str:
        """Generate JavaScript/TypeScript code."""
        code = f'''/**
 * {title}
 * 
 * Auto-generated JavaScript implementation.
 */

const logger = {{
    info: (msg) => console.log(`[INFO] ${{msg}}`),
    error: (msg) => console.error(`[ERROR] ${{msg}}`),
    debug: (msg) => console.debug(`[DEBUG] ${{msg}}`)
}};

/**
 * Main entry point
 * @returns {{Promise<Object>}} Result object
 */
async function main() {{
    logger.info("{title} - Starting execution");
    
    try {{
        // TODO: Implement main logic here
        const result = {{ success: true, data: {{}} }};
        
        logger.info("{title} - Execution complete");
        return result;
        
    }} catch (error) {{
        logger.error(`{{title}} - Error: ${{error.message}}`);
        return {{ success: false, error: error.message }};
    }}
}}

/**
 * Process a single item
 * @param {{string}} item - Item to process
 * @returns {{Object}} Processed result
 */
function processItem(item) {{
    logger.debug(`Processing item: ${{item}}`);
    return {{ item, processed: true }};
}}

// Export for testing
module.exports = {{ main, processItem }};

// Run if executed directly
if (require.main === module) {{
    main().then(result => {{
        if (result.success) {{
            console.log("Success:", result.data);
        }} else {{
            console.error("Error:", result.error);
        }}
    }});
}}
'''
        return f"```javascript\n{code}\n```"
    
    def _generate_bash_code(self, title: str, content: str, analysis: Dict) -> str:
        """Generate Bash script."""
        code = f'''#!/bin/bash
#
# {title}
# Auto-generated Bash script
#

set -euo pipefail

# Logging functions
log_info() {{
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}}

log_error() {{
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1" >&2
}}

log_debug() {{
    if [[ "${{DEBUG:-0}}" == "1" ]]; then
        echo "[DEBUG] $(date '+%Y-%m-%d %H:%M:%S') - $1"
    fi
}}

# Main function
main() {{
    log_info "{title} - Starting execution"
    
    # TODO: Implement main logic here
    
    log_info "{title} - Execution complete"
}}

# Process item function
process_item() {{
    local item="$1"
    log_debug "Processing item: $item"
    echo "Processed: $item"
}}

# Run main
main "$@"
'''
        return f"```bash\n{code}\n```"
    
    def _generate_generic_code(self, title: str, content: str, analysis: Dict) -> str:
        """Generate generic code placeholder."""
        return f"```python\n# TODO: Implement {title}\n# Language: {analysis['language']}\n# Type: {analysis['type']}\n```"
    
    def _generate_tests(self, title: str, analysis: Dict) -> str:
        """Generate unit tests."""
        lang = analysis['language']
        
        if lang == 'python':
            tests = f'''```python
#!/usr/bin/env python3
"""
Unit tests for {title}
"""

import unittest
from unittest.mock import patch, MagicMock


class TestImplementation(unittest.TestCase):
    """Test cases for the implementation."""
    
    def test_main_success(self):
        """Test successful execution."""
        # TODO: Implement test
        result = main()
        self.assertTrue(result.success)
    
    def test_process_item(self):
        """Test item processing."""
        # TODO: Implement test
        result = process_item("test")
        self.assertTrue(result.get("processed"))
    
    def test_error_handling(self):
        """Test error handling."""
        # TODO: Implement test
        pass


if __name__ == "__main__":
    unittest.main()
```'''
        else:
            tests = f"```javascript\n// TODO: Add tests for {title}\n```"
        
        return tests
    
    def _generate_documentation(self, title: str, analysis: Dict) -> str:
        """Generate documentation."""
        return f"""
## Documentation

### Overview

**Title:** {title}
**Language:** {analysis['language']}
**Type:** {analysis['type']}
**Framework:** {analysis.get('framework', 'None')}

### Usage

See code implementation above for usage examples.

### Requirements

""" + '\n'.join(f"- {req}" for req in analysis['requirements']) + """

### Notes

- Auto-generated by Coding Agent
- Review and customize as needed
- Add proper error handling for production use
"""
    
    def _combine_output(self, code: str, tests: str, docs: str, analysis: Dict) -> str:
        """Combine all output sections."""
        return f"""
## Code Implementation

**Language:** {analysis['language']}
**Type:** {analysis['type']}
**Complexity:** {analysis['complexity']}

{code}

---

## Tests

{tests}

---

{docs}
"""


if __name__ == "__main__":
    # Test execution
    BASE_DIR = Path(__file__).parent.parent
    VAULT_PATH = BASE_DIR / "notes"

    agent = CodingAgent(
        skills_dir=VAULT_PATH / "Skills",
        logs_dir=BASE_DIR / "Logs"
    )
    
    # Test with sample input
    test_input = {
        'title': 'Create REST API',
        'content': 'Build a Flask REST API with GET and POST endpoints',
        'execution_plan': {'skill': 'coding'}
    }
    
    result = agent.execute(test_input)
    print(f"Success: {result['success']}")
    print(f"Deliverables: {result['deliverables']}")
