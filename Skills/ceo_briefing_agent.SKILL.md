# CEO Briefing Agent Skill

## Purpose

Autonomous executive reporting agent that synthesizes multi-channel business data into comprehensive weekly CEO briefings with actionable insights, revenue analysis, and strategic recommendations.

---

## Weekly Analysis Scope

### Data Sources Analyzed

| Source | Data Type | Analysis Focus |
|--------|-----------|----------------|
| **Emails** | Inbox, Sent, Replies | Client communications, deals, issues |
| **WhatsApp** | Conversations, Leads | Customer sentiment, quick wins |
| **LinkedIn** | Posts, Engagement | Brand performance, reach |
| **Business Tasks** | Plans, Completions | Operational efficiency |
| **Accounting** | Invoices, Revenue | Financial health |

---

## Capabilities

### 1. Email Analysis

Analyze all email communications for:

- **Deal Indicators**: Pricing discussions, purchase intent, contract mentions
- **Client Sentiment**: Satisfaction levels, complaint patterns
- **Communication Volume**: Inbound/outbound trends
- **Response Times**: Team responsiveness metrics
- **Key Relationships**: VIP client interactions

**Metrics Extracted:**
```
- Total emails processed
- Sales-related emails
- Support issues raised
- Average response time
- Unresolved threads
```

### 2. WhatsApp Conversation Analysis

Process WhatsApp conversations for:

- **Lead Quality**: Hot/warm/cold lead distribution
- **Customer Issues**: Common problems, resolution rates
- **Conversion Signals**: Purchase intent messages
- **Response Performance**: Team response times
- **Sentiment Trends**: Positive/negative ratio

**Metrics Extracted:**
```
- Conversations analyzed
- Leads captured
- Issues resolved
- Escalation count
- Customer satisfaction indicators
```

### 3. LinkedIn Engagement Analysis

Evaluate LinkedIn marketing performance:

- **Post Performance**: Impressions, engagement rates
- **Audience Growth**: New followers, demographics
- **Content Effectiveness**: Top-performing post types
- **Lead Generation**: Inbound inquiries from posts
- **Brand Reach**: Share of voice, mentions

**Metrics Extracted:**
```
- Posts published
- Total impressions
- Engagement rate
- New followers
- Click-through rate
- Leads generated
```

### 4. Business Task Analysis

Review operational task completion:

- **Task Volume**: Created vs. completed
- **Completion Rates**: By category and agent
- **Bottlenecks**: Stuck or delayed tasks
- **Efficiency Metrics**: Average completion time
- **Backlog Status**: Pending task analysis

**Metrics Extracted:**
```
- Tasks created
- Tasks completed
- Completion rate %
- Average completion time
- Overdue tasks
```

### 5. Accounting Summary Analysis

Process financial data for:

- **Revenue Tracking**: Weekly revenue, trends
- **Invoice Status**: Paid, pending, overdue
- **Expense Overview**: Major expenditures
- **Cash Flow**: Inflow vs. outflow
- **Financial Risks**: Payment delays, outstanding receivables

**Metrics Extracted:**
```
- Total revenue
- Outstanding invoices
- Overdue payments
- Major expenses
- Cash flow status
```

---

## Report Generation

### Output Location

All reports generated to: `Reports/CEO_WEEKLY_REPORT.md`

### Report Schedule

```
Generation Day: Every Monday at 6:00 AM
Reporting Period: Previous week (Monday-Sunday)
Delivery: File + Email notification to CEO
```

---

## Report Template

