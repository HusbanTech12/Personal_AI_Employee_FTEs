#!/usr/bin/env python3
"""
Audit Agent - Gold+ Tier AI Employee

Comprehensive audit logging for all system activities.

Logs:
- Task lifecycle (created, started, completed, failed)
- Agent decisions (skill selection, routing, classification)
- MCP calls (requests, responses, errors, latency)
- Failures (with full context)
- Retries (attempts, backoff, outcomes)

Storage:
/Audit/
├── tasks/YYYY-MM/task_lifecycle.log
├── agents/YYYY-MM/agent_decisions.log
├── mcp/YYYY-MM/mcp_calls.log
├── failures/YYYY-MM/failures.log
├── retries/YYYY-MM/retries.log
└── summary/daily_audit_summary.md

Usage:
    python audit_agent.py

Runs continuously, collecting audit events from all agents.
"""

import os
import sys
import json
import logging
import time
import re
import threading
import queue
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AuditAgent")


class AuditCategory(Enum):
    """Audit log categories."""
    TASK_LIFECYCLE = "task_lifecycle"
    AGENT_DECISION = "agent_decision"
    MCP_CALL = "mcp_call"
    FAILURE = "failure"
    RETRY = "retry"
    SYSTEM = "system"


class TaskEvent(Enum):
    """Task lifecycle events."""
    CREATED = "task_created"
    DETECTED = "task_detected"
    CLASSIFIED = "task_classified"
    STARTED = "task_started"
    IN_PROGRESS = "task_in_progress"
    WAITING_APPROVAL = "task_waiting_approval"
    APPROVED = "task_approved"
    REJECTED = "task_rejected"
    COMPLETED = "task_completed"
    FAILED = "task_failed"
    RETRIED = "task_retried"


class DecisionType(Enum):
    """Agent decision types."""
    SKILL_SELECTION = "skill_selection"
    DOMAIN_ROUTING = "domain_routing"
    APPROVAL_REQUIRED = "approval_required"
    FALLBACK_USED = "fallback_used"
    RECOVERY_ACTION = "recovery_action"


@dataclass
class AuditEvent:
    """Base audit event."""
    timestamp: str
    category: str
    event: str
    agent_id: str
    details: Dict = field(default_factory=dict)
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    
    def to_json(self) -> str:
        """Convert to JSON line."""
        return json.dumps(asdict(self))


@dataclass
class TaskLifecycleEvent(AuditEvent):
    """Task lifecycle audit event."""
    task_id: str = ""
    task_file: str = ""
    previous_status: Optional[str] = None
    new_status: Optional[str] = None


@dataclass
class AgentDecisionEvent(AuditEvent):
    """Agent decision audit event."""
    decision_type: str = ""
    options_considered: List[str] = field(default_factory=list)
    rationale: str = ""
    confidence: float = 0.0


@dataclass
class MCPCallEvent(AuditEvent):
    """MCP call audit event."""
    mcp_name: str = ""
    action: str = ""
    request: Dict = field(default_factory=dict)
    response: Optional[Dict] = None
    error: Optional[str] = None
    latency_ms: float = 0.0
    success: bool = True


@dataclass
class FailureEvent(AuditEvent):
    """Failure audit event."""
    error_type: str = ""
    error_message: str = ""
    stack_trace: Optional[str] = None
    context: Dict = field(default_factory=dict)
    severity: str = "error"  # warning, error, critical
    resolved: bool = False
    resolution: Optional[str] = None


@dataclass
class RetryEvent(AuditEvent):
    """Retry audit event."""
    operation: str = ""
    attempt: int = 0
    max_attempts: int = 0
    backoff_seconds: float = 0.0
    reason: str = ""
    outcome: str = ""  # success, failed, pending


