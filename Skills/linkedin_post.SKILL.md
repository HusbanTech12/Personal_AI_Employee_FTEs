# Skill: LinkedIn Post

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `linkedin_post` |
| **Tier** | Gold |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Marketing & Social Media |
| **API** | LinkedIn UGC Posts API v2 |

---

## Purpose

Publish business content automatically on LinkedIn. Generates professional posts, publishes via LinkedIn API, and stores engagement summaries.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  LinkedIn       │ ──→ │  Content         │ ──→ │  LinkedIn       │
│  Agent          │     │  Generator       │     │  API            │
│                 │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
       │                        │                        │
       ▼                        ▼                        ▼
  Reads task              Formats post            POST /ugcPosts
  from Needs_Action       + hashtags              Bearer Token Auth
```

---

## Accepted Inputs

| Input Type | Description | Examples |
|------------|-------------|----------|
| **Business Post** | Company announcements, product launches | "Announce Q4 results", "New feature launch" |
| **Thought Leadership** | Industry insights, opinions | "AI trends 2026", "Remote work insights" |
| **Engagement Post** | Polls, questions, discussions | "What's your biggest challenge?" |
| **Educational Content** | How-to guides, tips | "5 tips for productivity" |

**Task Format:**
```markdown
---
title: LinkedIn Post
status: needs_action
priority: standard
skill: linkedin_post
topic: Product Launch
audience: Business professionals
tone: professional
---

## Content Brief

Announce our new AI Employee Gold Tier with multi-agent system.
Key features to highlight: autonomous agents, retry logic, analytics.
```

---

## LinkedIn API Integration

### Endpoint

```
POST https://api.linkedin.com/v2/ugcPosts
```

### Headers

```json
{
  "Authorization": "Bearer {ACCESS_TOKEN}",
  "Content-Type": "application/json",
  "X-Restli-Protocol-Version": "2.0.0"
}
```

### Request Body

```json
{
  "author": "urn:li:organization:{ORG_ID}",
  "lifecycleState": "PUBLISHED",
  "specificContent": {
    "com.linkedin.ugc.ShareContent": {
      "shareCommentary": {
        "text": "Post content with hashtags..."
      },
      "shareMediaCategory": "NONE"
    }
  },
  "visibility": {
    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
  }
}
```

### Response (Success - 201 Created)

```json
{
  "id": "urn:li:share:123456789"
}
```

---

## Execution Steps

### Step 1: Parse Marketing Task

```
Read task file from Needs_Action
↓
Extract frontmatter (topic, audience, tone, goal)
↓
Extract content brief from body
↓
Validate LinkedIn skill requirement
```

### Step 2: Generate Post Content

```
Select tone template (professional/conversational/enthusiastic/educational)
↓
Build hook/opening line
↓
Add value proposition
↓
Add call-to-action
↓
Suggest relevant hashtags (3-5)
```

### Step 3: Publish via API

```
Build UGC Post payload
↓
Set Authorization header with Bearer token
↓
POST to /v2/ugcPosts
↓
Receive post ID
↓
Build post URL
```

### Step 4: Store Engagement Summary

```
Create markdown file in Business/Marketing/linkedin_posts/
↓
Include post details, URL, content
↓
Add engagement metrics table
↓
Log publication timestamp
```

### Step 5: Update Task Status

```
Append Execution Result section to task
↓
Mark as completed
↓
Move to Done folder (by task executor)
```

---

## Content Templates

### Professional Tone

```
{Opening: "We're pleased to announce"}

{Value proposition or news}

{Call-to-action: "Learn more about our solution."}

