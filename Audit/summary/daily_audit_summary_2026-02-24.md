# Daily Audit Summary

**Date:** 2026-02-24
**Generated:** 2026-02-24 23:00:00
**Session:** session_20260224_100000

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Task Events | 5 |
| Agent Decisions | 5 |
| MCP Calls | 5 |
| Failures | 4 |
| Retries | 6 |

---

## Task Lifecycle

- **task_created:** 1
- **task_detected:** 1
- **task_classified:** 1
- **task_started:** 1
- **task_completed:** 1

---

## Agent Decisions

- **skill_selection:** 2
- **domain_routing:** 1
- **approval_required:** 1
- **fallback_used:** 1

---

## MCP Calls

- **Successful:** 4
- **Errors:** 1

---

## Failures

- **Warnings:** 1
- **Errors:** 2
- **Critical:** 1

---

## Retries

- **Successful:** 1
- **Failed:** 3
- **Pending:** 2

---

## System Metrics

| Metric | Value |
|--------|-------|
| Events Received | 25 |
| Events Written | 25 |
| Failures Logged | 4 |
| MCP Calls Logged | 5 |
| Retries Logged | 6 |

---

## Notable Events

### Critical Failures
1. **email_agent** - SMTP authentication failed (10:01:00)

### MCP Errors
1. **accounting_mcp** - invoice/create timeout (10:00:25)

### Successful Recoveries
1. **social_media_agent** - Rate limit retry succeeded (10:02:10)

---

## Recommendations

1. **Review SMTP credentials** for email_agent - critical authentication failure
2. **Check accounting_mcp server** - connection timeouts occurring
3. **Monitor rate limits** - social media hitting API limits

---

*Generated automatically by AI Employee Audit Agent*
