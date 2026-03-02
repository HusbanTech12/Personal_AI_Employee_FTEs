#!/usr/bin/env python3
"""
Cloud Health Monitor - PLATINUM Tier

Monitors the health of all cloud runtime components.
Provides real-time status, alerts, and recovery recommendations.

Responsibilities:
- Monitor orchestrator health
- Track draft generation rates
- Monitor approval request queue
- Detect and report anomalies
- Generate health reports
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import psutil

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.parent.resolve()
VAULT_PATH = BASE_DIR / "notes"
CLOUD_RUNTIME_DIR = Path(__file__).parent.resolve()

LOGS_DIR = BASE_DIR / "Logs"
DRAFTS_DIR = VAULT_PATH / "Drafts"
APPROVAL_REQUESTS_DIR = VAULT_PATH / "Approval_Requests"
HEALTH_REPORTS_DIR = CLOUD_RUNTIME_DIR / "health_reports"

# Health check intervals
HEALTH_CHECK_INTERVAL = 30  # seconds
ALERT_THRESHOLD_DRAFTS = 100  # Alert if drafts exceed this count
ALERT_THRESHOLD_APPROVALS = 50  # Alert if pending approvals exceed this

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to both file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"cloud_health_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("CloudHealthMonitor")


logger = setup_logging()


# =============================================================================
# Enums and Data Classes
# =============================================================================

class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class ComponentType(Enum):
    """Cloud component types."""
    ORCHESTRATOR = "orchestrator"
    DRAFT_GENERATOR = "draft_generator"
    APPROVAL_MANAGER = "approval_manager"
    SYNC_MANAGER = "sync_manager"
    STORAGE = "storage"


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    component: ComponentType
    status: HealthStatus
    message: str
    last_check: datetime = field(default_factory=datetime.now)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemHealth:
    """Overall system health status."""
    status: HealthStatus
    timestamp: datetime = field(default_factory=datetime.now)
    components: Dict[ComponentType, ComponentHealth] = field(default_factory=dict)
    alerts: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


# =============================================================================
# Health Monitor
# =============================================================================

class CloudHealthMonitor:
    """
    Monitors health of all cloud runtime components.
    Provides continuous monitoring, alerting, and reporting.
    """

    def __init__(self):
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.last_health: Optional[SystemHealth] = None
        self.health_history: List[SystemHealth] = []
        self.alerts: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        
        # Ensure directories exist
        HEALTH_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    def start(self) -> None:
        """Start continuous health monitoring."""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Cloud Health Monitor started")

    def stop(self) -> None:
        """Stop continuous health monitoring."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Cloud Health Monitor stopped")

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self.running:
            try:
                health = self.check_health()
                
                # Store health history (keep last 100 checks)
                with self.lock:
                    self.last_health = health
                    self.health_history.append(health)
                    if len(self.health_history) > 100:
                        self.health_history.pop(0)

                # Check for alerts
                self._check_alerts(health)

                # Log status
                self._log_health_status(health)

            except Exception as e:
                logger.error(f"Health monitoring error: {e}")

            time.sleep(HEALTH_CHECK_INTERVAL)

    def check_health(self) -> SystemHealth:
        """Perform comprehensive health check."""
        health = SystemHealth(status=HealthStatus.HEALTHY)

        # Check each component
        health.components[ComponentType.ORCHESTRATOR] = self._check_orchestrator()
        health.components[ComponentType.DRAFT_GENERATOR] = self._check_draft_generator()
        health.components[ComponentType.APPROVAL_MANAGER] = self._check_approval_manager()
        health.components[ComponentType.STORAGE] = self._check_storage()

        # Determine overall status
        statuses = [comp.status for comp in health.components.values()]
        if HealthStatus.CRITICAL in statuses:
            health.status = HealthStatus.CRITICAL
        elif HealthStatus.WARNING in statuses:
            health.status = HealthStatus.WARNING
        elif HealthStatus.UNKNOWN in statuses:
            health.status = HealthStatus.UNKNOWN

        # Generate recommendations
        health.recommendations = self._generate_recommendations(health)

        return health

    def _check_orchestrator(self) -> ComponentHealth:
        """Check orchestrator health."""
        try:
            # Check if orchestrator process is running
            orchestrator_running = self._check_process_running("orchestrator_cloud")
            
            if not orchestrator_running:
                return ComponentHealth(
                    component=ComponentType.ORCHESTRATOR,
                    status=HealthStatus.WARNING,
                    message="Orchestrator process not detected",
                    metrics={"running": False}
                )

            # Check task queue depth (if accessible)
            queue_depth = 0  # Would check actual queue in production

            return ComponentHealth(
                component=ComponentType.ORCHESTRATOR,
                status=HealthStatus.HEALTHY,
                message="Orchestrator operating normally",
                metrics={
                    "running": True,
                    "queue_depth": queue_depth,
                }
            )

        except Exception as e:
            return ComponentHealth(
                component=ComponentType.ORCHESTRATOR,
                status=HealthStatus.CRITICAL,
                message=f"Error checking orchestrator: {e}",
                metrics={"error": str(e)}
            )

    def _check_draft_generator(self) -> ComponentHealth:
        """Check draft generator health."""
        try:
            # Count recent drafts
            draft_count = self._count_files(DRAFTS_DIR)
            recent_drafts = self._count_recent_files(DRAFTS_DIR, minutes=60)

            metrics = {
                "total_drafts": draft_count,
                "recent_drafts_1h": recent_drafts,
            }

            # Check for concerning patterns
            if recent_drafts > 100:
                return ComponentHealth(
                    component=ComponentType.DRAFT_GENERATOR,
                    status=HealthStatus.WARNING,
                    message=f"High draft generation rate: {recent_drafts}/hour",
                    metrics=metrics
                )

            return ComponentHealth(
                component=ComponentType.DRAFT_GENERATOR,
                status=HealthStatus.HEALTHY,
                message=f"Draft generator healthy ({draft_count} total drafts)",
                metrics=metrics
            )

        except Exception as e:
            return ComponentHealth(
                component=ComponentType.DRAFT_GENERATOR,
                status=HealthStatus.CRITICAL,
                message=f"Error checking draft generator: {e}",
                metrics={"error": str(e)}
            )

    def _check_approval_manager(self) -> ComponentHealth:
        """Check approval manager health."""
        try:
            # Count pending approvals
            approval_count = self._count_files(APPROVAL_REQUESTS_DIR)
            pending_count = self._count_pending_approvals()

            metrics = {
                "total_approvals": approval_count,
                "pending_approvals": pending_count,
            }

            # Check for backlog
            if pending_count > ALERT_THRESHOLD_APPROVALS:
                return ComponentHealth(
                    component=ComponentType.APPROVAL_MANAGER,
                    status=HealthStatus.WARNING,
                    message=f"Approval backlog: {pending_count} pending",
                    metrics=metrics
                )

            return ComponentHealth(
                component=ComponentType.APPROVAL_MANAGER,
                status=HealthStatus.HEALTHY,
                message=f"Approval manager healthy ({pending_count} pending)",
                metrics=metrics
            )

        except Exception as e:
            return ComponentHealth(
                component=ComponentType.APPROVAL_MANAGER,
                status=HealthStatus.CRITICAL,
                message=f"Error checking approval manager: {e}",
                metrics={"error": str(e)}
            )

    def _check_storage(self) -> ComponentHealth:
        """Check storage health."""
        try:
            # Check disk usage
            disk_usage = psutil.disk_usage(str(BASE_DIR))
            usage_percent = disk_usage.percent

            metrics = {
                "total_gb": round(disk_usage.total / (1024**3), 2),
                "used_gb": round(disk_usage.used / (1024**3), 2),
                "free_gb": round(disk_usage.free / (1024**3), 2),
                "usage_percent": usage_percent,
            }

            if usage_percent > 90:
                return ComponentHealth(
                    component=ComponentType.STORAGE,
                    status=HealthStatus.CRITICAL,
                    message=f"Critical: Disk usage at {usage_percent}%",
                    metrics=metrics
                )
            elif usage_percent > 75:
                return ComponentHealth(
                    component=ComponentType.STORAGE,
                    status=HealthStatus.WARNING,
                    message=f"Warning: Disk usage at {usage_percent}%",
                    metrics=metrics
                )

            return ComponentHealth(
                component=ComponentType.STORAGE,
                status=HealthStatus.HEALTHY,
                message=f"Storage healthy ({usage_percent}% used)",
                metrics=metrics
            )

        except Exception as e:
            return ComponentHealth(
                component=ComponentType.STORAGE,
                status=HealthStatus.CRITICAL,
                message=f"Error checking storage: {e}",
                metrics={"error": str(e)}
            )

    def _check_alerts(self, health: SystemHealth) -> None:
        """Check for and record alerts."""
        for component, comp_health in health.components.items():
            if comp_health.status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
                alert = {
                    "timestamp": datetime.now().isoformat(),
                    "component": component.value,
                    "status": comp_health.status.value,
                    "message": comp_health.message,
                }
                self.alerts.append(alert)
                logger.warning(f"ALERT [{comp_health.status.value}]: {comp_health.message}")

        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]

    def _log_health_status(self, health: SystemHealth) -> None:
        """Log current health status."""
        status_emoji = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.WARNING: "⚠️",
            HealthStatus.CRITICAL: "❌",
            HealthStatus.UNKNOWN: "❓",
        }
        emoji = status_emoji.get(health.status, "❓")
        logger.info(f"{emoji} System Health: {health.status.value}")

    def _generate_recommendations(self, health: SystemHealth) -> List[str]:
        """Generate recommendations based on health status."""
        recommendations = []

        for component, comp_health in health.components.items():
            if comp_health.status == HealthStatus.CRITICAL:
                recommendations.append(f"URGENT: Address {component.value} issue - {comp_health.message}")
            elif comp_health.status == HealthStatus.WARNING:
                recommendations.append(f"Review {component.value}: {comp_health.message}")

        # Check for patterns
        pending_approvals = health.components.get(ComponentType.APPROVAL_MANAGER)
        if pending_approvals and pending_approvals.metrics.get("pending_approvals", 0) > 20:
            recommendations.append("Consider increasing approval review frequency")

        return recommendations

    def _check_process_running(self, process_name: str) -> bool:
        """Check if a process is running."""
        try:
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info.get('cmdline', []) or [])
                    if process_name in cmdline:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return False
        except Exception:
            return False

    def _count_files(self, directory: Path) -> int:
        """Count files in a directory."""
        if not directory.exists():
            return 0
        return len([f for f in directory.iterdir() if f.is_file()])

    def _count_recent_files(self, directory: Path, minutes: int = 60) -> int:
        """Count files created in the last N minutes."""
        if not directory.exists():
            return 0
        
        cutoff = datetime.now() - timedelta(minutes=minutes)
        count = 0
        
        for f in directory.iterdir():
            if f.is_file():
                try:
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    if mtime > cutoff:
                        count += 1
                except Exception:
                    continue
        
        return count

    def _count_pending_approvals(self) -> int:
        """Count pending approval requests."""
        if not APPROVAL_REQUESTS_DIR.exists():
            return 0
        
        count = 0
        for f in APPROVAL_REQUESTS_DIR.iterdir():
            if f.is_file() and f.suffix == '.md':
                try:
                    with open(f, 'r', encoding='utf-8') as file:
                        content = file.read()
                        if "Response: [PENDING]" in content:
                            count += 1
                except Exception:
                    continue
        
        return count

    def get_current_health(self) -> Optional[SystemHealth]:
        """Get the latest health check result."""
        with self.lock:
            return self.last_health

    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of current health."""
        health = self.get_current_health()
        if not health:
            return {"status": "UNKNOWN", "message": "No health data available"}

        return {
            "status": health.status.value,
            "timestamp": health.timestamp.isoformat(),
            "components": {
                comp.value: {
                    "status": ch.status.value,
                    "message": ch.message,
                }
                for comp, ch in health.components.items()
            },
            "alerts_count": len(self.alerts),
            "recommendations": health.recommendations,
        }

    def generate_report(self) -> Path:
        """Generate a detailed health report."""
        health = self.get_current_health()
        if not health:
            raise ValueError("No health data available")

        report_file = HEALTH_REPORTS_DIR / f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

        content = f"""# Cloud Runtime Health Report

