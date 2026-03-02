#!/usr/bin/env python3
"""
PLATINUM Watchdog - System Health Monitor

Monitors and auto-restarts critical PLATINUM Tier services:
- Watchers (filesystem, gmail, whatsapp, linkedin)
- Cloud Orchestrator
- Sync Service
- System Resources (disk, memory)

Auto-restarts failed processes and logs all events.
"""

import os
import sys
import json
import time
import signal
import logging
import threading
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import psutil

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.parent.resolve()
CLOUD_RUNTIME_DIR = Path(__file__).parent.resolve()
LOGS_DIR = BASE_DIR / "Logs"
VENV_DIR = BASE_DIR / "venv"

# System health log
SYSTEM_HEALTH_LOG = LOGS_DIR / "system_health.log"

# Monitored processes
MONITORED_PROCESSES = {
    'filesystem_watcher': {
        'script': BASE_DIR / 'filesystem_watcher.py',
        'name': 'Filesystem Watcher',
        'restart_delay': 5,
        'max_restarts': 10,
        'enabled': True,
    },
    'cloud_orchestrator': {
        'script': CLOUD_RUNTIME_DIR / 'orchestrator_cloud.py',
        'name': 'Cloud Orchestrator',
        'restart_delay': 5,
        'max_restarts': 10,
        'enabled': True,
    },
    'sync_manager': {
        'script': CLOUD_RUNTIME_DIR / 'sync_manager.py',
        'name': 'Sync Manager',
        'restart_delay': 5,
        'max_restarts': 10,
        'enabled': True,
    },
    'health_monitor': {
        'script': CLOUD_RUNTIME_DIR / 'health_monitor.py',
        'name': 'Health Monitor',
        'restart_delay': 5,
        'max_restarts': 10,
        'enabled': True,
    },
    'delegation_manager': {
        'script': CLOUD_RUNTIME_DIR / 'delegation_manager.py',
        'name': 'Delegation Manager',
        'restart_delay': 5,
        'max_restarts': 10,
        'enabled': True,
    },
    'approval_orchestrator': {
        'script': CLOUD_RUNTIME_DIR / 'approval_orchestrator.py',
        'name': 'Approval Orchestrator',
        'restart_delay': 5,
        'max_restarts': 10,
        'enabled': True,
    },
    'odoo_cloud_agent': {
        'script': CLOUD_RUNTIME_DIR / 'odoo_cloud_agent.py',
        'name': 'Odoo Cloud Agent',
        'restart_delay': 5,
        'max_restarts': 10,
        'enabled': False,  # Disabled by default, enable if Odoo is configured
    },
}

# Resource thresholds
RESOURCE_THRESHOLDS = {
    'disk_usage_warning': 75.0,    # Percent
    'disk_usage_critical': 90.0,   # Percent
    'memory_usage_warning': 75.0,  # Percent
    'memory_usage_critical': 90.0, # Percent
    'cpu_usage_warning': 80.0,     # Percent
    'cpu_usage_critical': 95.0,    # Percent
}

# Monitoring intervals
MONITOR_INTERVAL = 10  # seconds
RESOURCE_CHECK_INTERVAL = 30  # seconds

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to system health log."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Main system health log
    log_file = SYSTEM_HEALTH_LOG

    # Also create daily rotated logs
    daily_log = LOGS_DIR / f"watchdog_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.FileHandler(daily_log, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("PLATINUMWatchdog")


logger = setup_logging()


# =============================================================================
# Enums and Data Classes
# =============================================================================

class ProcessStatus(Enum):
    """Process status enumeration."""
    RUNNING = "running"
    STOPPED = "stopped"
    CRASHED = "crashed"
    RESTARTING = "restarting"
    DISABLED = "disabled"
    UNKNOWN = "unknown"


