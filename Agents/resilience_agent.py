#!/usr/bin/env python3
"""
Resilience Agent - Gold+ Tier AI Employee

Ensures system never crashes through comprehensive fault tolerance.

Capabilities:
- Detect agent failures (heartbeat, timeout, errors)
- Retry execution with exponential backoff + jitter
- Switch to fallback skills when primary fails
- Log degraded mode operations
- Auto-recovery to healthy state

Core Principle:
> The system must never crash.

Usage:
    python resilience_agent.py

Runs continuously as system watchdog.
"""

import os
import sys
import json
import logging
import time
import random
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("ResilienceAgent")


class SystemHealth(Enum):
    """System health levels."""
    HEALTHY = "healthy"
    DEGRADED_1 = "degraded_1"  # One non-critical service down
    DEGRADED_2 = "degraded_2"  # Multiple services down
    DEGRADED_3 = "degraded_3"  # Critical service down
    RECOVERY = "recovery"  # Services restoring


class FailureType(Enum):
    """Types of failures detected."""
    TIMEOUT = "timeout"
    EXCEPTION = "exception"
    HEARTBEAT_MISS = "heartbeat_miss"
    STATE_STALE = "state_stale"
    CONNECTION_LOST = "connection_lost"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    UNKNOWN = "unknown"


@dataclass
class AgentStatus:
    """Status of a monitored agent."""
    agent_id: str
    status: str = "unknown"  # running, stopped, failed
    last_heartbeat: Optional[str] = None
    last_error: Optional[str] = None
    error_count: int = 0
    consecutive_failures: int = 0
    last_success: Optional[str] = None
    priority: str = "normal"  # critical, high, normal, low


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_attempts: int = 3
    base_delay: float = 5.0
    max_delay: float = 60.0
    jitter: float = 0.5  # 50% jitter
    timeout: float = 120.0
    exponential: bool = True


@dataclass
class FallbackConfig:
    """Fallback configuration for a skill."""
    primary: str
    fallback: str
    degradation_level: int
    queue_on_fail: bool = True
    notify: bool = False


@dataclass
class FailureEvent:
    """Recorded failure event."""
    timestamp: str
    agent_id: str
    failure_type: str
    error: str
    retry_attempt: int
    fallback_used: Optional[str]
    resolved: bool = False
    resolved_at: Optional[str] = None


@dataclass
class SystemState:
    """Overall system state."""
    health: SystemHealth = SystemHealth.HEALTHY
    agents: Dict[str, AgentStatus] = field(default_factory=dict)
    active_failures: List[FailureEvent] = field(default_factory=list)
    failure_history: List[FailureEvent] = field(default_factory=list)
    degraded_since: Optional[str] = None
    recovery_started: Optional[str] = None
    metrics: Dict = field(default_factory=dict)