```markdown
# CEO Weekly Briefing

## Executive Summary
| Week | <Date Range> |
|------|--------------|
| Generated | <Timestamp> |
| Status | 🟢 On Track / 🟡 Attention Needed / 🔴 At Risk |

### Key Highlights
- 🎯 Top achievement of the week
- 💰 Revenue milestone (if any)
- 📈 Growth metric highlight
- ⚠️ Critical issue (if any)

---

## Revenue Opportunities

### Pipeline Summary
| Stage | Count | Value |
|-------|-------|-------|
| Hot Leads | | $ |
| Warm Leads | | $ |
| Negotiations | | $ |
| Closing Soon | | $ |
| **Total Pipeline** | | **$** |

### This Week's Opportunities
1. **<Opportunity Name>**
   - Value: $<amount>
   - Probability: <high/medium/low>
   - Expected Close: <date>
   - Next Action: <action>

2. **<Opportunity Name>**
   ...

### Revenue Forecast
| Period | Projected | Confidence |
|--------|-----------|------------|
| This Week | $ | % |
| This Month | $ | % |
| This Quarter | $ | % |

---

## Leads Generated

### Lead Summary
| Channel | New Leads | Conversion Rate |
|---------|-----------|-----------------|
| Email | | % |
| WhatsApp | | % |
| LinkedIn | | % |
| **Total** | | **%** |

### Lead Quality Distribution
```
🔥 Hot Leads:    [====    ] <count> (<percent>%)
🟡 Warm Leads:   [======  ] <count> (<percent>%)
❄️ Cold Leads:   [==      ] <count> (<percent>%)
```

### Top Leads This Week
1. **<Lead Name>** - <Company>
   - Source: <channel>
   - Interest: <product/service>
   - Estimated Value: $<amount>
   - Priority: <high/medium/low>

---

## Channel Performance

### Email Communications
| Metric | This Week | Last Week | Change |
|--------|-----------|-----------|--------|
| Emails Processed | | | |
| Sales Inquiries | | | |
| Support Issues | | | |
| Avg Response Time | | | |

### WhatsApp Activity
| Metric | This Week | Last Week | Change |
|--------|-----------|-----------|--------|
| Conversations | | | |
| Leads Captured | | | |
| Issues Resolved | | | |
| Escalations | | | |

### LinkedIn Performance
| Metric | This Week | Last Week | Change |
|--------|-----------|-----------|--------|
| Posts Published | | | |
| Impressions | | | |
| Engagement Rate | | | |
| New Followers | | | |
| Clicks to Website | | | |

---

## Financial Summary

### Revenue Overview
| Metric | Amount | Status |
|--------|--------|--------|
| Weekly Revenue | $ | vs target |
| MTD Revenue | $ | vs target |
| QTD Revenue | $ | vs target |

### Invoice Status
| Status | Count | Total Value |
|--------|-------|-------------|
| Paid | | $ |
| Pending | | $ |
| Overdue (>30 days) | | $ |
| At Risk | | $ |

### Top Expenses
1. <Expense category>: $<amount>
2. <Expense category>: $<amount>
3. <Expense category>: $<amount>

### Cash Flow Health
```
Inflow:  $<amount> ████████████
Outflow: $<amount> ████████
Net:     $<amount> <positive/negative>
```

---

## Risks Detected

### Critical Risks 🔴
| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| <risk> | High/Med/Low | High/Med/Low | <action> |

### Warning Signs 🟡
- <warning 1>
- <warning 2>
- <warning 3>

### Operational Concerns
- <concern 1>
- <concern 2>

---

## Task & Operations Summary

### Task Completion
| Category | Completed | Pending | Overdue |
|----------|-----------|---------|---------|
| Sales | | | |
| Support | | | |
| Marketing | | | |
| Operations | | | |

### Agent Performance
| Agent | Tasks Done | Success Rate | Avg Time |
|-------|------------|--------------|----------|
| Gmail Agent | | % | |
| WhatsApp Agent | | % | |
| LinkedIn Agent | | % | |

### Bottlenecks Identified
1. <bottleneck 1>
2. <bottleneck 2>

---

## Recommendations

### Immediate Actions (This Week)
1. **<Priority Action 1>**
   - Reason: <why>
   - Expected Impact: <impact>
   - Owner: <who>

2. **<Priority Action 2>**
   ...

### Strategic Initiatives
1. **<Initiative 1>**
   - Timeline: <when>
   - Investment: $<amount>
   - ROI Potential: <estimate>

### Process Improvements
- <improvement 1>
- <improvement 2>

### Resource Needs
- <need 1>
- <need 2>

---

## Week Ahead Preview

### Key Dates
- <date>: <event/deadline>
- <date>: <event/deadline>

### Expected Deliverables
- <deliverable 1>
- <deliverable 2>

### Focus Areas
1. <focus area 1>
2. <focus area 2>
3. <focus area 3>

---

## Appendix

### Data Sources
- Emails analyzed: <count>
- WhatsApp conversations: <count>
- LinkedIn posts: <count>
- Tasks reviewed: <count>
- Invoices processed: <count>

### Report Metadata
- Generated by: CEO Briefing Agent v1.0
- Generation time: <duration>
- Next report: <date>

---
*Confidential - For CEO Eyes Only*
```

