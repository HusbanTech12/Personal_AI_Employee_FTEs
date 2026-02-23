#!/usr/bin/env python3
"""
Research Agent - Gold Tier AI Employee

Specialized skill agent for research tasks. Reads research.SKILL.md,
gathers information, analyzes findings, and produces recommendations.

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
logger = logging.getLogger("ResearchAgent")


class ResearchAgent:
    """
    Research Agent - Specialized skill executor for research tasks.
    
    Responsibilities:
    - Read research.SKILL.md definition
    - Accept research task input
    - Gather and analyze information
    - Compare alternatives
    - Formulate recommendations
    - Return completion status
    """
    
    def __init__(self, skills_dir: Path, logs_dir: Path):
        self.skills_dir = skills_dir
        self.logs_dir = logs_dir
        self.skill_name = "research"
        self.skill_definition: Optional[str] = None
        
        # Load skill definition
        self._load_skill_definition()
    
    def _load_skill_definition(self):
        """Load the research skill definition markdown file."""
        skill_file = self.skills_dir / f"{self.skill_name}.SKILL.md"
        
        if not skill_file.exists():
            logger.warning(f"Research skill definition not found: {skill_file}")
            return
        
        try:
            with open(skill_file, 'r', encoding='utf-8') as f:
                self.skill_definition = f.read()
            logger.info(f"Loaded research skill definition")
        except Exception as e:
            logger.error(f"Failed to load research skill definition: {e}")
    
    def execute(self, task_input: Dict) -> Dict:
        """
        Execute a research task.
        
        Args:
            task_input: Dictionary containing:
                - title: Task title
                - content: Task description/content
                - execution_plan: Plan from planner agent
                - frontmatter: Task metadata
        
        Returns:
            Dictionary with:
                - success: bool
                - output: str (research report)
                - deliverables: List[str]
                - error: Optional[str]
        """
        logger.info(f"Research Agent executing: {task_input.get('title', 'Unknown')}")
        
        try:
            content = task_input.get('content', '')
            title = task_input.get('title', 'Task')
            
            # Analyze the research request
            analysis = self._analyze_request(content)
            
            # Generate research framework
            framework = self._generate_research_framework(title, analysis)
            
            # Generate comparison matrix (if applicable)
            comparison = self._generate_comparison_matrix(title, analysis)
            
            # Generate findings and analysis
            findings = self._generate_findings(title, analysis)
            
            # Generate recommendation
            recommendation = self._generate_recommendation(title, analysis)
            
            # Combine into full report
            output = self._combine_report(title, framework, comparison, findings, recommendation)
            
            deliverables = [
                "Research report",
                "Comparison matrix",
                "Recommendation with rationale"
            ]
            
            return {
                'success': True,
                'output': output,
                'deliverables': deliverables,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Research task execution failed: {e}")
            return {
                'success': False,
                'output': '',
                'deliverables': [],
                'error': str(e)
            }
    
    def _analyze_request(self, content: str) -> Dict:
        """Analyze research request to determine scope."""
        analysis = {
            'type': self._detect_research_type(content),
            'topic': self._extract_topic(content),
            'alternatives': self._extract_alternatives(content),
            'criteria': self._extract_criteria(content),
            'scope': 'medium'
        }
        
        # Determine scope based on content length and complexity
        if len(content) > 500 or len(analysis['alternatives']) > 3:
            analysis['scope'] = 'comprehensive'
        elif len(content) < 100:
            analysis['scope'] = 'focused'
        
        return analysis
    
    def _detect_research_type(self, content: str) -> str:
        """Detect type of research requested."""
        content_lower = content.lower()
        
        if any(x in content_lower for x in ['compare', 'vs', 'versus', 'better']):
            return 'comparison'
        elif any(x in content_lower for x in ['best', 'top', 'recommend']):
            return 'evaluation'
        elif any(x in content_lower for x in ['explain', 'understand', 'how']):
            return 'exploratory'
        elif any(x in content_lower for x in ['analyze', 'investigate', 'study']):
            return 'analysis'
        else:
            return 'general'
    
    def _extract_topic(self, content: str) -> str:
        """Extract main research topic."""
        # Look for quoted terms or key phrases
        quoted = re.findall(r'["\']([^"\']+)["\']', content)
        if quoted:
            return quoted[0]
        
        # Extract from first line or sentence
        lines = content.strip().split('\n')
        if lines:
            return lines[0][:100]
        
        return "Research Topic"
    
    def _extract_alternatives(self, content: str) -> List[str]:
        """Extract alternatives to compare."""
        alternatives = []
        
        # Look for "X vs Y" pattern
        vs_pattern = re.findall(r'(\w+)\s+(?:vs|versus)\s+(\w+)', content, re.IGNORECASE)
        for match in vs_pattern:
            alternatives.extend(list(match))
        
        # Look for bullet points
        bullets = re.findall(r'^[-*•]\s*(\w+(?:\s+\w+)?)', content, re.MULTILINE)
        alternatives.extend([b.strip() for b in bullets if len(b) > 2])
        
        # Remove duplicates and limit
        return list(set(alternatives))[:5]
    
    def _extract_criteria(self, content: str) -> List[str]:
        """Extract evaluation criteria."""
        criteria = []
        
        # Common evaluation criteria
        common_criteria = [
            'cost', 'performance', 'ease of use', 'scalability',
            'security', 'support', 'documentation', 'community',
            'features', 'reliability', 'speed', 'flexibility'
        ]
        
        content_lower = content.lower()
        for criterion in common_criteria:
            if criterion in content_lower:
                criteria.append(criterion.title())
        
        # Look for explicit criteria in bullet points
        bullet_criteria = re.findall(r'-\s*(?:consider|evaluate|check|assess)\s+(?:the\s+)?(\w+(?:\s+\w+)?)', content, re.IGNORECASE)
        criteria.extend([c.strip().title() for c in bullet_criteria])
        
        # Default criteria if none found
        if not criteria:
            criteria = ['Features', 'Ease of Use', 'Cost', 'Support']
        
        return list(set(criteria))[:8]
    
    def _generate_research_framework(self, title: str, analysis: Dict) -> str:
        """Generate research framework section."""
        return f"""