class AuditAgent:
    """
    Audit Agent - Comprehensive system auditing.
    
    Collects and stores audit events from all system components.
    """
    
    # Retention periods (days)
    RETENTION = {
        AuditCategory.TASK_LIFECYCLE: 90,
        AuditCategory.AGENT_DECISION: 90,
        AuditCategory.MCP_CALL: 30,
        AuditCategory.FAILURE: 180,
        AuditCategory.RETRY: 90,
        AuditCategory.SYSTEM: 365
    }
    
    def __init__(self, base_dir: Path, audit_dir: Optional[Path] = None):
        self.base_dir = base_dir
        self.audit_dir = audit_dir or (base_dir / "Audit")
        
        # Create audit subdirectories
        self.subdirs = {
            AuditCategory.TASK_LIFECYCLE: self.audit_dir / "tasks",
            AuditCategory.AGENT_DECISION: self.audit_dir / "agents",
            AuditCategory.MCP_CALL: self.audit_dir / "mcp",
            AuditCategory.FAILURE: self.audit_dir / "failures",
            AuditCategory.RETRY: self.audit_dir / "retries",
            AuditCategory.SYSTEM: self.audit_dir / "system"
        }
        
        for subdir in self.subdirs.values():
            subdir.mkdir(parents=True, exist_ok=True)
        
        self.summary_dir = self.audit_dir / "summary"
        self.summary_dir.mkdir(parents=True, exist_ok=True)
        
        # Event queue for async processing
        self.event_queue: queue.Queue = queue.Queue()
        
        # In-memory buffers for batching
        self.buffers: Dict[AuditCategory, List[AuditEvent]] = {
            cat: [] for cat in AuditCategory
        }
        
        # Session tracking
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Statistics
        self.stats = {
            'events_received': 0,
            'events_written': 0,
            'failures_logged': 0,
            'mcp_calls_logged': 0,
            'retries_logged': 0,
            'start_time': datetime.now().isoformat()
        }
        
        self.running = False
        self.writer_thread: Optional[threading.Thread] = None
        
        # Daily summary tracking
        self.daily_stats: Dict[str, Dict] = {}
        
        # Load existing state
        self._load_state()
    
    def _load_state(self):
        """Load audit agent state."""
        state_file = self.audit_dir / "audit_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                self.stats.update(state.get('stats', {}))
                logger.info(f"Loaded audit state: {self.stats['events_written']} events written")
            except Exception as e:
                logger.error(f"Failed to load audit state: {e}")
    
    def _save_state(self):
        """Save audit agent state."""
        state_file = self.audit_dir / "audit_state.json"
        
        try:
            with open(state_file, 'w') as f:
                json.dump({
                    'stats': self.stats,
                    'session_id': self.session_id,
                    'last_updated': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save audit state: {e}")
    
    def _get_log_file(self, category: AuditCategory) -> Path:
        """Get current log file for category."""
        month_dir = self.subdirs[category] / datetime.now().strftime('%Y-%m')
        month_dir.mkdir(parents=True, exist_ok=True)
        
        return month_dir / f"{category.value}.log"
    
    def log_task_lifecycle(self, event: TaskEvent, task_id: str, 
                           task_file: str = "", details: Optional[Dict] = None,
                           previous_status: str = None, new_status: str = None,
                           agent_id: str = "system"):
        """Log task lifecycle event."""
        audit_event = TaskLifecycleEvent(
            timestamp=datetime.now().isoformat(),
            category=AuditCategory.TASK_LIFECYCLE.value,
            event=event.value,
            agent_id=agent_id,
            task_id=task_id,
            task_file=task_file,
            previous_status=previous_status,
            new_status=new_status,
            details=details or {},
            session_id=self.session_id
        )
        
        self._queue_event(audit_event)
        self._update_daily_stats('task_lifecycle', event.value)
        
        logger.debug(f"Task lifecycle: {event.value} - {task_id}")
    
    def log_agent_decision(self, decision_type: DecisionType, agent_id: str,
                           options: List[str], selected: str,
                           rationale: str = "", confidence: float = 0.0,
                           details: Optional[Dict] = None):
        """Log agent decision event."""
        audit_event = AgentDecisionEvent(
            timestamp=datetime.now().isoformat(),
            category=AuditCategory.AGENT_DECISION.value,
            event=decision_type.value,
            agent_id=agent_id,
            decision_type=decision_type.value,
            options_considered=options,
            rationale=rationale,
            confidence=confidence,
            details={**details, 'selected': selected} if details else {'selected': selected},
            session_id=self.session_id
        )
        
        self._queue_event(audit_event)
        self._update_daily_stats('agent_decision', decision_type.value)
        
        logger.debug(f"Agent decision: {decision_type.value} by {agent_id}")
    
    def log_mcp_call(self, mcp_name: str, action: str, request: Dict,
                     response: Optional[Dict] = None, error: Optional[str] = None,
                     latency_ms: float = 0.0, agent_id: str = "system"):
        """Log MCP call event."""
        success = error is None
        
        audit_event = MCPCallEvent(
            timestamp=datetime.now().isoformat(),
            category=AuditCategory.MCP_CALL.value,
            event="mcp_call" if success else "mcp_error",
            agent_id=agent_id,
            mcp_name=mcp_name,
            action=action,
            request=request,
            response=response,
            error=error,
            latency_ms=latency_ms,
            success=success,
            session_id=self.session_id
        )
        
        self._queue_event(audit_event)
        self._update_daily_stats('mcp_call', 'success' if success else 'error')
        self.stats['mcp_calls_logged'] = self.stats.get('mcp_calls_logged', 0) + 1
        
        if not success:
            logger.warning(f"MCP call failed: {mcp_name}/{action} - {error}")
    
    def log_failure(self, error_type: str, error_message: str, agent_id: str,
                    context: Optional[Dict] = None, severity: str = "error",
                    stack_trace: Optional[str] = None):
        """Log failure event."""
        audit_event = FailureEvent(
            timestamp=datetime.now().isoformat(),
            category=AuditCategory.FAILURE.value,
            event="failure",
            agent_id=agent_id,
            error_type=error_type,
            error_message=error_message[:500],  # Truncate long messages
            stack_trace=stack_trace,
            context=context or {},
            severity=severity,
            session_id=self.session_id
        )
        
        self._queue_event(audit_event)
        self._update_daily_stats('failure', severity)
        self.stats['failures_logged'] = self.stats.get('failures_logged', 0) + 1
        
        logger.error(f"Failure logged: {error_type} - {agent_id}")
    
    def log_retry(self, operation: str, attempt: int, max_attempts: int,
                  backoff_seconds: float, reason: str, outcome: str,
                  agent_id: str = "system"):
        """Log retry event."""
        audit_event = RetryEvent(
            timestamp=datetime.now().isoformat(),
            category=AuditCategory.RETRY.value,
            event="retry",
            agent_id=agent_id,
            operation=operation,
            attempt=attempt,
            max_attempts=max_attempts,
            backoff_seconds=backoff_seconds,
            reason=reason,
            outcome=outcome,
            session_id=self.session_id
        )
        
        self._queue_event(audit_event)
        self._update_daily_stats('retry', outcome)
        self.stats['retries_logged'] = self.stats.get('retries_logged', 0) + 1
        
        logger.debug(f"Retry logged: {operation} attempt {attempt}/{max_attempts} - {outcome}")
    
    def _queue_event(self, event: AuditEvent):
        """Queue event for async processing."""
        self.event_queue.put(event)
        self.stats['events_received'] = self.stats.get('events_received', 0) + 1
    
    def _process_events(self):
        """Process queued events (writer thread)."""
        while self.running:
            try:
                # Collect events from queue
                events = []
                while not self.event_queue.empty() and len(events) < 100:
                    try:
                        event = self.event_queue.get_nowait()
                        events.append(event)
                    except queue.Empty:
                        break
                
                # Group by category
                by_category: Dict[AuditCategory, List[AuditEvent]] = {
                    cat: [] for cat in AuditCategory
                }
                
                for event in events:
                    try:
                        cat = AuditCategory(event.category)
                        by_category[cat].append(event)
                    except ValueError:
                        logger.warning(f"Unknown category: {event.category}")
                
                # Write to log files
                for category, cat_events in by_category.items():
                    if cat_events:
                        self._write_events(category, cat_events)
                
                # Generate daily summary if needed
                self._maybe_generate_daily_summary()
                
                # Save state periodically
                if self.stats['events_received'] % 100 == 0:
                    self._save_state()
                
                time.sleep(0.1)  # Small delay to prevent busy waiting
                
            except Exception as e:
                logger.error(f"Error processing events: {e}")
                time.sleep(1)
    
    def _write_events(self, category: AuditCategory, events: List[AuditEvent]):
        """Write events to log file."""
        log_file = self._get_log_file(category)
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                for event in events:
                    f.write(event.to_json() + '\n')
            
            self.stats['events_written'] = self.stats.get('events_written', 0) + len(events)
            
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def _update_daily_stats(self, category: str, event_type: str):
        """Update daily statistics."""
        today = datetime.now().strftime('%Y-%m-%d')
        
        if today not in self.daily_stats:
            self.daily_stats[today] = {
                'task_lifecycle': {},
                'agent_decision': {},
                'mcp_call': {'success': 0, 'error': 0},
                'failure': {'warning': 0, 'error': 0, 'critical': 0},
                'retry': {'success': 0, 'failed': 0, 'pending': 0}
            }
        
        if category in self.daily_stats[today]:
            if event_type not in self.daily_stats[today][category]:
                self.daily_stats[today][category][event_type] = 0
            self.daily_stats[today][category][event_type] += 1
    
    def _maybe_generate_daily_summary(self):
        """Generate daily summary if day changed."""
        today = datetime.now().strftime('%Y-%m-%d')
        summary_file = self.summary_dir / f"daily_audit_summary_{today}.md"
        
        if not summary_file.exists() and datetime.now().hour >= 23:
            # Generate summary near end of day
            self._generate_daily_summary(today)
    
    def _generate_daily_summary(self, date_str: str):
        """Generate daily audit summary."""
        summary_file = self.summary_dir / f"daily_audit_summary_{date_str}.md"
        
        stats = self.daily_stats.get(date_str, {})
        
        summary = f"""# Daily Audit Summary

**Date:** {date_str}
**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Session:** {self.session_id}

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Task Events | {sum(stats.get('task_lifecycle', {}).values())} |
| Agent Decisions | {sum(stats.get('agent_decision', {}).values())} |
| MCP Calls | {sum(stats.get('mcp_call', {}).values())} |
| Failures | {sum(stats.get('failure', {}).values())} |
| Retries | {sum(stats.get('retry', {}).values())} |

---

## Task Lifecycle

"""
        
        for event, count in stats.get('task_lifecycle', {}).items():
            summary += f"- **{event}:** {count}\n"
        
        summary += """
---

## Agent Decisions

"""
        
        for decision, count in stats.get('agent_decision', {}).items():
            summary += f"- **{decision}:** {count}\n"
        
        summary += """
---

## MCP Calls

"""
        
        mcp_stats = stats.get('mcp_call', {})
        summary += f"- **Successful:** {mcp_stats.get('success', 0)}\n"
        summary += f"- **Errors:** {mcp_stats.get('error', 0)}\n"
        
        summary += """
---

## Failures

"""
        
        failure_stats = stats.get('failure', {})
        summary += f"- **Warnings:** {failure_stats.get('warning', 0)}\n"
        summary += f"- **Errors:** {failure_stats.get('error', 0)}\n"
        summary += f"- **Critical:** {failure_stats.get('critical', 0)}\n"
        
        summary += """
---

## Retries

"""
        
        retry_stats = stats.get('retry', {})
        summary += f"- **Successful:** {retry_stats.get('success', 0)}\n"
        summary += f"- **Failed:** {retry_stats.get('failed', 0)}\n"
        summary += f"- **Pending:** {retry_stats.get('pending', 0)}\n"
        
        summary += f"""
---

## System Metrics

| Metric | Value |
|--------|-------|
| Events Received | {self.stats.get('events_received', 0)} |
| Events Written | {self.stats.get('events_written', 0)} |
| Failures Logged | {self.stats.get('failures_logged', 0)} |
| MCP Calls Logged | {self.stats.get('mcp_calls_logged', 0)} |
| Retries Logged | {self.stats.get('retries_logged', 0)} |

---

*Generated automatically by AI Employee Audit Agent*
"""
        
        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            logger.info(f"Daily audit summary generated: {summary_file.name}")
        except Exception as e:
            logger.error(f"Failed to generate daily summary: {e}")
    
    def query_events(self, category: AuditCategory, start_date: datetime,
                     end_date: datetime, filters: Optional[Dict] = None) -> List[Dict]:
        """Query audit events from log files."""
        events = []
        
        current = start_date
        while current <= end_date:
            month_dir = self.subdirs[category] / current.strftime('%Y-%m')
            log_file = month_dir / f"{category.value}.log"
            
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            try:
                                event = json.loads(line.strip())
                                
                                # Apply filters
                                if filters:
                                    match = all(
                                        event.get(k) == v 
                                        for k, v in filters.items()
                                    )
                                    if not match:
                                        continue
                                
                                events.append(event)
                            except json.JSONDecodeError:
                                continue
                except Exception as e:
                    logger.error(f"Failed to read log file: {e}")
            
            current += timedelta(days=1)
        
        return events
    
    def get_audit_report(self, days: int = 7) -> Dict:
        """Generate audit report for specified period."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        report = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'summary': {},
            'by_category': {}
        }
        
        for category in AuditCategory:
            events = self.query_events(category, start_date, end_date)
            report['by_category'][category.value] = {
                'count': len(events),
                'recent': events[-10:] if events else []  # Last 10 events
            }
        
        report['summary'] = {
            'total_events': sum(c['count'] for c in report['by_category'].values()),
            'failures': report['by_category'].get('failure', {}).get('count', 0),
            'retries': report['by_category'].get('retry', {}).get('count', 0),
            'mcp_errors': sum(
                1 for e in self.query_events(AuditCategory.MCP_CALL, start_date, end_date)
                if not e.get('success', True)
            )
        }
        
        return report
    
    def start(self):
        """Start audit agent."""
        self.running = True
        self.stats['start_time'] = datetime.now().isoformat()
        
        # Start writer thread
        self.writer_thread = threading.Thread(target=self._process_events)
        self.writer_thread.daemon = True
        self.writer_thread.start()
        
        logger.info("=" * 60)
        logger.info("Audit Agent started")
        logger.info(f"Audit directory: {self.audit_dir}")
        logger.info(f"Session ID: {self.session_id}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Logging categories:")
        for cat in AuditCategory:
            logger.info(f"  - {cat.value}")
        logger.info("")
    
    def stop(self):
        """Stop audit agent."""
        self.running = False
        self._save_state()
        logger.info("Audit Agent stopped")
    
    def run(self):
        """Main entry point."""
        self.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            self.stop()


# Global audit instance for easy import
_audit_instance: Optional[AuditAgent] = None


def get_audit_agent() -> AuditAgent:
    """Get or create global audit agent instance."""
    global _audit_instance
    if _audit_instance is None:
        _audit_instance = AuditAgent(Path(__file__).parent.parent)
    return _audit_instance


# Convenience functions for direct logging
def log_task_event(event: TaskEvent, task_id: str, **kwargs):
    """Log task lifecycle event."""
    get_audit_agent().log_task_lifecycle(event, task_id, **kwargs)


def log_decision(decision_type: DecisionType, agent_id: str, **kwargs):
    """Log agent decision."""
    get_audit_agent().log_agent_decision(decision_type, agent_id, **kwargs)


def log_mcp(mcp_name: str, action: str, request: Dict, **kwargs):
    """Log MCP call."""
    get_audit_agent().log_mcp_call(mcp_name, action, request, **kwargs)


def log_failure(error_type: str, error_message: str, agent_id: str, **kwargs):
    """Log failure."""
    get_audit_agent().log_failure(error_type, error_message, agent_id, **kwargs)


def log_retry(operation: str, attempt: int, max_attempts: int, **kwargs):
    """Log retry."""
    get_audit_agent().log_retry(operation, attempt, max_attempts, **kwargs)


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    agent = AuditAgent(base_dir=BASE_DIR)
    agent.run()
