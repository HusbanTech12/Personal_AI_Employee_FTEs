# Skill: System Resilience

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `system_resilience` |
| **Tier** | Gold+ |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | System Reliability |
| **Pattern** | Detect → Retry → Fallback → Log |

---

## Purpose

Ensure system never crashes by implementing comprehensive fault tolerance. This skill:

1. **Detects** agent failures automatically
2. **Retries** failed executions with backoff
3. **Switches** to fallback skills when primary fails
4. **Logs** degraded mode operations
5. **Recovers** system to healthy state

---

## Core Principle

> **The system must never crash.**

All failures are handled gracefully with fallbacks and recovery.

---

## Failure Detection

| Detection Method | Description |
|-----------------|-------------|
| **Heartbeat Monitor** | Agents ping every N seconds |
| **Timeout Detection** | Operations exceeding timeout |
| **Error Pattern** | Repeated error signatures |
| **State Staleness** | No state updates for N minutes |
| **Health Check** | Periodic health endpoint checks |

---

## Retry Strategy

### Exponential Backoff with Jitter

```
Attempt 1: Immediate
Attempt 2: 5s + random(0-2s)
Attempt 3: 10s + random(0-4s)
Attempt 4: 20s + random(0-8s)
Attempt 5: 40s + random(0-16s)
```

### Retry Limits

| Priority | Max Retries | Timeout |
|----------|-------------|---------|
| Critical | 5 | 300s |
| High | 3 | 180s |
| Normal | 3 | 120s |
| Low | 1 | 60s |

---

## Fallback Skills

| Primary Skill | Fallback Skill | Degradation |
|--------------|----------------|-------------|
| `email` | `log_only` | Queue for later |
| `linkedin_marketing` | `content_generate` | Skip publish |
| `odoo_accounting` | `local_record` | Local JSON storage |
| `social_media` | `draft_only` | Save as draft |
| `automation_mcp` | `manual_queue` | Queue for manual |

---

## Degraded Mode Levels

| Level | Description | Actions |
|-------|-------------|---------|
| **Healthy** | All systems operational | Full operation |
| **Degraded-1** | One non-critical service down | Retry + fallback |
| **Degraded-2** | Multiple services down | Queue non-critical |
| **Degraded-3** | Critical service down | Minimal operation |
| **Recovery** | Services restoring | Gradual restoration |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial resilience skill |