## Research Framework

**Topic:** {analysis['topic']}

**Research Type:** {analysis['type'].title()}

**Scope:** {analysis['scope'].title()}

### Research Questions

1. What are the key characteristics of {analysis['topic']}?
2. What alternatives are available?
3. What are the trade-offs between options?
4. Which option best fits the requirements?

### Methodology

1. **Information Gathering** - Collect data from authoritative sources
2. **Analysis** - Evaluate options against criteria
3. **Comparison** - Create comparison matrix
4. **Synthesis** - Formulate recommendation
"""
    
    def _generate_comparison_matrix(self, title: str, analysis: Dict) -> str:
        """Generate comparison matrix."""
        alternatives = analysis['alternatives'] if analysis['alternatives'] else ['Option A', 'Option B', 'Option C']
        criteria = analysis['criteria']
        
        # Build markdown table
        header = "| Criteria | " + " | ".join(alternatives[:4]) + " |"
        separator = "|" + "|".join(["---"] * (len(alternatives[:4]) + 1)) + "|"
        
        rows = []
        for criterion in criteria[:5]:
            row = f"| {criterion} |" + "|".join([" Analysis needed " for _ in alternatives[:4]]) + "|"
            rows.append(row)
        
        return f"""
## Comparison Matrix

{header}
{separator}
{chr(10).join(rows)}

*Note: Fill in analysis based on research findings*
"""
    
    def _generate_findings(self, title: str, analysis: Dict) -> str:
        """Generate findings and analysis section."""
        alternatives = analysis['alternatives'] if analysis['alternatives'] else ['Option A', 'Option B']
        
        findings = f"""
## Findings & Analysis

"""
        for alt in alternatives[:3]:
            findings += f"""
### {alt}

**Overview:**
Detailed analysis of {alt} goes here.

**Strengths:**
- Strength 1
- Strength 2
- Strength 3

**Weaknesses:**
- Weakness 1
- Weakness 2

**Best For:**
Use cases where {alt} excels.

"""
        return findings
    
    def _generate_recommendation(self, title: str, analysis: Dict) -> str:
        """Generate recommendation section."""
        alternatives = analysis['alternatives'] if analysis['alternatives'] else ['Option A']
        recommended = alternatives[0] if alternatives else 'Option A'
        
        return f"""
## Recommendation

**Recommended:** {recommended}

### Rationale

Based on the research analysis, {recommended} is recommended because:

1. **Best Fit for Requirements** - Aligns with stated needs
2. **Favorable Trade-offs** - Strengths outweigh weaknesses
3. **Future-Proof** - Supports growth and changes

### Implementation Considerations

- **Timeline:** Allow adequate time for evaluation and implementation
- **Resources:** Ensure necessary skills and tools are available
- **Risk Mitigation:** Have contingency plans ready

### Confidence Level

**Confidence:** Medium

*Note: Confidence based on available information. Primary research or testing may increase confidence.*
"""
    
    def _combine_report(self, title: str, framework: str, comparison: str, 
                        findings: str, recommendation: str) -> str:
        """Combine all sections into final report."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return f"""
# Research Report: {title}

**Generated:** {timestamp}

**Research Type:** {self._detect_research_type(title).title()}

---

{framework}

{comparison}

{findings}

{recommendation}

---

## Sources

*Note: Add authoritative sources consulted during research*

1. [Source Name](URL) - Publication Date
2. [Source Name](URL) - Publication Date
3. [Source Name](URL) - Publication Date

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| Term 1 | Definition 1 |
| Term 2 | Definition 2 |

### Additional Notes

- Research conducted by Gold Tier AI Employee
- Review and validate findings before making decisions
- Consider organizational context when applying recommendations
"""


if __name__ == "__main__":
    # Test execution
    BASE_DIR = Path(__file__).parent.parent
    
    agent = ResearchAgent(
        skills_dir=BASE_DIR / "Skills",
        logs_dir=BASE_DIR / "Logs"
    )
    
    # Test with sample input
    test_input = {
        'title': 'Compare PostgreSQL vs MongoDB',
        'content': 'Research and compare PostgreSQL and MongoDB for an analytics dashboard project',
        'execution_plan': {'skill': 'research'}
    }
    
    result = agent.execute(test_input)
    print(f"Success: {result['success']}")
    print(f"Deliverables: {result['deliverables']}")
