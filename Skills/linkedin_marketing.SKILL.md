# Skill: LinkedIn Marketing

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `linkedin_marketing` |
| **Tier** | Silver |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Marketing & Social Media |
| **MCP Server** | `linkedin_mcp_server.py` |

---

## Purpose

Generate and publish LinkedIn business posts on behalf of the AI Employee system. All LinkedIn operations are routed through the **LinkedIn MCP Server** for centralized management and analytics tracking.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ LinkedIn Agent  │ ──→ │  LinkedIn MCP    │ ──→ │  LinkedIn API   │
│ (AI Agent)      │     │  Server          │     │  or Simulator   │
│                 │     │  (HTTP API)      │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
       │                        │
       ▼                        ▼
  Generates post          Publishes & tracks
  content                 engagement metrics
```

---

## Accepted Inputs

| Input Type | Description | Examples |
|------------|-------------|----------|
| **Business Post** | Create LinkedIn business update | Product launch, company news, thought leadership |
| **Engagement Post** | Generate engagement content | Polls, questions, industry insights |
| **Campaign Post** | Multi-post campaign content | Product series, event promotion |

**Task Format:**
```markdown
---
title: LinkedIn Post
status: needs_action
priority: standard
skill: linkedin_marketing
---

## Post Details

**Topic:** Product Launch
**Audience:** Business professionals
**Goal:** Generate awareness

## Content Brief

Announce our new AI Employee Gold Tier...
```

---

## MCP Server API

### Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `LINKEDIN_MCP_HOST` | Server bind address | `127.0.0.1` |
| `LINKEDIN_MCP_PORT` | Server port | `8766` |
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn API token | - |
| `LINKEDIN_ORG_ID` | Organization ID | - |

### Endpoints

#### POST /publish

Publish a LinkedIn post.

**Request:**
```json
{
  "content": {
    "text": "Post content here..."
  },
  "visibility": "PUBLIC",
  "post_type": "business",
  "campaign_id": "optional_campaign",
  "agent_id": "linkedin_agent"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Post published successfully",
  "post_id": "urn:li:share:123456789",
  "post_url": "https://linkedin.com/feed/update/...",
  "timestamp": "2026-02-23T15:30:00",
  "demo_mode": true
}
```

#### POST /generate

Generate post content using AI.

**Request:**
```json
{
  "topic": "Product Launch",
  "audience": "Business professionals",
  "goal": "Generate awareness",
  "key_points": ["Feature 1", "Feature 2", "Feature 3"],
  "tone": "professional"
}
```

**Response:**
```json
{
  "success": true,
  "generated_content": {
    "text": "🚀 Exciting news! We're thrilled to announce...",
    "hashtags": ["#AI", "#Automation", "#Productivity"],
    "character_count": 280
  },
  "engagement_prediction": "high"
}
```

#### GET /analytics/:post_id

Get engagement analytics for a post.

**Response:**
```json
{
  "post_id": "urn:li:share:123456789",
  "impressions": 1500,
  "likes": 45,
  "comments": 12,
  "shares": 8,
  "clicks": 67,
  "engagement_rate": 4.3,
  "timestamp": "2026-02-23T18:00:00"
}
```

#### GET /analytics/summary

Get summary of all recent posts.

**Response:**
```json
{
  "period": "last_7_days",
  "total_posts": 5,
  "total_impressions": 12500,
  "total_engagement": 450,
  "average_engagement_rate": 3.6,
  "top_performing_post": {
    "post_id": "urn:li:share:123456789",
    "engagement_rate": 5.2
  }
}
```

#### GET /status

Get server status.

**Response:**
```json
{
  "status": "running",
  "host": "127.0.0.1",
  "port": 8766,
  "api_configured": true,
  "demo_mode": true,
  "posts_published": 15,
  "timestamp": "2026-02-23T15:30:00"
}
```

---

## Execution Steps

### Step 1: Parse Business Task

```
Read task file
↓
Extract topic, audience, goal
↓
Identify key points
↓
Determine post type
```

### Step 2: Generate Post Content

```
Call MCP /generate endpoint
↓
Receive AI-generated content
↓
Review and refine if needed
↓
Add relevant hashtags
```

### Step 3: Publish Post

```
Call MCP /publish endpoint
↓
Include generated content
↓
Set visibility (PUBLIC/CONNECTIONS)
↓
Receive post ID and URL
```

### Step 4: Log Activity

```
Record post published
↓
Save engagement summary
↓
Update activity log
↓
Update Dashboard metrics
```

### Step 5: Track Engagement

```
Periodically call /analytics/:post_id
↓
Update engagement summary
↓
Report performance metrics
```

---

## Output Format

### Post Content Structure

```markdown
## LinkedIn Post Published