---

## Input Schema

```json
{
  "report_id": "string",
  "report_period": {
    "start_date": "ISO8601",
    "end_date": "ISO8601"
  },
  "data_sources": {
    "emails": {
      "total": "integer",
      "sales_related": "integer",
      "support_issues": "integer",
      "avg_response_time_minutes": "float"
    },
    "whatsapp": {
      "conversations": "integer",
      "leads_captured": "integer",
      "escalations": "integer"
    },
    "linkedin": {
      "posts": "integer",
      "impressions": "integer",
      "engagement_rate": "float",
      "new_followers": "integer"
    },
    "tasks": {
      "created": "integer",
      "completed": "integer",
      "overdue": "integer"
    },
    "accounting": {
      "revenue": "float",
      "invoices_paid": "integer",
      "invoices_pending": "integer",
      "invoices_overdue": "integer",
      "expenses": "float"
    }
  },
  "generated_at": "ISO8601"
}
```

---

## Analysis Algorithms

### Revenue Opportunity Scoring

```
Opportunity Score = (Lead Quality × 0.4) + (Engagement Level × 0.3) + (Timeline Urgency × 0.3)

Lead Quality:
- Hot: 100 points
- Warm: 60 points
- Cold: 20 points

Engagement Level:
- High (daily interaction): 100 points
- Medium (weekly interaction): 60 points
- Low (monthly interaction): 20 points

Timeline Urgency:
- This week: 100 points
- This month: 60 points
- This quarter: 30 points
```

### Risk Detection Rules

| Pattern | Risk Level | Action |
|---------|------------|--------|
| Overdue invoice >60 days | 🔴 Critical | Flag for immediate follow-up |
| Lead gone cold >14 days | 🟡 Warning | Schedule re-engagement |
| Support issue escalated 2+ times | 🟡 Warning | Review process |
| Revenue below target >2 weeks | 🔴 Critical | Executive review |
| Negative sentiment spike | 🟡 Warning | Investigate root cause |
| Task overdue >7 days | 🟡 Warning | Reassign or escalate |

### Sentiment Analysis

```
Positive Indicators:
- "thank", "great", "excellent", "happy", "satisfied"
- Emoji: 😊 👍 ✅ 🎉 ⭐

Negative Indicators:
- "issue", "problem", "disappointed", "frustrated", "unhappy"
- Emoji: 😞 👎 ❌ 🚫 ⚠️

Sentiment Score = (Positive - Negative) / Total Messages × 100
```

---

## Output Schema

```json
{
  "report_id": "CEO_WEEKLY_YYYY_WW",
  "period": {
    "start": "ISO8601",
    "end": "ISO8601"
  },
  "generated_at": "ISO8601",
  "executive_summary": {
    "status": "on_track|attention_needed|at_risk",
    "highlights": ["string"],
    "critical_issues": ["string"]
  },
  "revenue": {
    "weekly": "float",
    "pipeline_total": "float",
    "forecast_confidence": "float"
  },
  "leads": {
    "total_new": "integer",
    "hot": "integer",
    "warm": "integer",
    "cold": "integer"
  },
  "risks": [
    {
      "type": "critical|warning",
      "description": "string",
      "impact": "high|medium|low",
      "mitigation": "string"
    }
  ],
  "recommendations": [
    {
      "priority": "high|medium|low",
      "action": "string",
      "owner": "string",
      "deadline": "ISO8601"
    }
  ],
  "report_path": "Reports/CEO_WEEKLY_REPORT.md",
  "delivered": "boolean"
}
```