{#Hashtag1} {#Hashtag2} {#Hashtag3}
```

### Conversational Tone

```
{Opening: "Hey everyone! Great news to share"}

{Casual update or insight}

{Call-to-action: "What do you think? Drop a comment!"}

{#Hashtag1} {#Hashtag2} {#Hashtag3}
```

### Enthusiastic Tone

```
🚀 {Opening: "Big news!"}

{Exciting announcement}

{Call-to-action: "This is just the beginning!"}

{#Hashtag1} {#Hashtag2} {#Hashtag3}
```

### Educational Tone

```
{Opening: "Here's something valuable to know"}

{Educational content or tips}

{Call-to-action: "Save this for later reference."}

{#Hashtag1} {#Hashtag2} {#Hashtag3}
```

---

## Hashtag Suggestions

| Topic | Suggested Hashtags |
|-------|-------------------|
| Product | #ProductLaunch #Innovation #Technology #NewProduct |
| Business | #Business #Leadership #Strategy #Growth |
| AI/Tech | #AI #ArtificialIntelligence #Automation #MachineLearning |
| Marketing | #Marketing #DigitalMarketing #ContentMarketing #SocialMedia |
| Career | #Career #ProfessionalDevelopment #Leadership #CareerAdvice |
| Company | #Company #TeamWork #Culture #WorkLife |

---

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LINKEDIN_ACCESS_TOKEN` | LinkedIn API access token | `AQ...` |
| `LINKEDIN_ORG_ID` | Organization ID | `12345678` |
| `LINKEDIN_AUTHOR_URN` | Author URN (optional) | `urn:li:organization:12345678` |

### Config File

Location: `Config/linkedin_config.json`

```json
{
  "access_token": "${LINKEDIN_ACCESS_TOKEN}",
  "org_id": "${LINKEDIN_ORG_ID}",
  "author_urn": "",
  "demo_mode": false,
  "max_retries": 3,
  "retry_delay_seconds": 30
}
```

---

## Output Format

### Engagement Summary File

Location: `Business/Marketing/linkedin_posts/linkedin_post_YYYYMMDD_HHMMSS.md`

```markdown
---
title: LinkedIn Post - {topic}
status: Published
post_id: {post_id}
post_url: {post_url}
published_at: {timestamp}
topic: {topic}
audience: {audience}
tone: {tone}
---

# LinkedIn Post Summary

## Publication Details

| Field | Value |
|-------|-------|
| **Post ID** | {post_id} |
| **URL** | {post_url} |
| **Published** | {timestamp} |
| **Topic** | {topic} |
| **Audience** | {audience} |
| **Tone** | {tone} |

---

## Post Content

{Full post text with hashtags}

---

## Hashtags

{#hashtag1} {#hashtag2} {#hashtag3}

---

## Engagement Summary

| Metric | Value |
|--------|-------|
| Impressions | 0 |
| Likes | 0 |
| Comments | 0 |
| Shares | 0 |

---

*Generated: {timestamp}*
```

---

## Completion Rules

A LinkedIn post task is **complete** when:

- [ ] **Content generated** - Post content formatted with tone
- [ ] **API responded** - HTTP 201 received from LinkedIn
- [ ] **Post published** - Post ID received
- [ ] **Summary saved** - Engagement summary in linkedin_posts/
- [ ] **Task updated** - Execution result appended to task file

---

## Error Handling

| Error | Handling |
|-------|----------|
| API not configured | Run in demo mode, log simulation |
| Invalid access token | Log error, retry up to 3 times |
| Rate limit exceeded | Wait retry_delay_seconds, retry |
| Network error | Add to retry queue |
| Max retries exceeded | Log failure, mark task as failed |

### Retry Logic

```
Post fails
↓
Add to retry queue with count=0
↓
Wait retry_delay_seconds (30s default)
↓
Increment count, retry
↓
If count >= max_retries: give up and log
```

---

## Demo Mode

When API credentials are not configured:

- Posts are simulated (not published)
- Demo post ID generated: `urn:li:share:{timestamp}`
- Demo URL created
- Engagement summary saved with demo_mode flag
- Safe for development and testing

---

## Security

### Credential Management

- Access tokens stored in **environment variables only**
- Config file uses placeholders or empty values
- Never commit real credentials to version control
- Tokens should have minimal required permissions

### API Permissions Required

- `w_member_social` - Post on behalf of user
- `w_organization_social` - Post on behalf of organization

---

## Examples

### Example 1: Product Launch

**Task:**
```markdown
---
title: LinkedIn Product Launch
skill: linkedin_post
topic: Product Launch
audience: Business professionals
tone: enthusiastic
---

## Content Brief

Announce Gold Tier AI Employee with multi-agent system.
Key features: 6 agents, automatic routing, retry logic.
```

**Generated Post:**
```
🚀 Big news!

Introducing Gold Tier AI Employee - our most advanced automation system!

✨ 6 specialized AI agents working concurrently
✨ Automatic task routing to the right skill
✨ Built-in retry logic for reliability
✨ Full execution history and analytics

This is just the beginning!

#AI #Automation #Productivity #Innovation #Tech
```

### Example 2: Thought Leadership

**Task:**
```markdown
---
title: AI Trends 2026
skill: linkedin_post
topic: AI Trends
audience: Tech leaders
tone: professional
---

## Content Brief

Share insights on multi-agent AI systems transforming business.
```

**Generated Post:**
```
We're excited to share insights on multi-agent AI systems.

Multi-agent architectures are transforming how businesses automate complex workflows.

Key trends for 2026:
- Autonomous agent collaboration
- Human-in-the-loop validation
- Cross-domain task routing

Learn more about our solution.

#AI #ArtificialIntelligence #Automation #Leadership #Technology
```

### Example 3: Educational Content

**Task:**
```markdown
---
title: Productivity Tips
skill: linkedin_post
topic: Productivity
audience: Professionals
tone: educational
---

## Content Brief

Share 5 tips for improving workplace productivity with AI.
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Posts not publishing | Verify LINKEDIN_ACCESS_TOKEN is valid |
| 401 Unauthorized | Check token expiration, refresh if needed |
| 403 Forbidden | Verify API permissions (w_organization_social) |
| Demo mode only | Set LINKEDIN_ACCESS_TOKEN and LINKEDIN_ORG_ID |
| Hashtags not showing | Ensure hashtags are at end of content |

---

## Related Files

| File | Purpose |
|------|---------|
| `Agents/linkedin_agent.py` | LinkedIn agent with API integration |
| `Skills/linkedin_post.SKILL.md` | This skill definition |
| `Config/linkedin_config.json` | LinkedIn configuration |
| `Business/Marketing/linkedin_posts/` | Published post summaries |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-25 | Initial implementation with direct LinkedIn API |

---

## References

- [LinkedIn UGC Posts API](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/ugc-posts-api)
- [LinkedIn API Documentation](https://learn.microsoft.com/en-us/linkedin/)
- [LinkedIn Authentication](https://learn.microsoft.com/en-us/linkedin/shared/authentication/authentication)