**Topic:** {topic}
**Published:** {timestamp}
**Post ID:** {post_id}
**URL:** {post_url}

### Content

{post_text}

### Hashtags

{#hashtag1} {#hashtag2} {#hashtag3}

### Engagement Summary

| Metric | Value |
|--------|-------|
| Impressions | 1,500 |
| Likes | 45 |
| Comments | 12 |
| Shares | 8 |
| Engagement Rate | 4.3% |
```

---

## Completion Rules

A LinkedIn marketing task is **complete** when:

- [ ] **Content generated** - Post content created
- [ ] **MCP server responded** - HTTP 200 received
- [ ] **Post published** - Post ID received
- [ ] **Logged** - Activity and marketing logs updated
- [ ] **Summary saved** - Engagement summary stored

---

## Content Guidelines

### Post Structure

1. **Hook** (first 1-2 lines) - Grab attention
2. **Value** - Share insight, news, or benefit
3. **Call-to-action** - Encourage engagement
4. **Hashtags** - 3-5 relevant tags

### Tone Options

| Tone | Description | Use Case |
|------|-------------|----------|
| Professional | Formal, business-appropriate | Company announcements |
| Conversational | Friendly, approachable | Thought leadership |
| Enthusiastic | Energetic, exciting | Product launches |
| Educational | Informative, helpful | How-to content |

### Character Limits

| Type | Limit | Recommendation |
|------|-------|----------------|
| Post text | 3,000 | 150-300 for best engagement |
| Headline | 150 | Keep under 100 |
| Hashtags | 3-5 | Most relevant first |

---

## Error Handling

| Error | Handling |
|-------|----------|
| MCP server not running | Start server, retry |
| API not configured | Log warning, use demo mode |
| Content generation failed | Retry with simplified prompt |
| Publish failed | Save content for manual review |
| Rate limit exceeded | Queue for later, retry after delay |

---

## Security

### Credential Management

- LinkedIn API tokens stored in **environment variables only**
- Never exposed to agents directly
- MCP server runs on localhost (127.0.0.1)
- OAuth tokens refreshed automatically

### Demo Mode

If API is not configured, server runs in **demo mode**:
- Posts are logged but not published
- Response includes `"demo_mode": true`
- Safe for testing without credentials

---

## Examples

### Example 1: Product Launch Post

**Task:**
```markdown
---
title: LinkedIn Product Launch
skill: linkedin_marketing
topic: Product Launch
audience: Business professionals
---

## Content Brief

Announce Gold Tier AI Employee with multi-agent system.
Key features: 6 agents, automatic routing, retry logic.
```

**Generated Post:**
```
🚀 Exciting News! Introducing Gold Tier AI Employee!

We're thrilled to announce our most advanced automation system yet:

✨ 6 specialized AI agents working concurrently
✨ Automatic task routing to the right skill
✨ Built-in retry logic for reliability
✨ Full execution history and analytics

Transform your workflow with autonomous multi-agent AI.

Learn more: [link]

#AI #Automation #Productivity #Innovation #GoldTier
```

### Example 2: Thought Leadership Post

**Task:**
```markdown
---
title: Industry Insights
skill: linkedin_marketing
topic: AI Trends 2026
audience: Tech leaders
tone: professional
---

Share insights on multi-agent AI systems.
```

### Example 3: Engagement Post (Poll)

**Task:**
```markdown
---
title: Team Poll
skill: linkedin_marketing
topic: Remote Work
type: poll
---

Create poll about remote work preferences.
```

---

## Integration with Other Skills

| Scenario | Handoff To | Information Passed |
|----------|------------|-------------------|
| Post needs research | `research` | Topic research, trends |
| Post is announcement | `documentation` | Press release content |
| Post requires graphics | External tool | Image generation request |

---

## Logs and Analytics

### Marketing Log Location

All LinkedIn marketing activity is saved to:
```
/Logs/Marketing/linkedin_YYYY-MM-DD.md
```

### Summary Contents

- Posts published
- Engagement metrics
- Top performing content
- Hashtag performance
- Audience insights

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Server won't start | Check port 8766 is available |
| Posts not publishing | Verify LinkedIn API credentials |
| Content too generic | Add more specific key points |
| Low engagement | Review posting time, hashtags |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-23 | Initial implementation with MCP server |