class HealthStatus(Enum):
    """System health status."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ProcessInfo:
    """Information about a monitored process."""
    name: str
    script: Path
    status: ProcessStatus = ProcessStatus.STOPPED
    pid: Optional[int] = None
    process: Optional[subprocess.Popen] = None
    start_time: Optional[datetime] = None
    restart_count: int = 0
    last_restart: Optional[datetime] = None
    last_error: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'status': self.status.value,
            'pid': self.pid,
            'restart_count': self.restart_count,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'last_restart': self.last_restart.isoformat() if self.last_restart else None,
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
        }


@dataclass
class ResourceUsage:
    """System resource usage."""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_gb: float = 0.0
    memory_total_gb: float = 0.0
    disk_percent: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'cpu_percent': self.cpu_percent,
            'memory_percent': self.memory_percent,
            'memory_used_gb': round(self.memory_used_gb, 2),
            'memory_total_gb': round(self.memory_total_gb, 2),
            'disk_percent': self.disk_percent,
            'disk_used_gb': round(self.disk_used_gb, 2),
            'disk_total_gb': round(self.disk_total_gb, 2),
            'timestamp': self.timestamp.isoformat(),
        }


@dataclass
class SystemHealth:
    """Overall system health."""
    status: HealthStatus = HealthStatus.HEALTHY
    timestamp: datetime = field(default_factory=datetime.now)
    processes: Dict[str, ProcessInfo] = field(default_factory=dict)
    resources: Optional[ResourceUsage] = None
    alerts: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'processes': {
                name: info.to_dict() 
                for name, info in self.processes.items()
            },
            'resources': self.resources.to_dict() if self.resources else None,
            'alerts': self.alerts,
        }


# =============================================================================
# Process Manager
# =============================================================================

class ProcessManager:
    """
    Manages monitored processes with auto-restart capability.
    """
    
    def __init__(self):
        self.processes: Dict[str, ProcessInfo] = {}
        self.lock = threading.Lock()
        self._initialize_processes()
    
    def _initialize_processes(self) -> None:
        """Initialize process info from configuration."""
        for name, config in MONITORED_PROCESSES.items():
            self.processes[name] = ProcessInfo(
                name=name,
                script=config['script'],
                status=ProcessStatus.DISABLED if not config['enabled'] else ProcessStatus.STOPPED,
            )
    
    def start_process(self, process_name: str) -> Tuple[bool, str]:
        """Start a monitored process."""
        if process_name not in self.processes:
            return False, f"Unknown process: {process_name}"
        
        proc_info = self.processes[process_name]
        config = MONITORED_PROCESSES.get(process_name, {})
        
        # Check if disabled
        if not config.get('enabled', True):
            return False, f"Process {process_name} is disabled"
        
        # Check if already running
        if proc_info.status == ProcessStatus.RUNNING:
            return False, f"Process {process_name} is already running"
        
        # Check script exists
        if not proc_info.script.exists():
            proc_info.last_error = f"Script not found: {proc_info.script}"
            logger.error(proc_info.last_error)
            return False, proc_info.last_error
        
        try:
            logger.info(f"Starting process: {process_name} ({proc_info.script})")
            
            # Determine Python interpreter
            python_cmd = sys.executable
            
            # Start process
            proc_info.process = subprocess.Popen(
                [python_cmd, str(proc_info.script)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if os.name != 'nt' else None,
            )
            
            proc_info.pid = proc_info.process.pid
            proc_info.status = ProcessStatus.RUNNING
            proc_info.start_time = datetime.now()
            proc_info.last_error = ""
            
            logger.info(f"Process started: {process_name} (PID: {proc_info.pid})")
            return True, f"Started with PID {proc_info.pid}"
            
        except Exception as e:
            proc_info.status = ProcessStatus.CRASHED
            proc_info.last_error = str(e)
            logger.error(f"Failed to start {process_name}: {e}")
            return False, str(e)
    
    def stop_process(self, process_name: str) -> Tuple[bool, str]:
        """Stop a monitored process."""
        if process_name not in self.processes:
            return False, f"Unknown process: {process_name}"
        
        proc_info = self.processes[process_name]
        
        if proc_info.status != ProcessStatus.RUNNING or not proc_info.process:
            return False, f"Process {process_name} is not running"
        
        try:
            logger.info(f"Stopping process: {process_name} (PID: {proc_info.pid})")
            
            # Try graceful shutdown
            proc_info.process.terminate()
            
            # Wait for process to stop
            try:
                proc_info.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                # Force kill
                proc_info.process.kill()
                proc_info.process.wait(timeout=5)
            
            proc_info.status = ProcessStatus.STOPPED
            proc_info.process = None
            proc_info.pid = None
            
            logger.info(f"Process stopped: {process_name}")
            return True, "Stopped successfully"
            
        except Exception as e:
            proc_info.last_error = str(e)
            logger.error(f"Failed to stop {process_name}: {e}")
            return False, str(e)
    
    def restart_process(self, process_name: str) -> Tuple[bool, str]:
        """Restart a process with rate limiting."""
        if process_name not in self.processes:
            return False, f"Unknown process: {process_name}"
        
        proc_info = self.processes[process_name]
        config = MONITORED_PROCESSES.get(process_name, {})
        
        # Check max restarts
        max_restarts = config.get('max_restarts', 10)
        if proc_info.restart_count >= max_restarts:
            proc_info.status = ProcessStatus.CRASHED
            proc_info.last_error = f"Max restarts ({max_restarts}) exceeded"
            logger.error(proc_info.last_error)
            return False, proc_info.last_error
        
        # Check restart delay
        restart_delay = config.get('restart_delay', 5)
        if proc_info.last_restart:
            time_since_restart = (datetime.now() - proc_info.last_restart).total_seconds()
            if time_since_restart < restart_delay:
                wait_time = restart_delay - time_since_restart
                logger.info(f"Waiting {wait_time:.1f}s before restart of {process_name}")
                return False, f"Restart delay: {wait_time:.1f}s remaining"
        
        # Stop if running
        if proc_info.status == ProcessStatus.RUNNING:
            self.stop_process(process_name)
        
        # Update restart info
        proc_info.status = ProcessStatus.RESTARTING
        proc_info.restart_count += 1
        proc_info.last_restart = datetime.now()
        
        logger.info(f"Restarting process: {process_name} (attempt {proc_info.restart_count})")
        
        # Start process
        return self.start_process(process_name)
    
    def check_process_status(self, process_name: str) -> ProcessStatus:
        """Check if a process is still running."""
        if process_name not in self.processes:
            return ProcessStatus.UNKNOWN
        
        proc_info = self.processes[process_name]
        
        if proc_info.status == ProcessStatus.DISABLED:
            return ProcessStatus.DISABLED
        
        if proc_info.status == ProcessStatus.STOPPED:
            return ProcessStatus.STOPPED
        
        if not proc_info.process:
            proc_info.status = ProcessStatus.CRASHED
            return ProcessStatus.CRASHED
        
        # Check if process is running
        poll_result = proc_info.process.poll()
        
        if poll_result is None:
            # Process is running, update resource usage
            try:
                ps_proc = psutil.Process(proc_info.pid)
                proc_info.cpu_percent = ps_proc.cpu_percent()
                proc_info.memory_percent = ps_proc.memory_percent()
            except:
                pass
            
            proc_info.status = ProcessStatus.RUNNING
        else:
            # Process has stopped
            proc_info.status = ProcessStatus.CRASHED
            proc_info.process = None
            proc_info.pid = None
            
            # Get exit code
            if hasattr(poll_result, 'returncode'):
                proc_info.last_error = f"Exit code: {poll_result.returncode}"
            else:
                proc_info.last_error = f"Exit code: {poll_result}"
            
            logger.warning(f"Process crashed: {process_name} - {proc_info.last_error}")
        
        return proc_info.status
    
    def get_all_processes(self) -> Dict[str, ProcessInfo]:
        """Get all monitored processes."""
        return self.processes.copy()
    
    def get_running_processes(self) -> List[str]:
        """Get list of running process names."""
        return [
            name for name, info in self.processes.items()
            if info.status == ProcessStatus.RUNNING
        ]
    
    def get_failed_processes(self) -> List[str]:
        """Get list of failed/crashed process names."""
        return [
            name for name, info in self.processes.items()
            if info.status in (ProcessStatus.CRASHED, ProcessStatus.STOPPED)
            and MONITORED_PROCESSES.get(name, {}).get('enabled', False)
        ]


# =============================================================================
# Resource Monitor
# =============================================================================

class ResourceMonitor:
    """
    Monitors system resources (CPU, memory, disk).
    """
    
    def __init__(self):
        self.thresholds = RESOURCE_THRESHOLDS
        self.last_check: Optional[ResourceUsage] = None
    
    def check_resources(self) -> ResourceUsage:
        """Check current resource usage."""
        usage = ResourceUsage(timestamp=datetime.now())
        
        # CPU
        usage.cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory
        memory = psutil.virtual_memory()
        usage.memory_percent = memory.percent
        usage.memory_used_gb = memory.used / (1024 ** 3)
        usage.memory_total_gb = memory.total / (1024 ** 3)
        
        # Disk
        disk = psutil.disk_usage(str(BASE_DIR))
        usage.disk_percent = disk.percent
        usage.disk_used_gb = disk.used / (1024 ** 3)
        usage.disk_total_gb = disk.total / (1024 ** 3)
        
        self.last_check = usage
        return usage
    
    def get_alerts(self, usage: Optional[ResourceUsage] = None) -> List[str]:
        """Get resource alerts based on thresholds."""
        if usage is None:
            usage = self.last_check
        
        if usage is None:
            return []
        
        alerts = []
        
        # Disk alerts
        if usage.disk_percent >= self.thresholds['disk_usage_critical']:
            alerts.append(f"CRITICAL: Disk usage at {usage.disk_percent:.1f}%")
        elif usage.disk_percent >= self.thresholds['disk_usage_warning']:
            alerts.append(f"WARNING: Disk usage at {usage.disk_percent:.1f}%")
        
        # Memory alerts
        if usage.memory_percent >= self.thresholds['memory_usage_critical']:
            alerts.append(f"CRITICAL: Memory usage at {usage.memory_percent:.1f}%")
        elif usage.memory_percent >= self.thresholds['memory_usage_warning']:
            alerts.append(f"WARNING: Memory usage at {usage.memory_percent:.1f}%")
        
        # CPU alerts
        if usage.cpu_percent >= self.thresholds['cpu_usage_critical']:
            alerts.append(f"CRITICAL: CPU usage at {usage.cpu_percent:.1f}%")
        elif usage.cpu_percent >= self.thresholds['cpu_usage_warning']:
            alerts.append(f"WARNING: CPU usage at {usage.cpu_percent:.1f}%")
        
        return alerts
    
    def get_health_status(self, usage: Optional[ResourceUsage] = None) -> HealthStatus:
        """Get overall resource health status."""
        alerts = self.get_alerts(usage)
        
        if any('CRITICAL' in alert for alert in alerts):
            return HealthStatus.CRITICAL
        elif any('WARNING' in alert for alert in alerts):
            return HealthStatus.WARNING
        else:
            return HealthStatus.HEALTHY


# =============================================================================
# PLATINUM Watchdog
# =============================================================================

class PLATINUMWatchdog:
    """
    Main watchdog that monitors all services and auto-restarts failed ones.
    """
    
    def __init__(self):
        self.process_manager = ProcessManager()
        self.resource_monitor = ResourceMonitor()
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.resource_thread: Optional[threading.Thread] = None
        self.start_time: Optional[datetime] = None
        
        # Statistics
        self.stats = {
            'process_starts': 0,
            'process_restarts': 0,
            'resource_alerts': 0,
            'crashes_detected': 0,
        }
        self.lock = threading.Lock()
        
        logger.info("PLATINUM Watchdog initialized")
    
    def start(self) -> None:
        """Start the watchdog."""
        self.running = True
        self.start_time = datetime.now()
        
        # Start all enabled processes
        logger.info("Starting monitored processes...")
        for name in MONITORED_PROCESSES:
            if MONITORED_PROCESSES[name].get('enabled', False):
                success, msg = self.process_manager.start_process(name)
                if success:
                    with self.lock:
                        self.stats['process_starts'] += 1
                time.sleep(1)  # Stagger starts
        
        # Start monitoring threads
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.resource_thread = threading.Thread(target=self._resource_loop, daemon=True)
        self.resource_thread.start()
        
        logger.info("PLATINUM Watchdog started")
    
    def stop(self) -> None:
        """Stop the watchdog."""
        logger.info("Stopping PLATINUM Watchdog...")
        self.running = False
        
        # Stop monitoring threads
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        if self.resource_thread:
            self.resource_thread.join(timeout=5)
        
        # Stop all processes
        logger.info("Stopping all monitored processes...")
        for name in list(MONITORED_PROCESSES.keys()):
            self.process_manager.stop_process(name)
        
        logger.info("PLATINUM Watchdog stopped")
    
    def _monitor_loop(self) -> None:
        """Main process monitoring loop."""
        while self.running:
            try:
                self._check_and_restart_processes()
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
            
            time.sleep(MONITOR_INTERVAL)
    
    def _resource_loop(self) -> None:
        """Resource monitoring loop."""
        while self.running:
            try:
                usage = self.resource_monitor.check_resources()
                alerts = self.resource_monitor.get_alerts(usage)
                
                for alert in alerts:
                    logger.warning(f"Resource Alert: {alert}")
                    with self.lock:
                        self.stats['resource_alerts'] += 1
                
                # Log resource status
                logger.debug(
                    f"Resources: CPU={usage.cpu_percent:.1f}%, "
                    f"Memory={usage.memory_percent:.1f}%, "
                    f"Disk={usage.disk_percent:.1f}%"
                )
                
            except Exception as e:
                logger.error(f"Resource loop error: {e}")
            
            time.sleep(RESOURCE_CHECK_INTERVAL)
    
    def _check_and_restart_processes(self) -> None:
        """Check all processes and restart failed ones."""
        for name in MONITORED_PROCESSES:
            if not MONITORED_PROCESSES[name].get('enabled', False):
                continue
            
            status = self.process_manager.check_process_status(name)
            
            if status == ProcessStatus.CRASHED:
                logger.warning(f"Process crashed: {name}")
                with self.lock:
                    self.stats['crashes_detected'] += 1
                
                # Attempt restart
                success, msg = self.process_manager.restart_process(name)
                
                if success:
                    with self.lock:
                        self.stats['process_restarts'] += 1
                    logger.info(f"Process restarted: {name}")
                else:
                    logger.error(f"Failed to restart {name}: {msg}")
            
            elif status == ProcessStatus.STOPPED:
                logger.info(f"Process stopped: {name}")
                
                # Attempt restart
                success, msg = self.process_manager.restart_process(name)
                
                if success:
                    with self.lock:
                        self.stats['process_restarts'] += 1
    
    def get_health(self) -> SystemHealth:
        """Get current system health."""
        health = SystemHealth(timestamp=datetime.now())
        
        # Get process info
        health.processes = self.process_manager.get_all_processes()
        
        # Get resource info
        health.resources = self.resource_monitor.last_check
        
        # Get resource alerts
        if health.resources:
            health.alerts = self.resource_monitor.get_alerts(health.resources)
        
        # Determine overall status
        failed = self.process_manager.get_failed_processes()
        
        if failed:
            health.status = HealthStatus.CRITICAL if len(failed) > 2 else HealthStatus.WARNING
            health.alerts.append(f"Failed processes: {', '.join(failed)}")
        elif health.resources and self.resource_monitor.get_health_status(health.resources) == HealthStatus.CRITICAL:
            health.status = HealthStatus.CRITICAL
        elif health.alerts:
            health.status = HealthStatus.WARNING
        else:
            health.status = HealthStatus.HEALTHY
        
        return health
    
    def get_stats(self) -> Dict[str, Any]:
        """Get watchdog statistics."""
        with self.lock:
            stats = self.stats.copy()
        
        stats['uptime'] = str(datetime.now() - self.start_time) if self.start_time else "N/A"
        stats['running_processes'] = len(self.process_manager.get_running_processes())
        stats['failed_processes'] = len(self.process_manager.get_failed_processes())
        
        return stats
    
    def generate_health_report(self) -> Path:
        """Generate a health report."""
        health = self.get_health()
        stats = self.get_stats()
        
        report_file = LOGS_DIR / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        content = f"""# PLATINUM Watchdog Health Report

