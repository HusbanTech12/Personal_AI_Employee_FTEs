#!/usr/bin/env python3
"""
Documentation Agent - Gold+ Tier AI Employee

Automatically generates and maintains system documentation.

Generates:
- ARCHITECTURE.md (system overview, components, data flows)
- LESSONS_LEARNED.md (execution insights, patterns, best practices)

Auto-updates after:
- New agent registrations
- Task completions
- Failure recoveries
- Daily scheduled updates

Usage:
    python documentation_agent.py

Runs continuously, updating documentation based on system activity.
"""

import os
import sys
import json
import logging
import time
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("DocumentationAgent")


@dataclass
class AgentInfo:
    """Information about a registered agent."""
    name: str
    file: str
    priority: str = "normal"
    status: str = "unknown"
    registered_at: str = ""
    last_active: str = ""
    executions: int = 0
    failures: int = 0


@dataclass
class MCPServerInfo:
    """Information about an MCP server."""
    name: str
    port: int
    host: str = "127.0.0.1"
    status: str = "unknown"
    actions: List[str] = field(default_factory=list)
    calls_today: int = 0
    errors_today: int = 0


@dataclass
class LessonLearned:
    """A lesson learned from execution."""
    timestamp: str
    category: str  # success, failure, recovery, optimization
    title: str
    description: str
    context: str = ""
    impact: str = ""
    recommendation: str = ""
    tags: List[str] = field(default_factory=list)