**Generated:** {health.timestamp.isoformat()}
**Overall Status:** {health.status.value}

---

## Component Status

| Component | Status | Message |
|-----------|--------|---------|
"""
        for comp, comp_health in health.components.items():
            content += f"| {comp.value} | {comp_health.status.value} | {comp_health.message} |\n"

        content += """
---

## Metrics

"""
        for comp, comp_health in health.components.items():
            if comp_health.metrics:
                content += f"### {comp.value}\n"
                for key, value in comp_health.metrics.items():
                    content += f"- {key}: {value}\n"
                content += "\n"

        if health.alerts:
            content += """---

## Recent Alerts

"""
            for alert in self.alerts[-10:]:  # Last 10 alerts
                content += f"- [{alert['timestamp']}] {alert['status']}: {alert['message']}\n"

        if health.recommendations:
            content += """---

## Recommendations

"""
            for rec in health.recommendations:
                content += f"- {rec}\n"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Health report generated: {report_file}")
        return report_file


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for health monitor."""
    print("=" * 60)
    print("AI Employee - PLATINUM Tier Cloud Health Monitor")
    print("=" * 60)
    print()

    monitor = CloudHealthMonitor()
    
    try:
        monitor.start()
        logger.info("Health Monitor running. Press Ctrl+C to stop.")
        
        # Keep main thread alive and show periodic status
        while True:
            time.sleep(60)
            summary = monitor.get_health_summary()
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Health: {summary.get('status', 'UNKNOWN')}")
            
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    finally:
        monitor.stop()
        
        # Generate final report
        try:
            report_path = monitor.generate_report()
            print(f"\nFinal health report: {report_path}")
        except Exception as e:
            print(f"\nCould not generate final report: {e}")
        
        print("\nHealth Monitor stopped.")


if __name__ == "__main__":
    main()