**Generated:** {health.timestamp.isoformat()}
**Overall Status:** {health.status.value.upper()}

---

## Statistics

| Metric | Value |
|--------|-------|
| Uptime | {stats['uptime']} |
| Running Processes | {stats['running_processes']} |
| Failed Processes | {stats['failed_processes']} |
| Process Starts | {stats['process_starts']} |
| Process Restarts | {stats['process_restarts']} |
| Crashes Detected | {stats['crashes_detected']} |
| Resource Alerts | {stats['resource_alerts']} |

---

## Process Status

| Process | Status | PID | Restarts | CPU | Memory |
|---------|--------|-----|----------|-----|--------|
"""
        
        for name, info in health.processes.items():
            content += (
                f"| {name} | {info.status.value} | "
                f"{info.pid or 'N/A'} | {info.restart_count} | "
                f"{info.cpu_percent:.1f}% | {info.memory_percent:.1f}% |\n"
            )
        
        if health.resources:
            content += f"""
---

## Resource Usage

| Resource | Usage | Status |
|----------|-------|--------|
| CPU | {health.resources.cpu_percent:.1f}% | {'⚠️' if health.resources.cpu_percent > 80 else '✅'} |
| Memory | {health.resources.memory_percent:.1f}% | {'⚠️' if health.resources.memory_percent > 80 else '✅'} |
| Disk | {health.resources.disk_percent:.1f}% | {'⚠️' if health.resources.disk_percent > 80 else '✅'} |
| Memory Used | {health.resources.memory_used_gb:.2f} GB / {health.resources.memory_total_gb:.2f} GB | |
| Disk Used | {health.resources.disk_used_gb:.2f} GB / {health.resources.disk_total_gb:.2f} GB | |
"""
        
        if health.alerts:
            content += """
