# AI Employee Schedule Configuration

## Overview

This file defines all scheduled tasks for the AI Employee system.
The scheduler_agent.py reads this configuration and triggers tasks automatically.

---

## Schedule Format

```yaml
task_name:
  schedule: "CRON_EXPRESSION or INTERVAL"
  type: "cron|interval"
  action: "action_type"
  enabled: true|false
  last_run: "YYYY-MM-DD HH:MM:SS"
  next_run: "YYYY-MM-DD HH:MM:SS"
```

---

## Scheduled Tasks

### Daily Tasks

```yaml
daily_linkedin_post:
  schedule: "0 9 * * *"  # Every day at 9:00 AM
  type: "cron"
  action: "linkedin_post"
  enabled: true
  description: "Publish daily LinkedIn business post"
  task_template: "linkedin_daily.md"
  
daily_inbox_scan:
  schedule: "0 */2 * * *"  # Every 2 hours
  type: "cron"
  action: "inbox_scan"
  enabled: true
  description: "Scan inbox for new files"

daily_digest:
  schedule: "0 17 * * *"  # Every day at 5:00 PM
  type: "cron"
  action: "generate_digest"
  enabled: true
  description: "Generate daily activity digest"
```

### Weekly Tasks

```yaml
weekly_report:
  schedule: "0 9 * * 1"  # Every Monday at 9:00 AM
  type: "cron"
  action: "weekly_report"
  enabled: true
  description: "Generate weekly activity report"
  
weekly_cleanup:
  schedule: "0 2 * * 0"  # Every Sunday at 2:00 AM
  type: "cron"
  action: "cleanup_logs"
  enabled: true
  description: "Archive old log files"
```

### Monthly Tasks

```yaml
monthly_analytics:
  schedule: "0 9 1 * *"  # First day of month at 9:00 AM
  type: "cron"
  action: "monthly_analytics"
  enabled: true
  description: "Generate monthly analytics report"
```

### Interval Tasks (relative timing)

```yaml
health_check:
  schedule: "300"  # Every 300 seconds (5 minutes)
  type: "interval"
  action: "health_check"
  enabled: true
  description: "Check system health"

queue_processor:
  schedule: "60"  # Every 60 seconds
  type: "interval"
  action: "process_queue"
  enabled: true
  description: "Process task queue"
```

---

## Cron Expression Format

```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday = 0)
│ │ │ │ │
* * * * *
```

### Examples

| Expression | Description |
|------------|-------------|
| `0 * * * *` | Every hour at minute 0 |
| `0 9 * * *` | Every day at 9:00 AM |
| `0 9 * * 1` | Every Monday at 9:00 AM |
| `0 9 1 * *` | First day of month at 9:00 AM |
| `*/15 * * * *` | Every 15 minutes |
| `0 9-17 * * *` | Every hour from 9 AM to 5 PM |
| `0 9 * * 1-5` | 9:00 AM on weekdays |

---

## Action Types

| Action | Description | Handler |
|--------|-------------|---------|
| `linkedin_post` | Trigger LinkedIn post | linkedin_agent.py |
| `email_digest` | Send email digest | email_agent.py |
| `inbox_scan` | Scan inbox folder | filesystem_watcher.py |
| `weekly_report` | Generate weekly report | report_generator.py |
| `cleanup_logs` | Archive old logs | cleanup_agent.py |
| `monthly_analytics` | Generate analytics | analytics_agent.py |
| `health_check` | System health check | health_agent.py |
| `process_queue` | Process task queue | task_executor.py |
| `custom` | Custom script | Specify in task_file |

---

## Timezone Configuration

```yaml
# Global timezone setting
timezone: "America/New_York"  # Default: UTC
```

---

## Holiday/Exception Dates

```yaml
exceptions:
  - date: "2026-12-25"
    action: "skip_all"
    reason: "Christmas Day"
  - date: "2026-01-01"
    action: "skip_all"
    reason: "New Year's Day"
  - date: "2026-07-04"
    action: "skip_all"
    reason: "Independence Day"
```

---

## Notification Settings

```yaml
notifications:
  on_success: false  # Don't notify on successful runs
  on_failure: true   # Notify on failed runs
  on_skip: false     # Don't notify on skipped runs
  channel: "log"     # log|email|slack
```

---

## Task Templates

### LinkedIn Daily Post Template

```markdown
---
title: Daily LinkedIn Post - {{date}}
status: needs_action
skill: linkedin_marketing
topic: Daily Business Update
audience: Business professionals
---

## Content Brief

Share daily insights about {{topic}}.

Key points:
- Industry update
- Company news
- Thought leadership
```

### Weekly Report Template

```markdown
---
title: Weekly Report - Week {{week_number}}
status: needs_action
skill: documentation
---

## Weekly Summary

### Tasks Completed
- Count: {{completed_count}}

### Tasks Pending
- Count: {{pending_count}}

### Key Achievements
- Achievement 1
- Achievement 2

### Next Week Goals
- Goal 1
- Goal 2
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-23 | Initial schedule configuration |
