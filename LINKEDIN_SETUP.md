# LinkedIn Integration Setup Guide

**Version:** 1.0  
**Date:** 2026-02-26  
**Tier:** Gold

---

## Overview

Autonomous LinkedIn posting agent that publishes business content directly via LinkedIn API.

---

## Architecture

```
Marketing Task → Planner → LinkedIn Agent → Content Generator → LinkedIn API
                                                                        ↓
Business/Marketing/linkedin_posts/ ← Engagement Summary ← Post URL + ID
```

---

## Quick Start (Demo Mode)

### Step 1: Install Dependencies

```bash
cd /mnt/d/Quarter_4/Hackathon_0/AI_Employee_Vault
./venv/bin/pip install -r requirements.txt
```

### Step 2: Start System

```bash
bash run_agents.sh
```

The LinkedIn agent will:
- Start in **DEMO MODE** (no actual posts published)
- Monitor `Needs_Action/` for LinkedIn tasks
- Generate content and simulate publication
- Save engagement summaries to `Business/Marketing/linkedin_posts/`

---

## Production Setup (With LinkedIn API)

### Step 1: Create LinkedIn Developer Account

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/)
2. Sign in with your LinkedIn account
3. Create a new app for your organization

### Step 2: Get API Credentials

From your LinkedIn App Dashboard:

1. **Access Token:**
   - Go to "Auth" tab
   - Generate token with `w_organization_social` permission
   - Copy the access token

2. **Organization ID:**
   - Go to "Products" tab
   - Enable "Share on LinkedIn"
   - Your Organization ID is shown in the dashboard

### Step 3: Configure Environment Variables

```bash
export LINKEDIN_ACCESS_TOKEN="AQ..."
export LINKEDIN_ORG_ID="12345678"
export LINKEDIN_AUTHOR_URN="urn:li:organization:12345678"
```

### Step 4: Verify Configuration

```bash
python Agents/linkedin_agent.py
```

You should see:
```
LinkedIn Agent Starting...
Demo Mode: False
API Configured: True
```

---

## Creating LinkedIn Tasks

### Task Format

Drop a markdown file in `Inbox/`:

```markdown
---
title: LinkedIn Product Launch
status: needs_action
priority: standard
skill: linkedin_post
topic: Product Launch
audience: Business professionals
tone: enthusiastic
---

## Content Brief

Announce our new AI Employee Gold Tier with multi-agent system.
Key features to highlight:
- 6 autonomous agents
- Automatic task routing
- Built-in retry logic
- Full analytics tracking
```

### Task Fields

| Field | Required | Description |
|-------|----------|-------------|
| `skill` | ✅ | Must be `linkedin_post` |
| `topic` | ✅ | Post topic/title |
| `audience` | Optional | Target audience |
| `tone` | Optional | `professional`, `conversational`, `enthusiastic`, `educational` |
| `visibility` | Optional | `PUBLIC` (default) or `CONNECTIONS` |

---

## Content Templates

### Professional Tone

```
We're pleased to announce {news}.

{Value proposition}.

Learn more about our solution.

#Business #Leadership #Innovation
```

### Enthusiastic Tone

```
🚀 Big news!

{Exciting announcement}.

This is just the beginning!

#AI #Technology #ProductLaunch
```

### Educational Tone

```
Here's something valuable to know about {topic}.

{Educational content}.

Save this for later reference.

#Education #Tips #Professional
```

---

## File Structure

```
AI_Employee_Vault/
├── Agents/
│   └── linkedin_agent.py          # LinkedIn posting agent
├── Skills/
│   └── linkedin_post.SKILL.md     # Skill definition
├── Config/
│   └── linkedin_config.json       # Configuration
├── Domains/Business/Marketing/
│   └── linkedin_posts/            # Published post summaries
├── Needs_Action/
│   └── linkedin_*.md              # LinkedIn tasks
└── Logs/
    └── linkedin_agent_*.log       # Agent logs
```

---

## API Details

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
        "text": "Post content with hashtags"
      },
      "shareMediaCategory": "NONE"
    }
  },
  "visibility": {
    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
  }
}
```

### Response (201 Created)

```json
{
  "id": "urn:li:share:123456789"
}
```

---

## Engagement Summary

After publishing, a summary file is created:

**Location:** `Business/Marketing/linkedin_posts/linkedin_post_YYYYMMDD_HHMMSS.md`

```markdown
---
title: LinkedIn Post - Product Launch
status: Published
post_id: urn:li:share:123456789
post_url: https://linkedin.com/feed/update/...
---

# LinkedIn Post Summary

## Post Content

{Full post text}

## Hashtags

#AI #Automation #Technology

## Engagement Summary

| Metric | Value |
|--------|-------|
| Impressions | 0 |
| Likes | 0 |
| Comments | 0 |
| Shares | 0 |
```

---

## Error Handling

| Error | Handling |
|-------|----------|
| API not configured | Run in demo mode |
| Invalid token | Retry up to 3 times, then log failure |
| Rate limit | Wait 30 seconds, retry |
| Network error | Add to retry queue |

---

## Troubleshooting

### Demo Mode Only

**Problem:** Agent runs in demo mode

**Solution:**
```bash
# Verify environment variables
echo $LINKEDIN_ACCESS_TOKEN
echo $LINKEDIN_ORG_ID

# Restart agent after setting variables
```

### Posts Not Publishing

**Problem:** Posts fail to publish

**Solutions:**
1. Check token has `w_organization_social` permission
2. Verify Organization ID is correct
3. Check agent logs: `Logs/linkedin_agent_*.log`

### 401 Unauthorized

**Problem:** API returns 401

**Solution:** Access token expired. Generate new token from LinkedIn Developer Console.

---

## Security Best Practices

1. **Never commit credentials** - Use environment variables
2. **Minimal permissions** - Request only `w_organization_social`
3. **Token rotation** - Regenerate tokens periodically
4. **Monitor logs** - Review `Logs/linkedin_agent_*.log` regularly

---

## Monitoring

### Check Agent Status

```bash
# View recent logs
tail -f Logs/linkedin_agent_*.log

# Check published posts
ls -la Business/Marketing/linkedin_posts/
```

### View Published Posts

```bash
# List all published posts
cat Business/Marketing/linkedin_posts/*.md
```

---

## Related Documentation

- [Skills/linkedin_post.SKILL.md](Skills/linkedin_post.SKILL.md) - Skill definition
- [LinkedIn API Docs](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/community-management/shares/ugc-posts-api)

---

## Support

For issues:
1. Check logs in `Logs/` folder
2. Review this setup guide
3. Verify LinkedIn API credentials
4. Check LinkedIn Developer Console for API status