---

## Alerts

"""
            for alert in health.alerts:
                content += f"- {alert}\n"
        
        content += """
---
*Generated by PLATINUM Watchdog*
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Health report generated: {report_file}")
        return report_file


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for PLATINUM Watchdog."""
    print("=" * 60)
    print("PLATINUM Watchdog - System Health Monitor")
    print("=" * 60)
    print()
    print("Monitored Services:")
    for name, config in MONITORED_PROCESSES.items():
        status = "ENABLED" if config.get('enabled', False) else "DISABLED"
        print(f"  - {config['name']} [{status}]")
    print()
    print("Resource Thresholds:")
    print(f"  - Disk Warning: {RESOURCE_THRESHOLDS['disk_usage_warning']}%")
    print(f"  - Disk Critical: {RESOURCE_THRESHOLDS['disk_usage_critical']}%")
    print(f"  - Memory Warning: {RESOURCE_THRESHOLDS['memory_usage_warning']}%")
    print(f"  - Memory Critical: {RESOURCE_THRESHOLDS['memory_usage_critical']}%")
    print()
    print("Auto-restart: ENABLED")
    print(f"Log File: {SYSTEM_HEALTH_LOG}")
    print()
    print("=" * 60)

    watchdog = PLATINUMWatchdog()
    
    # Handle signals
    def signal_handler(sig, frame):
        print("\nShutdown requested...")
        watchdog.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        watchdog.start()
        logger.info("Watchdog running. Press Ctrl+C to stop.")
        
        # Keep main thread alive and show periodic status
        while True:
            time.sleep(60)
            
            health = watchdog.get_health()
            stats = watchdog.get_stats()
            
            status_emoji = {
                HealthStatus.HEALTHY: "✅",
                HealthStatus.WARNING: "⚠️",
                HealthStatus.CRITICAL: "❌",
            }
            emoji = status_emoji.get(health.status, "❓")
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] "
                  f"{emoji} Status: {health.status.value.upper()} | "
                  f"Running: {stats['running_processes']} | "
                  f"Failed: {stats['failed_processes']}")
            
            # Generate hourly report
            if datetime.now().minute == 0:
                watchdog.generate_health_report()
            
    except KeyboardInterrupt:
        print("\nShutdown requested...")
    finally:
        watchdog.stop()
        
        # Generate final report
        try:
            report_path = watchdog.generate_health_report()
            print(f"\nFinal health report: {report_path}")
        except Exception as e:
            print(f"\nCould not generate final report: {e}")
        
        print("\nPLATINUM Watchdog stopped.")


if __name__ == "__main__":
    main()
