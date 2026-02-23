# Skill: Social Media Marketing

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `social_media_marketing` |
| **Tier** | Gold |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Business - Marketing |
| **Platforms** | Facebook, Instagram, Twitter (X) |
| **MCP Server** | `social_mcp_server.py` |

---

## Purpose

Manage social media marketing across multiple platforms. This skill:

1. **Generates** platform-optimized post content
2. **Publishes** via Social MCP server
3. **Fetches** engagement metrics from all platforms
4. **Generates** daily/weekly marketing summaries
5. **Maintains** content calendar

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Social Media    │ ──→ │  Social MCP      │ ──→ │  Platform APIs  │
│ Agent           │     │  Server (8768)   │     │  or Simulator   │
│                 │     │                  │     │                 │
└─────────────────┘     └──────────────────┘     └─────────────────┘
         │                                              │
         │                                              ▼
         │                                    ┌─────────────────┐
         │                                    │ - Facebook      │
         │                                    │ - Instagram     │
         │                                    │ - Twitter (X)   │
         │                                    └─────────────────┘
         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Business/Marketing/                                             │
│  └── daily_social_summary.md                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Supported Platforms

| Platform | Post Types | Max Length | Hashtags | Media |
|----------|------------|------------|----------|-------|
| **Facebook** | Text, Image, Video, Link | 63,206 chars | 5-10 recommended | Yes |
| **Instagram** | Image, Video, Reel, Story | 2,200 chars | 10-30 recommended | Required |
| **Twitter (X)** | Tweet, Thread | 280 chars (4000 Premium) | 2-3 recommended | Yes |

---

## Accepted Inputs

| Input Type | Description | Examples |
|------------|-------------|----------|
| **Generate Post** | Create platform-optimized content | "Generate Facebook post about product launch" |
| **Publish Post** | Publish to one or multiple platforms | "Publish to Facebook and Instagram" |
| **Fetch Engagement** | Get metrics for posts | "Get engagement for last 7 days" |
| **Generate Summary** | Create daily/weekly report | "Generate daily social media summary" |

**Task Format:**
```markdown
---
title: Social Media Post
status: needs_action
skill: social_media_marketing
platform: facebook,instagram,twitter
action: generate_and_publish
---

## Post Details

**Topic:** Product Launch
**Goal:** Generate awareness
**Key Points:**
- New feature announcement
- Special launch discount
- Limited time offer
```

---

## Execution Steps

### Step 1: Generate Post Content

```
Analyze topic and goal
↓
Determine platform requirements
↓
Generate platform-specific content
↓
Add appropriate hashtags
↓
Return content for review
```

### Step 2: Publish Post

```
Select target platforms
↓
Call Social MCP /publish endpoint
↓
Handle platform-specific formatting
↓
Return post IDs and URLs
```

### Step 3: Fetch Engagement

```
Call Social MCP /analytics endpoint
↓
Aggregate metrics across platforms
↓
Calculate engagement rates
↓
Return consolidated metrics
```

### Step 4: Generate Summary

```
Fetch posts for period
↓
Calculate totals (reach, engagement)
↓
Identify top performing content
↓
Generate daily_social_summary.md
↓
Save to Business/Marketing/
```

---

## MCP Server Integration

### Social MCP Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/post/schedule` | POST | Schedule a post |
| `/post/publish` | POST | Publish immediately |
| `/analytics` | GET | Get engagement metrics |
| `/calendar` | GET | Get content calendar |

### Example: Publish Post

```json
POST http://localhost:8768/post/publish
{
  "content": "🚀 Exciting news! Our new product is here...",
  "platforms": ["facebook", "instagram", "twitter"],
  "hashtags": ["#ProductLaunch", "#Innovation"],
  "agent_id": "social_media_agent"
}
```

### Example: Get Analytics

```json
GET http://localhost:8768/analytics?period=7d

Response:
{
  "success": true,
  "analytics": {
    "facebook": {"impressions": 5000, "likes": 150, "shares": 25},
    "instagram": {"impressions": 3000, "likes": 200, "comments": 30},
    "twitter": {"impressions": 2000, "likes": 80, "retweets": 15}
  }
}
```

---

## Platform-Specific Guidelines

### Facebook

**Best Practices:**
- Post length: 40-80 characters for best engagement
- Include image or video
- Post 1-2 times per day
- Use 3-5 hashtags

**Content Types:**
- Status updates
- Photo posts
- Video posts
- Link shares
- Events

### Instagram

**Best Practices:**
- High-quality images required
- Post length: 138-150 characters
- Use 10-15 hashtags
- Post 1-3 times per day
- Use Stories for engagement

