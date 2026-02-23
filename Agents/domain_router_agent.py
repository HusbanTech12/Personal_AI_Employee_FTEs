#!/usr/bin/env python3
"""
Domain Router Agent - Gold Tier AI Employee

Classifies incoming tasks and routes them to Personal or Business domains.
Maintains separation of memory and knowledge between domains.

Behavior:
- Read tasks from Inbox/Needs_Action
- Classify task domain (Personal/Business)
- Route to appropriate domain folder
- Maintain separate memory per domain
- Support cross-domain tasks

Workflow:
Inbox → Domain Router → Domain Folder → Planner → Manager → Skill Agents

All classification logic is markdown-driven via domains.md
"""

import os
import sys
import re
import shutil
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DomainRouterAgent")


class Domain(Enum):
    """Available domains."""
    PERSONAL = "Personal"
    BUSINESS = "Business"
    SHARED = "Shared"
    UNKNOWN = "Unknown"


@dataclass
class ClassificationResult:
    """Result of domain classification."""
    domain: Domain
    confidence: float
    category: str
    keywords_matched: List[str]
    skill_detected: Optional[str]
    cross_domain: bool = False
    secondary_domain: Optional[Domain] = None


class DomainRouterAgent:
    """
    Domain Router Agent - Classifies and routes tasks to domains.
    
    Responsibilities:
    - Read classification rules from domains.md
    - Analyze task content and metadata
    - Classify task into Personal or Business domain
    - Route task to appropriate domain folder
    - Maintain domain-specific memory
    - Handle cross-domain tasks
    """
    
    # Domain-specific keywords for classification
    PERSONAL_KEYWORDS = [
        'personal', 'learn', 'study', 'course', 'reminder', 'appointment',
        'health', 'workout', 'meal', 'family', 'friend', 'hobby',
        'journal', 'diary', 'vacation', 'travel personal', 'shopping',
        'home personal', 'car personal', 'insurance personal'
    ]
    
    BUSINESS_KEYWORDS = [
        'business', 'client', 'customer', 'invoice', 'payment', 'marketing',
        'linkedin', 'report', 'meeting', 'project', 'deadline', 'revenue',
        'expense', 'accounting', 'tax business', 'contract', 'proposal',
        'presentation', 'quarterly', 'annual', 'stakeholder', 'investor'
    ]
    
    # Domain-specific skills
    PERSONAL_SKILLS = ['documentation', 'planner', 'research']
    BUSINESS_SKILLS = ['email', 'linkedin_marketing', 'coding', 'documentation', 
                       'planner', 'research', 'approval']
    
    # Category mappings
    PERSONAL_CATEGORIES = {
        'notes': ['note', 'journal', 'thought', 'idea', 'reflection'],
        'learning': ['learn', 'study', 'course', 'tutorial', 'certificate', 'degree'],
        'reminders': ['reminder', 'appointment', 'birthday', 'anniversary', 'todo'],
        'health': ['health', 'workout', 'exercise', 'diet', 'meal', 'medical', 'doctor']
    }
    
    BUSINESS_CATEGORIES = {
        'accounting': ['invoice', 'payment', 'expense', 'receipt', 'budget', 'tax'],
        'marketing': ['marketing', 'linkedin', 'social', 'campaign', 'content', 'post'],
        'reporting': ['report', 'analytics', 'metrics', 'dashboard', 'kpi', 'summary'],
        'projects': ['project', 'deliverable', 'milestone', 'sprint', 'client']
    }
    
    def __init__(self, base_dir: Path, domains_dir: Optional[Path] = None):
        self.base_dir = base_dir
        self.domains_dir = domains_dir or (base_dir / "Domains")
        self.inbox_dir = base_dir / "Inbox"
        self.needs_action_dir = base_dir / "Needs_Action"
        self.logs_dir = base_dir / "Logs"
        
        self.personal_dir = self.domains_dir / "Personal"
        self.business_dir = self.domains_dir / "Business"
        
        self.personal_memory = self.personal_dir / "memory.md"
        self.business_memory = self.business_dir / "memory.md"
        self.shared_memory = self.domains_dir / "shared_memory.md"
        
        self.routing_log: List[Dict] = []
        self.processed_tasks: Set[str] = set()
        
        # Ensure directories exist
        self._ensure_directories()
        
        # Load domain configuration
        self._load_domain_config()
    
    def _ensure_directories(self):
        """Ensure all domain directories exist."""
        for domain_dir in [self.personal_dir, self.business_dir]:
            domain_dir.mkdir(parents=True, exist_ok=True)
            
            # Create category subdirectories
            if domain_dir == self.personal_dir:
                for category in self.PERSONAL_CATEGORIES:
                    (domain_dir / category).mkdir(exist_ok=True)
            else:
                for category in self.BUSINESS_CATEGORIES:
                    (domain_dir / category).mkdir(exist_ok=True)
        
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_domain_config(self):
        """Load domain configuration from domains.md."""
        config_file = self.base_dir / "domains.md"
        
        if not config_file.exists():
            logger.warning("domains.md not found, using default configuration")
            return
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse configuration (simplified YAML-like parsing)
            logger.info("Loaded domain configuration from domains.md")
            
        except Exception as e:
            logger.error(f"Failed to load domain config: {e}")
    
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
    
    def classify_domain(self, file_path: Path) -> ClassificationResult:
        """
        Classify task into Personal or Business domain.
        
        Uses multiple signals:
        1. Frontmatter domain hint
        2. Keyword matching
        3. Skill detection
        4. Content analysis
        """
        content, frontmatter = self.read_task(file_path)
        content_lower = content.lower()
        title = frontmatter.get('title', '').lower()
        
        # Check for explicit domain in frontmatter
        if 'domain' in frontmatter:
            domain_str = frontmatter['domain'].lower()
            if 'personal' in domain_str:
                return ClassificationResult(
                    domain=Domain.PERSONAL,
                    confidence=1.0,
                    category='explicit',
                    keywords_matched=['domain:personal'],
                    skill_detected=frontmatter.get('skill')
                )
            elif 'business' in domain_str:
                return ClassificationResult(
                    domain=Domain.BUSINESS,
                    confidence=1.0,
                    category='explicit',
                    keywords_matched=['domain:business'],
                    skill_detected=frontmatter.get('skill')
                )
        
        # Keyword matching
        personal_matches = []
        business_matches = []
        
        for keyword in self.PERSONAL_KEYWORDS:
            if keyword in content_lower or keyword in title:
                personal_matches.append(keyword)
        
        for keyword in self.BUSINESS_KEYWORDS:
            if keyword in content_lower or keyword in title:
                business_matches.append(keyword)
        
        # Skill detection
        skill = frontmatter.get('skill', '')
        skill_detected = None
        
        if skill in self.PERSONAL_SKILLS and skill not in self.BUSINESS_SKILLS:
            skill_detected = skill
            personal_matches.append(f'skill:{skill}')
        elif skill in self.BUSINESS_SKILLS:
            skill_detected = skill
            if skill in ['email', 'linkedin_marketing', 'approval']:
                business_matches.append(f'skill:{skill}')
        
        # Calculate confidence
        personal_score = len(personal_matches)
        business_score = len(business_matches)
        
        total_matches = personal_score + business_score
        
        if total_matches == 0:
            # No matches - default to Personal
            return ClassificationResult(
                domain=Domain.PERSONAL,
                confidence=0.5,
                category='default',
                keywords_matched=[],
                skill_detected=skill if skill else None
            )
        
        # Determine domain
        if personal_score > business_score:
            confidence = personal_score / total_matches
            domain = Domain.PERSONAL
        elif business_score > personal_score:
            confidence = business_score / total_matches
            domain = Domain.BUSINESS
        else:
            # Tie - use skill as tiebreaker
            if skill in self.BUSINESS_SKILLS:
                domain = Domain.BUSINESS
                confidence = 0.6
            else:
                domain = Domain.PERSONAL
                confidence = 0.6
        
        # Check for cross-domain
        cross_domain = False
        secondary_domain = None
        
        if personal_score > 0 and business_score > 0:
            cross_domain = True
            if domain == Domain.PERSONAL:
                secondary_domain = Domain.BUSINESS
            else:
                secondary_domain = Domain.PERSONAL
        
        # Determine category
        category = self._determine_category(content_lower, domain)
        
        return ClassificationResult(
            domain=domain,
            confidence=round(confidence, 2),
            category=category,
            keywords_matched=personal_matches if domain == Domain.PERSONAL else business_matches,
            skill_detected=skill_detected,
            cross_domain=cross_domain,
            secondary_domain=secondary_domain
        )
    
    def _determine_category(self, content: str, domain: Domain) -> str:
        """Determine specific category within domain."""
        categories = self.PERSONAL_CATEGORIES if domain == Domain.PERSONAL else self.BUSINESS_CATEGORIES
        
        for category, keywords in categories.items():
            for keyword in keywords:
                if keyword in content:
                    return category
        
        return 'general'
    
    def route_task(self, file_path: Path, classification: ClassificationResult) -> Optional[Path]:
        """Route task to appropriate domain folder."""
        try:
            # Determine destination
            if classification.domain == Domain.PERSONAL:
                dest_dir = self.personal_dir / classification.category
            elif classification.domain == Domain.BUSINESS:
                dest_dir = self.business_dir / classification.category
            else:
                dest_dir = self.needs_action_dir  # Fallback
            
            # Ensure destination exists
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy task to domain folder
            dest_path = dest_dir / file_path.name
            
            # Read and add domain metadata
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add domain metadata if not present
            if 'domain:' not in content:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                domain_metadata = f"""
# Domain Information
domain: {classification.domain.value}
domain_category: {classification.category}
domain_confidence: {classification.confidence}
routed_at: {timestamp}
"""
                # Insert after frontmatter
                if '---\n' in content:
                    parts = content.split('---\n', 2)
                    if len(parts) >= 2:
                        content = f"---\n{parts[1]}---\n{domain_metadata}{parts[2] if len(parts) > 2 else ''}"
            
            with open(dest_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Routed {file_path.name} → {classification.domain.value}/{classification.category}")
            
            # Log routing
            self._log_routing(file_path.name, classification)
            
            # Update domain memory
            self._update_domain_memory(classification, file_path.name)
            
            return dest_path
            
        except Exception as e:
            logger.error(f"Failed to route task: {e}")
            return None
    
    def _log_routing(self, task_name: str, classification: ClassificationResult):
        """Log routing decision."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        self.routing_log.append({
            'timestamp': timestamp,
            'task': task_name,
            'domain': classification.domain.value,
            'category': classification.category,
            'confidence': classification.confidence,
            'cross_domain': classification.cross_domain
        })
        
        # Write to routing log file
        log_file = self.logs_dir / "domain_routing_log.md"
        
        try:
            if not log_file.exists():
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write("# Domain Routing Log\n\n")
                    f.write("| Timestamp | Task | Domain | Category | Confidence |\n")
                    f.write("|-----------|------|--------|----------|------------|\n")
            
            entry = f"| {timestamp} | {task_name} | {classification.domain.value} | {classification.category} | {classification.confidence} |\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(entry)
            
        except Exception as e:
            logger.error(f"Failed to log routing: {e}")
    
    def _update_domain_memory(self, classification: ClassificationResult, task_name: str):
        """Update domain-specific memory."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if classification.domain == Domain.PERSONAL:
            memory_file = self.personal_memory
            domain_name = "Personal"
        elif classification.domain == Domain.BUSINESS:
            memory_file = self.business_memory
            domain_name = "Business"
        else:
            return
        
        try:
            entry = f"\n- [{timestamp}] Processed: {task_name} (Category: {classification.category})"
            
            if memory_file.exists():
                with open(memory_file, 'a', encoding='utf-8') as f:
                    f.write(entry)
            else:
                with open(memory_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {domain_name} Domain Memory\n\n")
                    f.write("## Task History\n")
                    f.write(entry)
            
            logger.debug(f"Updated {domain_name} domain memory")
            
        except Exception as e:
            logger.error(f"Failed to update domain memory: {e}")
    
    def scan_inbox(self) -> List[Path]:
        """Scan Inbox for tasks to classify."""
        tasks = []
        
        if not self.inbox_dir.exists():
            return tasks
        
        for file_path in self.inbox_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.md':
                if file_path.name not in self.processed_tasks:
                    tasks.append(file_path)
        
        return tasks
    
    def process_task(self, file_path: Path) -> bool:
        """Process a single task: classify and route."""
        logger.info(f"Classifying task: {file_path.name}")
        
        # Classify domain
        classification = self.classify_domain(file_path)
        
        logger.info(f"  Domain: {classification.domain.value}")
        logger.info(f"  Category: {classification.category}")
        logger.info(f"  Confidence: {classification.confidence}")
        logger.info(f"  Keywords: {', '.join(classification.keywords_matched[:3])}")
        
        if classification.cross_domain:
            logger.info(f"  Cross-domain: Also relevant to {classification.secondary_domain.value}")
        
        # Route to domain
        dest_path = self.route_task(file_path, classification)
        
        if dest_path:
            self.processed_tasks.add(file_path.name)
            return True
        
        return False
    
    def get_status(self) -> Dict:
        """Get router status."""
        return {
            'tasks_routed': len(self.routing_log),
            'personal_tasks': sum(1 for r in self.routing_log if r['domain'] == 'Personal'),
            'business_tasks': sum(1 for r in self.routing_log if r['domain'] == 'Business'),
            'cross_domain_tasks': sum(1 for r in self.routing_log if r['cross_domain'])
        }
    
    def run(self):
        """Main domain router loop."""
        logger.info("=" * 60)
        logger.info("Domain Router Agent started")
        logger.info(f"Domains directory: {self.domains_dir}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Domains:")
        logger.info(f"  - Personal: {self.personal_dir}")
        logger.info(f"  - Business: {self.business_dir}")
        logger.info("")
        logger.info("Workflow: Inbox → Domain Router → Domain → Planner → Manager → Skills")
        logger.info("")
        
        while True:
            try:
                # Scan inbox for new tasks
                tasks = self.scan_inbox()
                
                if tasks:
                    logger.info(f"Found {len(tasks)} task(s) to classify")
                    
                    for task_file in tasks:
                        self.process_task(task_file)
                    
                    logger.info("Waiting for more tasks...")
                
                # Also check Needs_Action for unclassified tasks
                na_tasks = self._scan_needs_action()
                for task_file in na_tasks:
                    self.process_task(task_file)
                
                # Wait before next scan
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("")
                logger.info("Domain Router Agent stopping...")
                break
            except Exception as e:
                logger.error(f"Error in domain router loop: {e}")
                time.sleep(5)
    
    def _scan_needs_action(self) -> List[Path]:
        """Scan Needs_Action for unclassified tasks."""
        tasks = []
        
        if not self.needs_action_dir.exists():
            return tasks
        
        for file_path in self.needs_action_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.md':
                # Check if already has domain
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if 'domain:' not in content and file_path.name not in self.processed_tasks:
                    tasks.append(file_path)
        
        return tasks


# Import time for the run loop
import time

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    agent = DomainRouterAgent(base_dir=BASE_DIR)
    agent.run()