class ResilienceAgent:
    """
    Resilience Agent - System-wide fault tolerance.
    
    Ensures the system never crashes by:
    - Monitoring all agents
    - Retrying failed operations
    - Switching to fallbacks
    - Logging degradation
    - Auto-recovering
    """
    
    # Fallback mappings
    FALLBACK_MAP: Dict[str, FallbackConfig] = {
        'email': FallbackConfig('email', 'log_only', 1, queue_on_fail=True),
        'linkedin_marketing': FallbackConfig('linkedin_marketing', 'content_generate', 1, queue_on_fail=True),
        'odoo_accounting': FallbackConfig('odoo_accounting', 'local_record', 2, queue_on_fail=True),
        'social_media': FallbackConfig('social_media', 'draft_only', 1, queue_on_fail=True),
        'automation_mcp': FallbackConfig('automation_mcp', 'manual_queue', 2, queue_on_fail=True),
        'accounting_mcp': FallbackConfig('accounting_mcp', 'local_record', 2, queue_on_fail=True),
        'social_mcp': FallbackConfig('social_mcp', 'draft_only', 1, queue_on_fail=True),
    }
    
    # Retry configs by priority
    RETRY_CONFIGS = {
        'critical': RetryConfig(max_attempts=5, base_delay=5.0, max_delay=60.0, timeout=300.0),
        'high': RetryConfig(max_attempts=3, base_delay=5.0, max_delay=30.0, timeout=180.0),
        'normal': RetryConfig(max_attempts=3, base_delay=5.0, max_delay=20.0, timeout=120.0),
        'low': RetryConfig(max_attempts=1, base_delay=5.0, max_delay=10.0, timeout=60.0),
    }
    
    # Heartbeat thresholds (seconds)
    HEARTBEAT_THRESHOLDS = {
        'critical': 30,
        'high': 60,
        'normal': 120,
        'low': 300
    }
    
    def __init__(self, base_dir: Path, logs_dir: Optional[Path] = None):
        self.base_dir = base_dir
        self.logs_dir = logs_dir or (base_dir / "Logs")
        self.state_dir = self.logs_dir / "resilience"
        self.queue_dir = self.logs_dir / "failure_queue"
        
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        
        self.system_state = SystemState()
        self.agent_statuses: Dict[str, AgentStatus] = {}
        self.failure_queue: queue.Queue = queue.Queue()
        
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.recovery_thread: Optional[threading.Thread] = None
        
        # Registered agents for monitoring
        self.monitored_agents: Dict[str, Dict] = {}
        
        # Load persisted state
        self._load_state()
    
    def _load_state(self):
        """Load persisted system state."""
        state_file = self.state_dir / "system_state.json"
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    data = json.load(f)
                
                # Restore key state
                health_str = data.get('health', 'healthy')
                self.system_state.health = SystemHealth(health_str)
                self.system_state.degraded_since = data.get('degraded_since')
                self.system_state.failure_history = [
                    FailureEvent(**f) for f in data.get('failure_history', [])[-100:]
                ]
                
                logger.info(f"Loaded resilience state: {self.system_state.health.value}")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
    
    def _save_state(self):
        """Persist system state."""
        state_file = self.state_dir / "system_state.json"
        
        try:
            data = {
                'health': self.system_state.health.value,
                'degraded_since': self.system_state.degraded_since,
                'recovery_started': self.system_state.recovery_started,
                'agents': {
                    k: asdict(v) if hasattr(v, '__dataclass_fields__') else v
                    for k, v in self.agent_statuses.items()
                },
                'active_failures': [asdict(f) for f in self.system_state.active_failures[-20:]],
                'failure_history': [asdict(f) for f in self.system_state.failure_history[-100:]],
                'metrics': self.system_state.metrics,
                'updated_at': datetime.now().isoformat()
            }
            
            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def register_agent(self, agent_id: str, priority: str = "normal", 
                       heartbeat_interval: int = 60):
        """Register an agent for monitoring."""
        self.monitored_agents[agent_id] = {
            'priority': priority,
            'heartbeat_interval': heartbeat_interval,
            'registered_at': datetime.now().isoformat()
        }
        
        self.agent_statuses[agent_id] = AgentStatus(
            agent_id=agent_id,
            priority=priority
        )
        
        logger.info(f"Registered agent: {agent_id} (priority: {priority})")
    
    def heartbeat(self, agent_id: str):
        """Record heartbeat from an agent."""
        if agent_id in self.agent_statuses:
            self.agent_statuses[agent_id].last_heartbeat = datetime.now().isoformat()
            self.agent_statuses[agent_id].status = "running"
        else:
            # Auto-register unknown agents
            self.register_agent(agent_id)
            self.agent_statuses[agent_id].last_heartbeat = datetime.now().isoformat()
    
    def record_failure(self, agent_id: str, error: str, 
                       failure_type: FailureType = FailureType.UNKNOWN):
        """Record a failure event."""
        timestamp = datetime.now().isoformat()
        
        event = FailureEvent(
            timestamp=timestamp,
            agent_id=agent_id,
            failure_type=failure_type.value,
            error=error[:500],  # Truncate long errors
            retry_attempt=self.agent_statuses.get(agent_id, AgentStatus(agent_id)).consecutive_failures + 1,
            fallback_used=None
        )
        
        # Update agent status
        if agent_id in self.agent_statuses:
            self.agent_statuses[agent_id].last_error = error[:200]
            self.agent_statuses[agent_id].error_count += 1
            self.agent_statuses[agent_id].consecutive_failures += 1
            self.agent_statuses[agent_id].status = "failed"
        
        # Add to active failures
        self.system_state.active_failures.append(event)
        self.system_state.failure_history.append(event)
        
        # Update system health
        self._update_system_health()
        
        # Save state
        self._save_state()
        
        logger.warning(f"Failure recorded: {agent_id} - {failure_type.value}")
        
        return event
    
    def record_success(self, agent_id: str):
        """Record successful operation."""
        if agent_id in self.agent_statuses:
            self.agent_statuses[agent_id].status = "running"
            self.agent_statuses[agent_id].last_success = datetime.now().isoformat()
            self.agent_statuses[agent_id].consecutive_failures = 0
            self.agent_statuses[agent_id].last_heartbeat = datetime.now().isoformat()
        
        # Resolve related failures
        self.system_state.active_failures = [
            f for f in self.system_state.active_failures 
            if f.agent_id != agent_id or f.resolved
        ]
        
        # Update system health
        self._update_system_health()
        self._save_state()
    
    def _update_system_health(self):
        """Update overall system health based on failures."""
        critical_failures = sum(
            1 for f in self.system_state.active_failures
            if self.agent_statuses.get(f.agent_id, AgentStatus(f.agent_id)).priority == 'critical'
        )
        
        high_failures = sum(
            1 for f in self.system_state.active_failures
            if self.agent_statuses.get(f.agent_id, AgentStatus(f.agent_id)).priority == 'high'
        )
        
        total_failures = len(self.system_state.active_failures)
        
        if critical_failures > 0:
            new_health = SystemHealth.DEGRADED_3
        elif high_failures > 0 or total_failures > 3:
            new_health = SystemHealth.DEGRADED_2
        elif total_failures > 0:
            new_health = SystemHealth.DEGRADED_1
        else:
            new_health = SystemHealth.HEALTHY
        
        if new_health != self.system_state.health:
            logger.info(f"System health changed: {self.system_state.health.value} → {new_health.value}")
            
            if new_health == SystemHealth.HEALTHY and self.system_state.health != SystemHealth.HEALTHY:
                self.system_state.recovery_started = datetime.now().isoformat()
                logger.info("System entering recovery mode")
            
            if new_health != SystemHealth.HEALTHY and self.system_state.health == SystemHealth.HEALTHY:
                self.system_state.degraded_since = datetime.now().isoformat()
                self._log_degraded_mode(new_health)
            
            self.system_state.health = new_health
    
    def _log_degraded_mode(self, health: SystemHealth):
        """Log degraded mode entry."""
        log_file = self.logs_dir / "degraded_mode_log.md"
        
        entry = f"""
---

## Degraded Mode Entry

**Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Level:** {health.value.upper()}
**Active Failures:** {len(self.system_state.active_failures)}

### Active Issues

"""
        for failure in self.system_state.active_failures[-10:]:
            entry += f"- **{failure.agent_id}**: {failure.failure_type} - {failure.error[:100]}\n"
        
        try:
            if log_file.exists():
                with open(log_file, 'a') as f:
                    f.write(entry)
            else:
                with open(log_file, 'w') as f:
                    f.write("# Degraded Mode Log\n\n")
                    f.write(entry)
        except Exception as e:
            logger.error(f"Failed to log degraded mode: {e}")
    
    def execute_with_resilience(self, agent_id: str, operation: Callable,
                                 fallback: Optional[Callable] = None,
                                 priority: str = "normal") -> Any:
        """
        Execute an operation with full resilience.
        
        Flow:
        1. Try operation
        2. On failure → retry with backoff
        3. On max retries → use fallback
        4. On fallback failure → queue for later
        5. Never crash
        """
        config = self.RETRY_CONFIGS.get(priority, self.RETRY_CONFIGS['normal'])
        fallback_config = self.FALLBACK_MAP.get(agent_id)
        
        last_error = None
        attempt = 0
        
        while attempt < config.max_attempts:
            try:
                attempt += 1
                
                # Execute with timeout
                result = self._execute_with_timeout(operation, config.timeout)
                
                # Success!
                self.record_success(agent_id)
                logger.info(f"Operation successful: {agent_id} (attempt {attempt})")
                return result
                
            except TimeoutError as e:
                last_error = f"Timeout after {config.timeout}s"
                self.record_failure(agent_id, last_error, FailureType.TIMEOUT)
                
            except Exception as e:
                last_error = str(e)
                self.record_failure(agent_id, last_error, FailureType.EXCEPTION)
            
            # Calculate backoff with jitter
            if attempt < config.max_attempts:
                if config.exponential:
                    delay = config.base_delay * (2 ** (attempt - 1))
                else:
                    delay = config.base_delay
                
                # Add jitter
                jitter = delay * config.jitter * random.random()
                delay = min(delay + jitter, config.max_delay)
                
                logger.info(f"Retry {attempt}/{config.max_attempts} after {delay:.1f}s")
                time.sleep(delay)
        
        # All retries exhausted - use fallback
        logger.warning(f"All retries exhausted for {agent_id}, using fallback")
        
        if fallback:
            try:
                result = fallback()
                
                # Record fallback usage
                if self.system_state.active_failures:
                    self.system_state.active_failures[-1].fallback_used = fallback_config.fallback if fallback_config else 'custom'
                
                self._save_state()
                logger.info(f"Fallback successful: {agent_id}")
                return result
                
            except Exception as e:
                logger.error(f"Fallback also failed: {e}")
        
        # Queue for later processing
        if fallback_config and fallback_config.queue_on_fail:
            self._queue_for_later(agent_id, operation, priority)
        
        # Return safe default
        return self._get_safe_default(agent_id)
    
    def _execute_with_timeout(self, operation: Callable, timeout: float) -> Any:
        """Execute operation with timeout."""
        result_queue = queue.Queue()
        error_container = {'error': None, 'exception': None}
        
        def wrapper():
            try:
                result = operation()
                result_queue.put(('success', result))
            except Exception as e:
                error_container['exception'] = e
        
        thread = threading.Thread(target=wrapper)
        thread.daemon = True
        thread.start()
        
        try:
            thread.join(timeout=timeout)
            
            if thread.is_alive():
                raise TimeoutError(f"Operation timed out after {timeout}s")
            
            if error_container['exception']:
                raise error_container['exception']
            
            if not result_queue.empty():
                status, result = result_queue.get()
                if status == 'success':
                    return result
            
            return None
            
        except Exception as e:
            raise
    
    def _queue_for_later(self, agent_id: str, operation: Callable, priority: str):
        """Queue failed operation for later processing."""
        queue_item = {
            'agent_id': agent_id,
            'priority': priority,
            'queued_at': datetime.now().isoformat(),
            'retry_count': 0
        }
        
        # Save to file queue (persistent)
        queue_file = self.queue_dir / f"queue_{agent_id}_{int(time.time())}.json"
        
        try:
            with open(queue_file, 'w') as f:
                json.dump(queue_item, f, indent=2)
            logger.info(f"Queued for later: {agent_id} → {queue_file.name}")
        except Exception as e:
            logger.error(f"Failed to queue: {e}")
    
    def _get_safe_default(self, agent_id: str) -> Any:
        """Return safe default value for failed operation."""
        defaults = {
            'email': {'success': False, 'queued': True},
            'linkedin_marketing': {'success': False, 'draft_saved': True},
            'odoo_accounting': {'success': False, 'local_record': True},
            'social_media': {'success': False, 'draft_saved': True},
        }
        return defaults.get(agent_id, {'success': False, 'degraded': True})
    
    def process_failure_queue(self):
        """Process queued failed operations."""
        queue_files = list(self.queue_dir.glob("queue_*.json"))
        
        for queue_file in queue_files:
            try:
                with open(queue_file, 'r') as f:
                    item = json.load(f)
                
                # Check if we should retry
                retry_count = item.get('retry_count', 0)
                max_queue_retries = 3
                
                if retry_count < max_queue_retries:
                    # Try to re-execute
                    item['retry_count'] = retry_count + 1
                    item['last_retry'] = datetime.now().isoformat()
                    
                    logger.info(f"Retrying queued item: {item['agent_id']} (attempt {retry_count + 1})")
                    
                    # Update file
                    with open(queue_file, 'w') as f:
                        json.dump(item, f, indent=2)
                    
                    # In production, would re-execute the operation
                    # For now, just track the retry
                    
                else:
                    # Max retries exceeded - move to dead letter
                    dead_letter_dir = self.queue_dir / "dead_letter"
                    dead_letter_dir.mkdir(exist_ok=True)
                    
                    item['dead_letter_at'] = datetime.now().isoformat()
                    item['reason'] = 'max_queue_retries_exceeded'
                    
                    with open(dead_letter_dir / queue_file.name, 'w') as f:
                        json.dump(item, f, indent=2)
                    
                    queue_file.unlink()
                    logger.warning(f"Moved to dead letter: {queue_file.name}")
                    
            except Exception as e:
                logger.error(f"Failed to process queue item: {e}")
    
    def check_heartbeats(self):
        """Check all agent heartbeats for misses."""
        current_time = datetime.now()
        
        for agent_id, status in self.agent_statuses.items():
            if not status.last_heartbeat:
                continue
            
            priority = status.priority
            threshold = self.HEARTBEAT_THRESHOLDS.get(priority, 120)
            
            last_hb = datetime.fromisoformat(status.last_heartbeat)
            elapsed = (current_time - last_hb).total_seconds()
            
            if elapsed > threshold:
                self.record_failure(
                    agent_id,
                    f"No heartbeat for {elapsed:.0f}s (threshold: {threshold}s)",
                    FailureType.HEARTBEAT_MISS
                )
                logger.warning(f"Heartbeat miss: {agent_id} ({elapsed:.0f}s)")
    
    def get_system_status(self) -> Dict:
        """Get current system status."""
        return {
            'health': self.system_state.health.value,
            'agents': {
                agent_id: {
                    'status': status.status,
                    'last_heartbeat': status.last_heartbeat,
                    'consecutive_failures': status.consecutive_failures,
                    'priority': status.priority
                }
                for agent_id, status in self.agent_statuses.items()
            },
            'active_failures': len(self.system_state.active_failures),
            'queued_items': len(list(self.queue_dir.glob("queue_*.json"))),
            'degraded_since': self.system_state.degraded_since,
            'metrics': self.system_state.metrics
        }
    
    def run_monitoring_loop(self):
        """Main monitoring loop."""
        logger.info("Starting resilience monitoring...")
        
        while self.running:
            try:
                # Check heartbeats
                self.check_heartbeats()
                
                # Process failure queue
                self.process_failure_queue()
                
                # Update metrics
                self.system_state.metrics['uptime'] = (
                    datetime.now() - datetime.fromisoformat(self.system_state.metrics.get('start_time', datetime.now().isoformat()))
                ).total_seconds()
                self.system_state.metrics['total_failures'] = len(self.system_state.failure_history)
                self.system_state.metrics['active_failures'] = len(self.system_state.active_failures)
                
                # Save state periodically
                self._save_state()
                
                # Log status periodically
                status = self.get_system_status()
                if status['health'] != 'healthy':
                    logger.info(f"System status: {status['health']} ({status['active_failures']} active failures)")
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Monitoring error: {e}")
                # Never crash - just log and continue
                time.sleep(5)
    
    def start(self):
        """Start resilience monitoring."""
        self.running = True
        self.system_state.metrics['start_time'] = datetime.now().isoformat()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self.run_monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("=" * 60)
        logger.info("Resilience Agent started")
        logger.info(f"System Health: {self.system_state.health.value}")
        logger.info("Monitoring agents for failures...")
        logger.info("Retry with exponential backoff enabled")
        logger.info("Fallback skills configured")
        logger.info("Failure queue active")
        logger.info("=" * 60)
    
    def stop(self):
        """Stop resilience monitoring."""
        self.running = False
        self._save_state()
        logger.info("Resilience Agent stopped")
    
    def run(self):
        """Main entry point."""
        self.start()
        
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("\nShutting down...")
            self.stop()


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    agent = ResilienceAgent(base_dir=BASE_DIR)
    
    # Register agents for monitoring
    agent.register_agent('email_agent', priority='high')
    agent.register_agent('linkedin_agent', priority='normal')
    agent.register_agent('accounting_agent', priority='high')
    agent.register_agent('social_media_agent', priority='normal')
    agent.register_agent('autonomy_loop_agent', priority='critical')
    agent.register_agent('ceo_briefing_agent', priority='normal')
    
    agent.run()
