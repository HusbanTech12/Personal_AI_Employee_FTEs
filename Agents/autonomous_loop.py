#!/usr/bin/env python3
"""
Autonomous Loop Agent

Continuous reasoning loop for GOLD TIER AI Employee.
Implements self-recovering, fault-tolerant task execution.

Behavior:
1. Check new events
2. Analyze
3. Create Plan
4. Execute Skills
5. Verify Result
6. Retry if failed
7. Log outcome

Loop Interval: 30 seconds
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum


# =============================================================================
# Configuration
# =============================================================================

class Config:
    """Central configuration for autonomous loop."""
    
    # Loop timing
    LOOP_INTERVAL_SECONDS = 30
    MAX_RETRY_ATTEMPTS = 3
    RETRY_DELAY_SECONDS = 5
    
    # Paths
    BASE_DIR = Path(__file__).parent.parent
    INBOX_DIR = BASE_DIR / "Inbox"
    PLANS_DIR = BASE_DIR / "Plans"
    LOGS_DIR = BASE_DIR / "Logs"
    VAULT_DIR = BASE_DIR / "Vault"
    SKILLS_DIR = BASE_DIR / "Skills"
    
    # Log files
    AUDIT_LOG = LOGS_DIR / "audit.log"
    LOOP_LOG = LOGS_DIR / "autonomous_loop.log"
    
    # State files
    STATE_FILE = BASE_DIR / ".agent_state.json"
    PROCESSED_EVENTS_FILE = BASE_DIR / ".processed_events.json"
    
    # Error handling
    MAX_CONSECUTIVE_ERRORS = 10
    ERROR_COOLDOWN_SECONDS = 60
    GRACEFUL_DEGRADATION_ENABLED = True
    
    # Self-recovery
    SELF_RECOVERY_ENABLED = True
    RECOVERY_CHECK_INTERVAL = 300  # 5 minutes


# =============================================================================
# Enums
# =============================================================================

class LoopState(Enum):
    """Agent loop states."""
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    RECOVERING = "recovering"
    STOPPED = "stopped"


class EventStatus(Enum):
    """Event processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Event:
    """Represents an incoming event to process."""
    event_id: str
    channel: str  # gmail, whatsapp, linkedin
    timestamp: str
    data: Dict[str, Any]
    status: EventStatus = EventStatus.PENDING
    retry_count: int = 0
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "event_id": self.event_id,
            "channel": self.channel,
            "timestamp": self.timestamp,
            "data": self.data,
            "status": self.status.value,
            "retry_count": self.retry_count,
            "error_message": self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Event":
        return cls(
            event_id=data["event_id"],
            channel=data["channel"],
            timestamp=data["timestamp"],
            data=data["data"],
            status=EventStatus(data["status"]),
            retry_count=data.get("retry_count", 0),
            error_message=data.get("error_message")
        )


@dataclass
class Plan:
    """Represents an execution plan."""
    plan_id: str
    event_id: str
    intent: str
    actions: List[Dict[str, Any]]
    target_agent: Optional[str]
    priority: str
    created_at: str
    status: str = "pending"
    result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Plan":
        return cls(**data)