---

## Audit Log Format

All actions logged to `Logs/ceo_briefing.log`:

```
[TIMESTAMP] | ACTION | SOURCE | RECORDS | STATUS | NOTES
```

Example:
```
[2026-03-03T06:00:00Z] | GENERATE_START | weekly | - | success | Starting weekly report generation
[2026-03-03T06:00:15Z] | ANALYZE | emails | 247 | success | Processed 247 emails
[2026-03-03T06:00:30Z] | ANALYZE | whatsapp | 89 | success | Processed 89 conversations
[2026-03-03T06:00:45Z] | ANALYZE | linkedin | 12 | success | Processed 12 posts
[2026-03-03T06:01:00Z] | ANALYZE | accounting | 34 | success | Processed 34 transactions
[2026-03-03T06:02:00Z] | REPORT_GENERATED | CEO_WEEKLY_2026_09 | - | success | Report saved to Reports/
[2026-03-03T06:02:05Z] | NOTIFY | CEO | - | success | Notification sent
```

---

## Integration Points

### Required Connections

| System | Purpose | Method |
|--------|---------|--------|
| Gmail Agent | Email data extraction | File system / API |
| WhatsApp Agent | Conversation data | File system / API |
| LinkedIn Agent | Engagement metrics | File system / API |
| Task System | Task completion data | Plan files |
| Accounting System | Financial data | API / File import |
| Email Server | Report delivery | SMTP / MCP |

### File Locations

```
Skills/ceo_briefing_agent.SKILL.md       ← This file
Reports/CEO_WEEKLY_REPORT.md             ← Weekly report output
Reports/Archive/                         ← Historical reports
Vault/Analytics/                         │ Intermediate analysis data
Logs/ceo_briefing.log                    ← Agent audit trail
```

---

## Error Handling

| Error Type | Response |
|------------|----------|
| Data source unavailable | Use cached data, flag in report |
| Accounting data missing | Generate partial report, notify admin |
| Report generation failure | Retry 3x, escalate to admin |
| Email delivery failure | Save report, notify via alternative channel |
| Analysis timeout | Use partial analysis, extend timeout next run |

---

## Performance Metrics

| Metric | Target |
|--------|--------|
| Report Generation Time | <5 minutes |
| Data Accuracy | ≥98% |
| Report Completeness | 100% (all sections) |
| Delivery Reliability | ≥99% |
| Insight Actionability | ≥80% (CEO feedback) |

---

## Configuration

```json
{
  "generation_enabled": true,
  "generation_day": "Monday",
  "generation_time": "06:00",
  "timezone": "UTC",
  "report_recipients": ["ceo @company.com"],
  "data_retention_weeks": 52,
  "include_appendix": true,
  "include_recommendations": true,
  "risk_threshold_critical": 3,
  "risk_threshold_warning": 5,
  "log_path": "Logs/ceo_briefing.log",
  "report_path": "Reports/CEO_WEEKLY_REPORT.md",
  "archive_path": "Reports/Archive"
}
```

---

## Security & Confidentiality

### Access Control
- Reports marked **Confidential - For CEO Eyes Only**
- Store in protected `Reports/` directory
- Encrypt sensitive financial data
- Audit all report access

### Data Handling
- Anonymize customer data in examples
- Aggregate sensitive metrics
- Secure deletion of temporary analysis files
- Comply with data retention policies

---

## Customization Options

### Report Sections (Toggle)
```json
{
  "include_revenue": true,
  "include_leads": true,
  "include_channel_performance": true,
  "include_financial_summary": true,
  "include_risks": true,
  "include_recommendations": true,
  "include_task_summary": true,
  "include_week_ahead": true
}
```

### Executive Summary Style
- **Brief**: 3-5 bullet points
- **Standard**: Full template (default)
- **Detailed**: Extended analysis with charts

---

*Skill Version: 1.0.0*  
*Last Updated: 2026-02-28*  
*Tier: GOLD*