class DocumentationAgent:
    """
    Documentation Agent - Auto-generates system documentation.
    """
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.logs_dir = base_dir / "Logs"
        self.audit_dir = base_dir / "Audit"
        self.agents_dir = base_dir / "Agents"
        self.mcp_dir = base_dir / "MCP"
        self.skills_dir = base_dir / "Skills"
        
        # Documentation files
        self.architecture_file = base_dir / "ARCHITECTURE.md"
        self.lessons_file = base_dir / "LESSONS_LEARNED.md"
        
        # Registries
        self.agents: Dict[str, AgentInfo] = {}
        self.mcp_servers: Dict[str, MCPServerInfo] = {}
        self.lessons: List[LessonLearned] = []
        
        # Statistics
        self.stats = {
            'total_executions': 0,
            'total_failures': 0,
            'total_recoveries': 0,
            'docs_updated': 0,
            'start_time': datetime.now().isoformat()
        }
        
        # Ensure directories exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing data
        self._load_state()
        
        # Auto-discover agents and MCPs
        self._discover_components()
    
    def _load_state(self):
        """Load documentation agent state."""
        state_file = self.logs_dir / "documentation_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                self.stats.update(state.get('stats', {}))
                logger.info(f"Loaded documentation state")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
    
    def _save_state(self):
        """Save documentation agent state."""
        state_file = self.logs_dir / "documentation_state.json"
        
        try:
            with open(state_file, 'w') as f:
                json.dump({
                    'stats': self.stats,
                    'agents_count': len(self.agents),
                    'mcp_count': len(self.mcp_servers),
                    'lessons_count': len(self.lessons),
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def _discover_components(self):
        """Auto-discover agents and MCP servers."""
        # Discover agents
        if self.agents_dir.exists():
            for agent_file in self.agents_dir.glob("*_agent.py"):
                self.register_agent(agent_file.name)
        
        # Discover MCP servers
        if self.mcp_dir.exists():
            for mcp_subdir in self.mcp_dir.iterdir():
                if mcp_subdir.is_dir():
                    self.register_mcp_server(mcp_subdir.name)
        
        logger.info(f"Discovered {len(self.agents)} agents and {len(self.mcp_servers)} MCP servers")
    
    def register_agent(self, agent_file: str, priority: str = "normal"):
        """Register an agent."""
        agent_name = agent_file.replace("_agent.py", "")
        
        self.agents[agent_name] = AgentInfo(
            name=agent_name,
            file=agent_file,
            priority=priority,
            registered_at=datetime.now().isoformat(),
            last_active=datetime.now().isoformat()
        )
        
        logger.info(f"Registered agent: {agent_name}")
        
        # Update architecture doc
        self._update_architecture()
    
    def register_mcp_server(self, mcp_name: str, port: int = 0, actions: List[str] = None):
        """Register an MCP server."""
        # Try to discover port from file
        discovered_port = port
        discovered_actions = actions or []
        
        mcp_file = self.mcp_dir / mcp_name / f"{mcp_name}_server.py"
        if mcp_file.exists():
            try:
                with open(mcp_file, 'r') as f:
                    content = f.read()
                
                # Discover port
                port_match = re.search(r'PORT\s*=\s*int\(.*?(\d+)', content)
                if port_match:
                    discovered_port = int(port_match.group(1))
                
                # Discover actions from docstrings or endpoint definitions
                action_matches = re.findall(r'["\']/(.*?)["\']', content)
                discovered_actions = list(set(action_matches))[:10]
                
            except Exception as e:
                logger.warning(f"Failed to parse MCP file: {e}")
        
        self.mcp_servers[mcp_name] = MCPServerInfo(
            name=mcp_name,
            port=discovered_port,
            actions=discovered_actions
        )
        
        logger.info(f"Registered MCP server: {mcp_name}")
        
        # Update architecture doc
        self._update_architecture()
    
    def record_execution(self, agent_name: str, task_id: str = "", success: bool = True):
        """Record an execution for documentation."""
        self.stats['total_executions'] = self.stats.get('total_executions', 0) + 1
        
        if agent_name in self.agents:
            self.agents[agent_name].executions += 1
            self.agents[agent_name].last_active = datetime.now().isoformat()
            
            if not success:
                self.agents[agent_name].failures += 1
                self.stats['total_failures'] = self.stats.get('total_failures', 0) + 1
        
        # Update architecture
        self._update_architecture()
    
    def record_lesson(self, category: str, title: str, description: str,
                     context: str = "", impact: str = "", 
                     recommendation: str = "", tags: List[str] = None):
        """Record a lesson learned."""
        lesson = LessonLearned(
            timestamp=datetime.now().isoformat(),
            category=category,
            title=title,
            description=description[:500],  # Truncate long descriptions
            context=context,
            impact=impact,
            recommendation=recommendation,
            tags=tags or []
        )
        
        self.lessons.append(lesson)
        self.stats['total_recoveries'] = self.stats.get('total_recoveries', 0) + 1
        
        # Update lessons doc
        self._update_lessons_learned()
        
        logger.info(f"Recorded lesson: {title}")
    
    def _update_architecture(self):
        """Generate/update ARCHITECTURE.md."""
        logger.info("Updating ARCHITECTURE.md...")
        
        content = f"""# AI Employee System Architecture

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Version:** Gold Tier
**Session:** {self.stats.get('start_time', 'unknown')[:19].replace('T', ' ')}

---

## System Overview

The AI Employee is an autonomous multi-agent system that processes tasks through a pipeline of specialized agents, MCP servers, and skills.

### Key Components

| Component | Count | Description |
|-----------|-------|-------------|
| Agents | {len(self.agents)} | Autonomous task processors |
| MCP Servers | {len(self.mcp_servers)} | Service integration layer |
| Skills | {len(list(self.skills_dir.glob('*.SKILL.md')))} | Capability definitions |

---

## Agent Registry

| Agent | File | Priority | Executions | Failures | Status |
|-------|------|----------|------------|----------|--------|
"""
        
        for name, info in sorted(self.agents.items()):
            content += f"| {name} | {info.file} | {info.priority} | {info.executions} | {info.failures} | {info.status} |\n"
        
        content += f"""
---

## MCP Server Map

| Server | Port | Host | Actions | Status |
|--------|------|------|---------|--------|
"""
        
        for name, info in sorted(self.mcp_servers.items()):
            actions_str = ', '.join(info.actions[:5]) if info.actions else 'N/A'
            content += f"| {name} | {info.port} | {info.host} | {actions_str} | {info.status} |\n"
        
        content += f"""
---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      AI Employee System                         │
└─────────────────────────────────────────────────────────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Inbox     │ ──→ │   Domain    │ ──→ │   Planner   │
│  (Watch)    │     │   Router    │     │   Agent     │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Manager Agent                              │
│              (Skill Selection & Orchestration)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Skill Agents   │ │  Approval       │ │  Resilience     │
│  (Execution)    │ │  Agent          │ │  Agent          │
└────────┬────────┘ └─────────────────┘ └─────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      MCP Server Layer                           │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │  Email  │ │LinkedIn │ │Accounting│ │ Social  │ │Automation│ │
│  │ :8765   │ │ :8766   │ │ :8767   │ │ :8768   │ │ :8769   │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Task Processing Pipeline

1. **Inbox Detection** → `filesystem_watcher.py`
2. **Domain Classification** → `domain_router_agent.py`
3. **Task Planning** → `planner_agent.py`
4. **Skill Selection** → `manager_agent.py`
5. **Execution** → Skill-specific agent
6. **Validation** → `validator_agent.py`
7. **Memory Update** → `memory_agent.py`

### Cross-Cutting Concerns

| Concern | Agent |
|---------|-------|
| Resilience | `resilience_agent.py` |
| Audit | `audit_agent.py` |
| Documentation | `documentation_agent.py` |
| Scheduling | `scheduler_agent.py` |
| CEO Briefing | `ceo_briefing_agent.py` |

---

## Configuration

### Directory Structure

```
AI_Employee_Vault/
├── Agents/           # Agent executables
├── Skills/           # Skill definitions (*.SKILL.md)
├── MCP/              # MCP servers
├── Domains/          # Domain separation
│   ├── Personal/
│   └── Business/
├── Logs/             # System logs
├── Audit/            # Audit trails
└── Done/             # Completed tasks
```

### Key Configuration Files

| File | Purpose |
|------|---------|
| `domains.md` | Domain routing rules |
| `schedule.md` | Scheduled tasks |
| `Company_Handbook.md` | System rules |
| `Dashboard.md` | System status |

---

## Statistics

| Metric | Value |
|--------|-------|
| Total Executions | {self.stats.get('total_executions', 0)} |
| Total Failures | {self.stats.get('total_failures', 0)} |
| Total Recoveries | {self.stats.get('total_recoveries', 0)} |
| Documentation Updates | {self.stats.get('docs_updated', 0)} |
| Uptime | {self._format_uptime()} |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| Gold Tier | 2026-02-24 | Multi-agent with domains |
| Silver Tier | 2026-02-23 | MCP integration |
| Bronze Tier | 2026-02-20 | Initial release |

---

*Generated automatically by AI Employee Documentation Agent*
"""
        
        try:
            with open(self.architecture_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.stats['docs_updated'] = self.stats.get('docs_updated', 0) + 1
            self._save_state()
            logger.info(f"ARCHITECTURE.md updated")
            
        except Exception as e:
            logger.error(f"Failed to update ARCHITECTURE.md: {e}")
    
    def _update_lessons_learned(self):
        """Generate/update LESSONS_LEARNED.md."""
        logger.info("Updating LESSONS_LEARNED.md...")
        
        # Group lessons by category
        by_category: Dict[str, List[LessonLearned]] = {}
        for lesson in self.lessons:
            if lesson.category not in by_category:
                by_category[lesson.category] = []
            by_category[lesson.category].append(lesson)
        
        content = f"""# Lessons Learned

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total Lessons:** {len(self.lessons)}

---

## Summary

| Category | Count |
|----------|-------|
"""
        
        for category, lessons in by_category.items():
            content += f"| {category.title()} | {len(lessons)} |\n"
        
        content += f"""
---

## Successes

"""
        
        for lesson in by_category.get('success', []):
            content += self._format_lesson(lesson)
        
        if 'success' not in by_category:
            content += "*No successes recorded yet*\n"
        
        content += f"""
---

## Failures & Recoveries

"""
        
        for lesson in by_category.get('failure', []) + by_category.get('recovery', []):
            content += self._format_lesson(lesson)
        
        if 'failure' not in by_category and 'recovery' not in by_category:
            content += "*No failures recorded yet*\n"
        
        content += f"""
---

## Optimizations

"""
        
        for lesson in by_category.get('optimization', []):
            content += self._format_lesson(lesson)
        
        if 'optimization' not in by_category:
            content += "*No optimizations recorded yet*\n"
        
        content += f"""
---

## Best Practices

### System Operation

1. **Start all agents** using `bash run_agents.sh`
2. **Monitor health** via Dashboard.md
3. **Review audit logs** in Audit/summary/
4. **Check failures** in Logs/failures/

### Task Processing

1. **Drop tasks** in Inbox/ folder
2. **Monitor progress** in Needs_Action/
3. **Review completions** in Done/
4. **Check CEO briefing** for weekly summary

### Troubleshooting

1. **Check logs** in Logs/ directory
2. **Review audit trail** in Audit/
3. **Check agent status** in ARCHITECTURE.md
4. **Review lessons** in this document

---

## Pattern Recognition

### Common Failure Patterns

"""
        
        # Analyze failure patterns
        failure_patterns = self._analyze_failure_patterns()
        for pattern in failure_patterns:
            content += f"- **{pattern['pattern']}**: {pattern['count']} occurrences\n"
        
        if not failure_patterns:
            content += "*No patterns identified yet*\n"
        
        content += f"""
### Successful Recovery Patterns

"""
        
        recovery_patterns = self._analyze_recovery_patterns()
        for pattern in recovery_patterns:
            content += f"- **{pattern['pattern']}**: {pattern['count']} successful recoveries\n"
        
        if not recovery_patterns:
            content += "*No patterns identified yet*\n"
        
        content += f"""
---

## Knowledge Base

### Agent-Specific Learnings

"""
        
        for name, info in sorted(self.agents.items()):
            if info.failures > 0:
                content += f"""
#### {name}

- Executions: {info.executions}
- Failures: {info.failures}
- Success Rate: {(1 - info.failures/max(info.executions,1)) * 100:.1f}%

"""
        
        content += f"""
---

## Recommendations

Based on accumulated learnings:

1. **Monitor high-failure agents** - Check agents with >10% failure rate
2. **Review MCP timeouts** - Adjust timeout settings for slow services
3. **Implement circuit breakers** - Prevent cascade failures
4. **Document runbooks** - Create troubleshooting guides

---

## Appendix

### Glossary

| Term | Definition |
|------|------------|
| MCP | Model Context Protocol - service integration layer |
| Skill | Capability definition in markdown format |
| Domain | Task classification (Personal/Business) |
| Fallback | Alternative action when primary fails |

### Related Documents

- [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
- [Dashboard.md](Dashboard.md) - System status
- [Company_Handbook.md](Company_Handbook.md) - System rules
- [Audit/summary/](Audit/summary/) - Daily audit summaries

---

*Generated automatically by AI Employee Documentation Agent*
"""
        
        try:
            with open(self.lessons_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"LESSONS_LEARNED.md updated")
            
        except Exception as e:
            logger.error(f"Failed to update LESSONS_LEARNED.md: {e}")
    
    def _format_lesson(self, lesson: LessonLearned) -> str:
        """Format a lesson for markdown."""
        tags_str = ', '.join(lesson.tags) if lesson.tags else ''
        
        return f"""
### {lesson.title}

**When:** {lesson.timestamp[:19].replace('T', ' ')}
**Category:** {lesson.category}
{f'**Tags:** {tags_str}' if tags_str else ''}

**Description:**
{lesson.description}

{f'**Context:** {lesson.context}' if lesson.context else ''}
{f'**Impact:** {lesson.impact}' if lesson.impact else ''}
{f'**Recommendation:** {lesson.recommendation}' if lesson.recommendation else ''}

---
"""
    
    def _analyze_failure_patterns(self) -> List[Dict]:
        """Analyze failure patterns from audit logs."""
        patterns = []
        
        # Read failure audit log
        failure_log = self.audit_dir / "failures" / datetime.now().strftime('%Y-%m') / "failures.log"
        
        if failure_log.exists():
            try:
                with open(failure_log, 'r') as f:
                    error_types: Dict[str, int] = {}
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            error_type = event.get('error_type', 'Unknown')
                            error_types[error_type] = error_types.get(error_type, 0) + 1
                        except json.JSONDecodeError:
                            continue
                    
                    for error_type, count in sorted(error_types.items(), key=lambda x: -x[1])[:5]:
                        patterns.append({'pattern': error_type, 'count': count})
                        
            except Exception as e:
                logger.warning(f"Failed to analyze failures: {e}")
        
        return patterns
    
    def _analyze_recovery_patterns(self) -> List[Dict]:
        """Analyze recovery patterns from audit logs."""
        patterns = []
        
        # Read retry audit log
        retry_log = self.audit_dir / "retries" / datetime.now().strftime('%Y-%m') / "retries.log"
        
        if retry_log.exists():
            try:
                with open(retry_log, 'r') as f:
                    outcomes: Dict[str, int] = {}
                    for line in f:
                        try:
                            event = json.loads(line.strip())
                            outcome = event.get('outcome', 'unknown')
                            outcomes[outcome] = outcomes.get(outcome, 0) + 1
                        except json.JSONDecodeError:
                            continue
                    
                    for outcome, count in sorted(outcomes.items(), key=lambda x: -x[1]):
                        if outcome == 'success':
                            patterns.append({'pattern': 'Retry with backoff', 'count': count})
                            
            except Exception as e:
                logger.warning(f"Failed to analyze recoveries: {e}")
        
        return patterns
    
    def _format_uptime(self) -> str:
        """Format system uptime."""
        start_str = self.stats.get('start_time', datetime.now().isoformat())
        try:
            start = datetime.fromisoformat(start_str)
            delta = datetime.now() - start
            
            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except Exception:
            return "Unknown"
    
    def start(self):
        """Start documentation agent."""
        logger.info("=" * 60)
        logger.info("Documentation Agent started")
        logger.info(f"Architecture: {self.architecture_file}")
        logger.info(f"Lessons: {self.lessons_file}")
        logger.info("=" * 60)
        
        # Generate initial documentation
        self._update_architecture()
        self._update_lessons_learned()
    
    def run(self):
        """Main documentation agent loop."""
        self.start()
        
        while True:
            try:
                # Periodic updates
                time.sleep(3600)  # Update every hour
                
                # Check for new agents/MCPs
                self._discover_components()
                
            except KeyboardInterrupt:
                logger.info("\nShutting down...")
                break
            except Exception as e:
                logger.error(f"Error in documentation agent: {e}")
                time.sleep(300)


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    agent = DocumentationAgent(base_dir=BASE_DIR)
    agent.run()