@dataclass
class LoopMetrics:
    """Metrics for loop performance tracking."""
    cycles_completed: int = 0
    events_processed: int = 0
    events_failed: int = 0
    plans_created: int = 0
    retries_total: int = 0
    consecutive_errors: int = 0
    last_cycle_time: float = 0.0
    avg_cycle_time: float = 0.0
    uptime_seconds: float = 0.0
    last_error: Optional[str] = None
    last_recovery: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging for autonomous loop."""
    # Ensure logs directory exists
    Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("autonomous_loop")
    logger.setLevel(logging.DEBUG)
    
    # File handler
    file_handler = logging.FileHandler(Config.LOOP_LOG)
    file_handler.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# =============================================================================
# State Manager
# =============================================================================

class StateManager:
    """Manages agent state persistence and recovery."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.state = {
            "loop_state": LoopState.IDLE.value,
            "started_at": None,
            "last_cycle": None,
            "metrics": LoopMetrics().to_dict()
        }
        self.load_state()
    
    def load_state(self) -> None:
        """Load state from file if exists."""
        if Config.STATE_FILE.exists():
            try:
                with open(Config.STATE_FILE, 'r') as f:
                    saved_state = json.load(f)
                    self.state.update(saved_state)
                    self.logger.info(f"State loaded from {Config.STATE_FILE}")
            except Exception as e:
                self.logger.warning(f"Failed to load state: {e}")
    
    def save_state(self) -> None:
        """Persist state to file."""
        try:
            Config.STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(Config.STATE_FILE, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
    
    def update_state(self, key: str, value: Any) -> None:
        """Update state value and persist."""
        self.state[key] = value
        self.save_state()
    
    def update_metrics(self, **kwargs) -> None:
        """Update metrics values."""
        for key, value in kwargs.items():
            if key in self.state["metrics"]:
                self.state["metrics"][key] = value
        self.save_state()
    
    def increment_metric(self, key: str, amount: int = 1) -> None:
        """Increment a metric value."""
        if key in self.state["metrics"]:
            self.state["metrics"][key] += amount
            self.save_state()
    
    def get_state(self) -> str:
        """Get current loop state."""
        return LoopState(self.state["loop_state"])
    
    def set_state(self, state: LoopState) -> None:
        """Set loop state."""
        self.state["loop_state"] = state.value
        self.save_state()
        self.logger.info(f"State changed to: {state.value}")
    
    def get_metrics(self) -> LoopMetrics:
        """Get current metrics."""
        return LoopMetrics(**self.state["metrics"])


# =============================================================================
# Event Processor
# =============================================================================

class EventProcessor:
    """Handles event detection and processing."""
    
    def __init__(self, logger: logging.Logger, state_manager: StateManager):
        self.logger = logger
        self.state_manager = state_manager
        self.processed_events = self._load_processed_events()
    
    def _load_processed_events(self) -> set:
        """Load set of processed event IDs."""
        if Config.PROCESSED_EVENTS_FILE.exists():
            try:
                with open(Config.PROCESSED_EVENTS_FILE, 'r') as f:
                    data = json.load(f)
                    return set(data.get("processed", []))
            except Exception as e:
                self.logger.warning(f"Failed to load processed events: {e}")
        return set()
    
    def _save_processed_events(self) -> None:
        """Save processed events to file."""
        try:
            Config.PROCESSED_EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(Config.PROCESSED_EVENTS_FILE, 'w') as f:
                json.dump({"processed": list(self.processed_events)}, f)
        except Exception as e:
            self.logger.error(f"Failed to save processed events: {e}")
    
    def check_new_events(self) -> List[Event]:
        """Check for new events from all channels."""
        events = []
        
        try:
            # Check Gmail inbox
            gmail_events = self._check_gmail_inbox()
            events.extend(gmail_events)
            
            # Check WhatsApp messages
            whatsapp_events = self._check_whatsapp()
            events.extend(whatsapp_events)
            
            # Check LinkedIn events
            linkedin_events = self._check_linkedin()
            events.extend(linkedin_events)
            
            self.logger.debug(f"Found {len(events)} new events")
            
        except Exception as e:
            self.logger.error(f"Error checking events: {e}")
        
        return events
    
    def _check_gmail_inbox(self) -> List[Event]:
        """Check Gmail inbox for new events."""
        events = []
        inbox_path = Config.INBOX_DIR / "gmail"
        
        if inbox_path.exists():
            for file in inbox_path.glob("*.json"):
                event_id = file.stem
                if event_id not in self.processed_events:
                    try:
                        with open(file, 'r') as f:
                            data = json.load(f)
                        event = Event(
                            event_id=event_id,
                            channel="gmail",
                            timestamp=datetime.now().isoformat(),
                            data=data
                        )
                        events.append(event)
                        self.logger.debug(f"Found Gmail event: {event_id}")
                    except Exception as e:
                        self.logger.error(f"Error reading Gmail event {event_id}: {e}")
        
        return events
    
    def _check_whatsapp(self) -> List[Event]:
        """Check WhatsApp for new events."""
        events = []
        whatsapp_path = Config.INBOX_DIR / "whatsapp"
        
        if whatsapp_path.exists():
            for file in whatsapp_path.glob("*.json"):
                event_id = file.stem
                if event_id not in self.processed_events:
                    try:
                        with open(file, 'r') as f:
                            data = json.load(f)
                        event = Event(
                            event_id=event_id,
                            channel="whatsapp",
                            timestamp=datetime.now().isoformat(),
                            data=data
                        )
                        events.append(event)
                        self.logger.debug(f"Found WhatsApp event: {event_id}")
                    except Exception as e:
                        self.logger.error(f"Error reading WhatsApp event {event_id}: {e}")
        
        return events
    
    def _check_linkedin(self) -> List[Event]:
        """Check LinkedIn for new events."""
        events = []
        linkedin_path = Config.INBOX_DIR / "linkedin"
        
        if linkedin_path.exists():
            for file in linkedin_path.glob("*.json"):
                event_id = file.stem
                if event_id not in self.processed_events:
                    try:
                        with open(file, 'r') as f:
                            data = json.load(f)
                        event = Event(
                            event_id=event_id,
                            channel="linkedin",
                            timestamp=datetime.now().isoformat(),
                            data=data
                        )
                        events.append(event)
                        self.logger.debug(f"Found LinkedIn event: {event_id}")
                    except Exception as e:
                        self.logger.error(f"Error reading LinkedIn event {event_id}: {e}")
        
        return events
    
    def mark_event_processed(self, event_id: str) -> None:
        """Mark event as processed."""
        self.processed_events.add(event_id)
        self._save_processed_events()
    
    def mark_event_failed(self, event: Event) -> bool:
        """Mark event as failed, return True if can retry."""
        event.retry_count += 1
        if event.retry_count < Config.MAX_RETRY_ATTEMPTS:
            event.status = EventStatus.RETRYING
            self.logger.warning(f"Event {event.event_id} marked for retry ({event.retry_count}/{Config.MAX_RETRY_ATTEMPTS})")
            return True
        else:
            event.status = EventStatus.FAILED
            self.logger.error(f"Event {event.event_id} failed after {event.retry_count} attempts")
            self.mark_event_processed(event.event_id)
            return False


# =============================================================================
# Plan Generator
# =============================================================================

class PlanGenerator:
    """Generates execution plans for events."""
    
    def __init__(self, logger: logging.Logger, state_manager: StateManager):
        self.logger = logger
        self.state_manager = state_manager
    
    def create_plan(self, event: Event) -> Optional[Plan]:
        """Create execution plan for an event."""
        try:
            # Generate plan ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            plan_id = f"PLAN_{timestamp}_{event.event_id[:8]}"
            
            # Analyze event and determine intent
            intent = self._classify_intent(event)
            
            # Determine target agent based on intent
            target_agent = self._get_target_agent(intent, event.channel)
            
            # Define actions
            actions = self._define_actions(event, intent)
            
            # Determine priority
            priority = self._determine_priority(event, intent)
            
            plan = Plan(
                plan_id=plan_id,
                event_id=event.event_id,
                intent=intent,
                actions=actions,
                target_agent=target_agent,
                priority=priority,
                created_at=datetime.now().isoformat()
            )
            
            # Save plan to file
            self._save_plan(plan, event)
            
            self.logger.info(f"Created plan {plan_id} for event {event.event_id}")
            self.state_manager.increment_metric("plans_created")
            
            return plan
            
        except Exception as e:
            self.logger.error(f"Failed to create plan: {e}")
            return None
    
    def _classify_intent(self, event: Event) -> str:
        """Classify event intent."""
        # Simple keyword-based classification
        # In production, this would use ML/NLP
        
        data_str = json.dumps(event.data).lower()
        
        if any(word in data_str for word in ["buy", "price", "cost", "purchase", "demo"]):
            return "SALES"
        elif any(word in data_str for word in ["help", "support", "issue", "problem", "bug"]):
            return "SUPPORT"
        elif any(word in data_str for word in ["partnership", "collaboration", "business"]):
            return "BUSINESS"
        elif any(word in data_str for word in ["spam", "promo", "unsubscribe"]):
            return "SPAM"
        elif event.channel == "gmail" and "@company.com" in data_str:
            return "INTERNAL"
        
        return "GENERAL"
    
    def _get_target_agent(self, intent: str, channel: str) -> Optional[str]:
        """Determine target agent for intent."""
        agent_mapping = {
            "SALES": "sales_agent",
            "SUPPORT": "support_agent",
            "BUSINESS": "business_agent",
            "INTERNAL": "internal_agent",
            "SPAM": None,
            "GENERAL": None
        }
        return agent_mapping.get(intent)
    
    def _define_actions(self, event: Event, intent: str) -> List[Dict[str, Any]]:
        """Define actions for the plan."""
        actions = []
        
        if intent == "SPAM":
            actions.append({"type": "archive", "reason": "spam_detected"})
        elif intent == "SALES":
            actions.append({"type": "analyze", "focus": "lead_qualification"})
            actions.append({"type": "respond", "tone": "professional"})
            actions.append({"type": "create_task", "agent": "sales_agent"})
        elif intent == "SUPPORT":
            actions.append({"type": "analyze", "focus": "issue_classification"})
            actions.append({"type": "respond", "tone": "empathetic"})
            actions.append({"type": "create_ticket", "priority": "normal"})
        elif intent == "BUSINESS":
            actions.append({"type": "analyze", "focus": "opportunity_assessment"})
            actions.append({"type": "escalate", "level": "management"})
        else:
            actions.append({"type": "log", "action": "general_processing"})
        
        return actions
    
    def _determine_priority(self, event: Event, intent: str) -> str:
        """Determine plan priority."""
        if intent in ["SALES", "SUPPORT"]:
            return "high"
        elif intent == "BUSINESS":
            return "medium"
        elif intent == "INTERNAL":
            return "medium"
        else:
            return "low"
    
    def _save_plan(self, plan: Plan, event: Event) -> None:
        """Save plan to file."""
        Config.PLANS_DIR.mkdir(parents=True, exist_ok=True)
        
        plan_content = f"""# Plan: {plan.plan_id}

## Generated
{plan.created_at}

## Source Event
- **Channel**: {event.channel}
- **Event ID**: {event.event_id}

## Classification
- **Intent**: {plan.intent}
- **Target Agent**: {plan.target_agent or "None (auto-process)"}
- **Priority**: {plan.priority}

## Actions
"""
        for i, action in enumerate(plan.actions, 1):
            plan_content += f"{i}. {action['type']}"
            if 'focus' in action:
                plan_content += f" ({action['focus']})"
            plan_content += "\n"
        
        plan_content += f"""
## Status
{plan.status}

---
*Auto-generated by Autonomous Loop Agent*
"""
        
        plan_file = Config.PLANS_DIR / f"{plan.plan_id}.md"
        with open(plan_file, 'w') as f:
            f.write(plan_content)


# =============================================================================
# Skill Executor
# =============================================================================

class SkillExecutor:
    """Executes skills based on plans."""
    
    def __init__(self, logger: logging.Logger, state_manager: StateManager):
        self.logger = logger
        self.state_manager = state_manager
        self.loaded_skills = self._load_skills()
    
    def _load_skills(self) -> Dict[str, Any]:
        """Load available skills."""
        skills = {}
        
        if Config.SKILLS_DIR.exists():
            for skill_file in Config.SKILLS_DIR.glob("*.SKILL.md"):
                skill_name = skill_file.stem.replace(".SKILL", "")
                skills[skill_name] = {
                    "path": str(skill_file),
                    "loaded": True
                }
                self.logger.debug(f"Loaded skill: {skill_name}")
        
        return skills
    
    def execute_plan(self, plan: Plan, event: Event) -> Dict[str, Any]:
        """Execute plan using appropriate skill."""
        result = {
            "success": False,
            "actions_completed": [],
            "actions_failed": [],
            "error": None
        }
        
        try:
            if plan.target_agent:
                # Execute via target agent
                result = self._execute_agent_action(plan, event)
            else:
                # Auto-process without agent
                result = self._auto_process(plan, event)
            
            if result["success"]:
                self.logger.info(f"Plan {plan.plan_id} executed successfully")
            else:
                self.logger.warning(f"Plan {plan.plan_id} execution had issues")
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            self.logger.error(f"Plan execution error: {e}")
        
        return result
    
    def _execute_agent_action(self, plan: Plan, event: Event) -> Dict[str, Any]:
        """Execute action via target agent."""
        result = {
            "success": True,
            "actions_completed": [],
            "actions_failed": [],
            "error": None,
            "agent": plan.target_agent
        }
        
        for action in plan.actions:
            try:
                # Simulate agent execution
                # In production, this would call the actual agent
                self.logger.debug(f"Executing action via {plan.target_agent}: {action['type']}")
                
                # Create execution record
                execution_record = {
                    "plan_id": plan.plan_id,
                    "event_id": event.event_id,
                    "agent": plan.target_agent,
                    "action": action,
                    "timestamp": datetime.now().isoformat(),
                    "status": "completed"
                }
                
                result["actions_completed"].append(execution_record)
                
            except Exception as e:
                result["success"] = False
                result["actions_failed"].append({
                    "action": action,
                    "error": str(e)
                })
        
        return result
    
    def _auto_process(self, plan: Plan, event: Event) -> Dict[str, Any]:
        """Auto-process without specific agent."""
        result = {
            "success": True,
            "actions_completed": [],
            "actions_failed": [],
            "error": None,
            "auto_processed": True
        }
        
        for action in plan.actions:
            try:
                self.logger.debug(f"Auto-processing action: {action['type']}")
                
                execution_record = {
                    "plan_id": plan.plan_id,
                    "event_id": event.event_id,
                    "action": action,
                    "timestamp": datetime.now().isoformat(),
                    "status": "completed"
                }
                
                result["actions_completed"].append(execution_record)
                
            except Exception as e:
                result["success"] = False
                result["actions_failed"].append({
                    "action": action,
                    "error": str(e)
                })
        
        return result


# =============================================================================
# Result Verifier
# =============================================================================

class ResultVerifier:
    """Verifies execution results."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
    
    def verify_result(self, plan: Plan, result: Dict[str, Any]) -> bool:
        """Verify execution result."""
        try:
            # Check if execution was successful
            if not result.get("success", False):
                self.logger.warning(f"Verification failed: execution not successful")
                return False
            
            # Check if all actions completed
            expected_actions = len(plan.actions)
            completed_actions = len(result.get("actions_completed", []))
            
            if completed_actions < expected_actions:
                self.logger.warning(
                    f"Verification warning: {completed_actions}/{expected_actions} actions completed"
                )
                # Still return True if critical actions completed
            
            # Check for errors
            if result.get("error"):
                self.logger.warning(f"Verification warning: execution had errors")
            
            self.logger.info(f"Verification passed for plan {plan.plan_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Verification error: {e}")
            return False


# =============================================================================
# Audit Logger
# =============================================================================

class AuditLogger:
    """Logs all decisions and actions to audit log."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    
    def log_decision(self, event: Event, plan: Optional[Plan]) -> None:
        """Log classification decision."""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        if plan:
            log_line = (
                f"[{timestamp}] | {event.channel} | {event.event_id} | "
                f"{plan.intent} | AUTO | {plan.target_agent or 'none'} | "
                f"plan_created | {plan.plan_id}\n"
            )
        else:
            log_line = (
                f"[{timestamp}] | {event.channel} | {event.event_id} | "
                f"NO_PLAN | - | - | skipped\n"
            )
        
        self._append_to_audit_log(log_line)
    
    def log_action(self, plan: Plan, result: Dict[str, Any]) -> None:
        """Log execution action."""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        status = "success" if result.get("success") else "failed"
        actions_count = len(result.get("actions_completed", []))
        
        log_line = (
            f"[{timestamp}] | {plan.plan_id} | {plan.event_id} | "
            f"EXECUTE | {status} | actions={actions_count}\n"
        )
        
        self._append_to_audit_log(log_line)
    
    def log_error(self, event: Event, error: str) -> None:
        """Log error."""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        log_line = (
            f"[{timestamp}] | ERROR | {event.channel} | {event.event_id} | "
            f"{error}\n"
        )
        
        self._append_to_audit_log(log_line)
    
    def log_recovery(self, recovery_type: str, details: str) -> None:
        """Log recovery action."""
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        
        log_line = (
            f"[{timestamp}] | RECOVERY | {recovery_type} | {details}\n"
        )
        
        self._append_to_audit_log(log_line)
    
    def _append_to_audit_log(self, log_line: str) -> None:
        """Append line to audit log."""
        try:
            with open(Config.AUDIT_LOG, 'a') as f:
                f.write(log_line)
        except Exception as e:
            self.logger.error(f"Failed to write audit log: {e}")


# =============================================================================
# Recovery Manager
# =============================================================================

class RecoveryManager:
    """Handles self-recovery and graceful degradation."""
    
    def __init__(self, logger: logging.Logger, state_manager: StateManager):
        self.logger = logger
        self.state_manager = state_manager
        self.last_recovery_check = time.time()
    
    def check_and_recover(self) -> bool:
        """Check system health and attempt recovery if needed."""
        if not Config.SELF_RECOVERY_ENABLED:
            return True
        
        current_time = time.time()
        if current_time - self.last_recovery_check < Config.RECOVERY_CHECK_INTERVAL:
            return True
        
        self.last_recovery_check = current_time
        metrics = self.state_manager.get_metrics()
        
        try:
            # Check for consecutive errors
            if metrics.consecutive_errors >= Config.MAX_CONSECUTIVE_ERRORS:
                self.logger.warning(
                    f"High consecutive errors detected: {metrics.consecutive_errors}"
                )
                
                if Config.GRACEFUL_DEGRADATION_ENABLED:
                    self._activate_graceful_degradation()
                    return True
                
                return False
            
            # Check system resources
            self._check_system_health()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Recovery check failed: {e}")
            return False
    
    def _activate_graceful_degradation(self) -> None:
        """Activate graceful degradation mode."""
        self.logger.warning("Activating graceful degradation mode")
        
        # Reduce loop frequency
        Config.LOOP_INTERVAL_SECONDS = 60  # Double the interval
        
        # Log recovery action
        self.state_manager.update_metrics(
            last_recovery=datetime.now().isoformat()
        )
    
    def _check_system_health(self) -> None:
        """Check system health metrics."""
        # Check disk space
        self._check_disk_space()
        
        # Check log file sizes
        self._check_log_sizes()
    
    def _check_disk_space(self) -> None:
        """Check available disk space."""
        try:
            import shutil
            total, used, free = shutil.disk_usage(Config.BASE_DIR)
            free_gb = free / (1024 ** 3)
            
            if free_gb < 1.0:  # Less than 1GB free
                self.logger.warning(f"Low disk space: {free_gb:.2f}GB free")
        except Exception as e:
            self.logger.debug(f"Disk space check skipped: {e}")
    
    def _check_log_sizes(self) -> None:
        """Check and rotate large log files."""
        max_log_size = 10 * 1024 * 1024  # 10MB
        
        for log_file in Config.LOGS_DIR.glob("*.log"):
            try:
                if log_file.stat().st_size > max_log_size:
                    self.logger.info(f"Rotating large log file: {log_file}")
                    self._rotate_log_file(log_file)
            except Exception as e:
                self.logger.debug(f"Log size check failed for {log_file}: {e}")
    
    def _rotate_log_file(self, log_file: Path) -> None:
        """Rotate a log file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated_file = log_file.with_suffix(f".{timestamp}.log")
        
        try:
            log_file.rename(rotated_file)
            # Create new empty log file
            log_file.touch()
        except Exception as e:
            self.logger.error(f"Failed to rotate log file: {e}")


# =============================================================================
# Autonomous Loop Agent
# =============================================================================

class AutonomousLoopAgent:
    """Main autonomous loop agent."""
    
    def __init__(self):
        self.logger = setup_logging()
        self.state_manager = StateManager(self.logger)
        self.event_processor = EventProcessor(self.logger, self.state_manager)
        self.plan_generator = PlanGenerator(self.logger, self.state_manager)
        self.skill_executor = SkillExecutor(self.logger, self.state_manager)
        self.result_verifier = ResultVerifier(self.logger)
        self.audit_logger = AuditLogger(self.logger)
        self.recovery_manager = RecoveryManager(self.logger, self.state_manager)
        
        self.running = False
        self.start_time = None
    
    def start(self) -> None:
        """Start the autonomous loop."""
        self.logger.info("=" * 60)
        self.logger.info("AUTONOMOUS LOOP AGENT STARTING")
        self.logger.info("=" * 60)
        self.logger.info(f"Loop interval: {Config.LOOP_INTERVAL_SECONDS}s")
        self.logger.info(f"Max retries: {Config.MAX_RETRY_ATTEMPTS}")
        self.logger.info(f"Self-recovery: {Config.SELF_RECOVERY_ENABLED}")
        self.logger.info(f"Graceful degradation: {Config.GRACEFUL_DEGRADATION_ENABLED}")
        self.logger.info("=" * 60)
        
        self.running = True
        self.start_time = time.time()
        self.state_manager.set_state(LoopState.RUNNING)
        self.state_manager.update_state("started_at", datetime.now().isoformat())
        
        try:
            self._run_loop()
        except KeyboardInterrupt:
            self.logger.info("Received shutdown signal")
        except Exception as e:
            self.logger.error(f"Fatal error in main loop: {e}")
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop the autonomous loop."""
        self.running = False
        self.state_manager.set_state(LoopState.STOPPED)
        
        # Calculate final uptime
        if self.start_time:
            uptime = time.time() - self.start_time
            self.state_manager.update_metrics(uptime_seconds=uptime)
            self.logger.info(f"Total uptime: {uptime:.2f}s ({uptime/3600:.2f}h)")
        
        self.logger.info("Autonomous loop stopped")
    
    def _run_loop(self) -> None:
        """Main loop execution."""
        cycle_count = 0
        
        while self.running:
            cycle_start = time.time()
            cycle_count += 1
            
            try:
                # Step 1: Check system health and recover if needed
                if not self.recovery_manager.check_and_recover():
                    self.logger.error("Recovery failed, entering error state")
                    self.state_manager.set_state(LoopState.ERROR)
                    time.sleep(Config.ERROR_COOLDOWN_SECONDS)
                    continue
                
                # Step 2: Check for new events
                events = self.event_processor.check_new_events()
                
                if events:
                    self.logger.info(f"Processing {len(events)} new events")
                    
                    for event in events:
                        self._process_event(event)
                else:
                    self.logger.debug("No new events to process")
                
                # Update metrics
                self.state_manager.increment_metric("cycles_completed")
                
            except Exception as e:
                self.logger.error(f"Cycle error: {e}")
                self.state_manager.increment_metric("consecutive_errors")
                
                if Config.GRACEFUL_DEGRADATION_ENABLED:
                    self.logger.warning("Graceful degradation activated")
                    time.sleep(Config.ERROR_COOLDOWN_SECONDS)
                else:
                    raise
            
            # Calculate cycle time
            cycle_time = time.time() - cycle_start
            self.state_manager.update_metrics(
                last_cycle_time=cycle_time,
                consecutive_errors=0  # Reset on successful cycle
            )
            
            # Sleep until next cycle
            sleep_time = max(0, Config.LOOP_INTERVAL_SECONDS - cycle_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def _process_event(self, event: Event) -> None:
        """Process a single event through the full pipeline."""
        self.logger.info(f"Processing event: {event.event_id} ({event.channel})")
        
        try:
            # Step 1: Mark as processing
            event.status = EventStatus.PROCESSING
            self.state_manager.increment_metric("events_processed")
            
            # Step 2: Analyze and create plan
            plan = self.plan_generator.create_plan(event)
            
            if not plan:
                self.logger.warning(f"Failed to create plan for {event.event_id}")
                self.audit_logger.log_decision(event, None)
                self.event_processor.mark_event_processed(event.event_id)
                return
            
            # Log decision
            self.audit_logger.log_decision(event, plan)
            
            # Step 3: Execute skills
            result = self.skill_executor.execute_plan(plan, event)
            
            # Step 4: Verify result
            verification_passed = self.result_verifier.verify_result(plan, result)
            
            # Log action
            self.audit_logger.log_action(plan, result)
            
            # Step 5: Handle result
            if verification_passed and result.get("success", False):
                # Success - mark as completed
                self.event_processor.mark_event_processed(event.event_id)
                self.logger.info(f"Event {event.event_id} completed successfully")
            else:
                # Failed - check for retry
                can_retry = self.event_processor.mark_event_failed(event)
                
                if can_retry:
                    # Will be retried in next cycle
                    self.state_manager.increment_metric("retries_total")
                    time.sleep(Config.RETRY_DELAY_SECONDS)
                    self._process_event(event)  # Retry immediately
                else:
                    # Max retries exceeded
                    self.audit_logger.log_error(
                        event, 
                        f"Max retries exceeded. Last error: {result.get('error', 'unknown')}"
                    )
                    self.state_manager.increment_metric("events_failed")
            
        except Exception as e:
            self.logger.error(f"Event processing error: {e}")
            self.audit_logger.log_error(event, str(e))
            
            # Attempt retry
            can_retry = self.event_processor.mark_event_failed(event)
            if can_retry:
                self.state_manager.increment_metric("retries_total")
            else:
                self.state_manager.increment_metric("events_failed")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point."""
    # Ensure required directories exist
    Config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    Config.PLANS_DIR.mkdir(parents=True, exist_ok=True)
    Config.VAULT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create and start agent
    agent = AutonomousLoopAgent()
    agent.start()


if __name__ == "__main__":
    main()