**Content Types:**
- Feed posts (image/video)
- Stories (24hr ephemeral)
- Reels (short video)
- IGTV (long video)

### Twitter (X)

**Best Practices:**
- Tweet length: 100-120 characters (leave room for RTs)
- Use 1-2 hashtags
- Include images/videos when possible
- Tweet 3-5 times per day
- Engage with replies

**Content Types:**
- Standard tweets
- Threads (connected tweets)
- Polls
- Quote tweets

---

## Output Format

### Post Generation Response

```json
{
  "success": true,
  "generated_posts": {
    "facebook": {
      "content": "🎉 Exciting news! Our new product...",
      "hashtags": ["#ProductLaunch", "#Innovation"],
      "character_count": 150
    },
    "instagram": {
      "content": "✨ Something amazing is here!...",
      "hashtags": ["#NewProduct", "#Launch", "#Innovation"],
      "character_count": 180
    },
    "twitter": {
      "content": "🚀 It's here! Our new product...",
      "hashtags": ["#Launch"],
      "character_count": 120
    }
  }
}
```

### Publishing Response

```json
{
  "success": true,
  "published": {
    "facebook": {
      "post_id": "FB_123456",
      "url": "https://facebook.com/posts/123456",
      "status": "published"
    },
    "instagram": {
      "post_id": "IG_789012",
      "url": "https://instagram.com/p/789012",
      "status": "published"
    }
  }
}
```

---

## Daily Summary Format

### Generated File: `Business/Marketing/daily_social_summary.md`

```markdown
# Daily Social Media Summary

**Date:** 2026-02-24
**Generated by:** AI Employee Social Media Agent

---

## Summary

| Platform | Posts | Impressions | Engagement | Rate |
|----------|-------|-------------|------------|------|
| Facebook | 3 | 5,000 | 175 | 3.5% |
| Instagram | 2 | 3,000 | 230 | 7.7% |
| Twitter | 5 | 2,000 | 95 | 4.8% |
| **Total** | **10** | **10,000** | **500** | **5.0%** |

---

## Top Performing Posts

### Facebook
**Post:** "🎉 Exciting news!..."
**Engagement:** 150 likes, 25 shares
**Reach:** 4,500

### Instagram
**Post:** "✨ Something amazing..."
**Engagement:** 200 likes, 30 comments
**Reach:** 2,800

### Twitter
**Post:** "🚀 It's here!..."
**Engagement:** 80 likes, 15 retweets
**Reach:** 1,900

---

## Content Calendar (Next 7 Days)

| Date | Platform | Topic | Status |
|------|----------|-------|--------|
| Feb 25 | Facebook | Product tips | Scheduled |
| Feb 25 | Instagram | Behind the scenes | Scheduled |
| Feb 26 | Twitter | Industry news | Draft |

---

## Recommendations

1. **Instagram** showing highest engagement rate - consider increasing post frequency
2. **Twitter** threads performing well - create more thread content
3. **Facebook** video posts get 2x engagement - add more video content

---

*Generated automatically by AI Employee Social Media Agent*
```

---

## Completion Rules

A social media task is **complete** when:

- [ ] **Content generated** - Platform-specific content created
- [ ] **Published/Scheduled** - Post published or scheduled via MCP
- [ ] **Metrics fetched** - Engagement data retrieved (if requested)
- [ ] **Summary updated** - Daily summary generated (if applicable)
- [ ] **Logged** - Activity logged to MCP and local files

---

## Error Handling

| Error | Handling |
|-------|----------|
| MCP server offline | Use fallback (generate content, queue for later) |
| Platform API error | Retry with backoff, log error |
| Content rejected | Revise content, check platform guidelines |
| Rate limit exceeded | Queue for later, respect rate limits |

---

## Integration with Other Skills

| Scenario | Handoff To | Information Passed |
|----------|------------|-------------------|
| Post needs approval | `approval` | Post content for review |
| Marketing report | `documentation` | Summary data for formatting |
| Product announcement | `linkedin_marketing` | Coordinated messaging |
| Customer response | `email` | Follow-up emails |

---

## Security

### Credential Management

- Platform API tokens stored in `MCP/social_mcp/config.json`
- File permissions: 600 (owner read/write only)
- Use app-specific tokens when available

### Content Guidelines

- No automated posting to personal accounts without consent
- Respect platform terms of service
- Include proper disclosures for sponsored content

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Posts not publishing | Check MCP server is running |
| Wrong formatting | Verify platform-specific guidelines |
| Low engagement | Review posting times and content quality |
| Hashtags not working | Check platform hashtag limits |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial social media marketing skill |
