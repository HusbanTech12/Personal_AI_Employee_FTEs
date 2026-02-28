# LinkedIn Marketing Agent Skill

## Purpose

Autonomous business growth agent that leverages LinkedIn for brand building, lead generation, and audience engagement through strategic content creation and automated posting.

---

## Capabilities

### 1. Weekly Business Post Generation

- Generate professional business posts weekly
- Align content with company goals and values
- Incorporate industry trends and news
- Maintain consistent brand voice and messaging
- Optimize for LinkedIn algorithm (hashtags, timing, format)

### 2. Multi-Source Content Conversion

Convert insights from multiple channels into posts:

| Source | Content Type | Conversion |
|--------|--------------|------------|
| **Gmail** | Client testimonials, success stories | Case study posts |
| **WhatsApp** | Customer feedback, quick wins | Achievement posts |
| **Internal Docs** | Product updates, milestones | Announcement posts |
| **Industry News** | Trends, market shifts | Thought leadership |
| **Company Events** | Meetings, partnerships | Engagement posts |

### 3. Sales-Focused Content Creation

Create content designed to drive sales:

- **Problem-Awareness Posts**: Highlight common pain points
- **Solution Posts**: Showcase product/service benefits
- **Social Proof Posts**: Share testimonials, case studies
- **Urgency Posts**: Limited offers, time-sensitive deals
- **Educational Posts**: Tips that lead to product interest

### 4. Automated Posting System

- Post using LinkedIn MCP Server
- Schedule posts for optimal engagement times
- Handle image/video attachments
- Include relevant hashtags (3-5 per post)
- Tag relevant companies/people when appropriate

### 5. Engagement Summary Generation

- Track post performance metrics
- Generate weekly engagement reports
- Analyze audience demographics
- Identify top-performing content types
- Recommend content strategy adjustments

---

## Schedule

### Automatic Posting Cadence

```
Post Frequency: Every 2 days (3-4 posts per week)
Optimal Times: Tuesday-Thursday, 8-10 AM or 12-1 PM
```

### Weekly Content Calendar

| Day | Content Type | Goal |
|-----|--------------|------|
| **Monday** | Motivational/Industry Insight | Engagement |
| **Wednesday** | Product/Service Highlight | Awareness |
| **Friday** | Case Study/Testimonial | Social Proof |
| **Sunday** (optional) | Thought Leadership | Authority |

### Content Mix Ratio

```
40% Educational/Value-driven
30% Social Proof/Case Studies
20% Promotional/Sales-focused
10% Company Culture/Behind-the-scenes
```

---

## Workflow

```
┌──────────────────┐
│  Content         │
│  Ideation        │ ← Gather insights from emails, WhatsApp, trends
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Content         │ ← Write post, select media, add hashtags
│  Creation        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Review &        │ ← Check quality, compliance, brand alignment
│  Approval        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Schedule &      │ ← Queue for optimal time, auto-post
│  Post            │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Track &         │ ← Monitor engagement, log results
│  Report          │
└──────────────────┘
```

---

## Post Templates

### Template 1: Problem-Solution Post
```markdown
🎯 Are you struggling with [common pain point]?

You're not alone. [X]% of businesses face this challenge daily.

Here's what we've learned helping [number] clients:

✅ [Solution tip 1]
✅ [Solution tip 2]
✅ [Solution tip 3]

Want to learn how we can help you solve this? 
Drop a comment or send us a message! 💬

#IndustryHashtag #Solution #BusinessGrowth
```

### Template 2: Case Study Post
```markdown
📈 CLIENT SUCCESS STORY

When [Client Name] came to us, they were facing [challenge].

The results after working together?
→ [Result 1 with metric]
→ [Result 2 with metric]
→ [Result 3 with metric]

"We couldn't have done it without [Company]!" - [Client Name]

Ready for similar results? Let's talk! 🚀

#CaseStudy #ClientSuccess #Results
```

### Template 3: Thought Leadership Post
```markdown
💡 INDUSTRY INSIGHT

The landscape of [industry] is changing fast.

Here's what I'm seeing in [year]:

1️⃣ [Trend 1]
2️⃣ [Trend 2]
3️⃣ [Trend 3]

The companies that adapt to these changes will thrive.
Those that don't? They'll be left behind.

Where do you stand? 👇

#ThoughtLeadership #IndustryTrends #Future
```

### Template 4: Promotional Post
```markdown
🔥 LIMITED TIME OFFER

For the next [timeframe], we're offering:

✨ [Offer detail 1]
✨ [Offer detail 2]
✨ [Offer detail 3]

This is your chance to [benefit] at an unbeatable value.

⏰ Offer ends [date]
📩 DM us "READY" to claim your spot!

Don't miss out! 

#SpecialOffer #LimitedTime #ActNow
```

### Template 5: Educational Post
```markdown
📚 QUICK TIP: [Topic]

Did you know that [surprising fact/statistic]?

Here's why this matters:

[Brief explanation in 2-3 sentences]

Pro tip: [Actionable advice]

Save this for later! 🔖

#Tip #Education #ProfessionalDevelopment
```

---

## Input Schema

```json
{
  "content_request_id": "string",
  "source": "email|whatsapp|internal|manual|trending",
  "source_data": {
    "type": "testimonial|feedback|update|news|idea",
    "content": "string",
    "sender": "string|null",
    "timestamp": "ISO8601"
  },
  "post_type": "educational|promotional|case_study|thought_leadership|engagement",
  "priority": "normal|high|urgent",
  "scheduled_time": "ISO8601|null",
  "media_attachments": [
    {
      "type": "image|video|document",
      "path": "string",
      "caption": "string"
    }
  ],
  "hashtags": ["string"],
  "mentions": ["string"]
}
```

---

## Output Schema

```json
{
  "post_id": "string",
  "content_request_id": "string",
  "post_content": {
    "text": "string",
    "media": ["string"],
    "hashtags": ["string"],
    "mentions": ["string"]
  },
  "scheduling": {
    "scheduled_time": "ISO8601",
    "posted_time": "ISO8601|null",
    "status": "draft|scheduled|posted|failed"
  },
  "engagement": {
    "impressions": "integer|null",
    "likes": "integer|null",
    "comments": "integer|null",
    "shares": "integer|null",
    "clicks": "integer|null"
  },
  "storage_path": "Vault/SocialMedia/LinkedInPosts/*.md",
  "logged": "boolean"
}
```

---

## Post Storage Format

All posts stored in `Vault/SocialMedia/LinkedInPosts/`:

```markdown
# LinkedIn Post: <POST_ID>

## Created
<Timestamp>

## Post Type
<type>

## Content
<full post text>

## Media
- <list of attached media>

## Hashtags
#Hashtag1 #Hashtag2 #Hashtag3

## Mentions
@Company @Person

## Scheduling
- **Scheduled For**: <datetime>
- **Posted At**: <datetime>
- **Status**: <draft|scheduled|posted|failed>

## Source
- **Origin**: <email|whatsapp|internal|manual|trending>
- **Source Data**: <reference to original content>

## Performance (Post-Publish)
| Metric | Value |
|--------|-------|
| Impressions | |
| Likes | |
| Comments | |
| Shares | |
| Clicks | |

## Notes
<any additional notes>

---
*Generated by LinkedIn Marketing Agent*
```

---

## Engagement Summary Report

Weekly report generated every Monday:

```markdown
# LinkedIn Engagement Summary

## Report Period
<start_date> to <end_date>

## Overview
| Metric | This Week | Last Week | Change |
|--------|-----------|-----------|--------|
| Posts Published | | | |
| Total Impressions | | | |
| Total Engagement | | | |
| Engagement Rate | | | |
| New Followers | | | |
| Profile Views | | | |

## Top Performing Posts
1. **<Post Title>** - <engagement metric>
2. **<Post Title>** - <engagement metric>
3. **<Post Title>** - <engagement metric>

## Content Performance by Type
| Type | Posts | Avg Engagement |
|------|-------|----------------|
| Educational | | |
| Promotional | | |
| Case Study | | |
| Thought Leadership | | |

## Audience Insights
- **Top Industries**: <list>
- **Top Locations**: <list>
- **Top Job Functions**: <list>

## Recommendations
1. <recommendation_1>
2. <recommendation_2>
3. <recommendation_3>

## Next Week's Content Plan
- <planned_post_1>
- <planned_post_2>
- <planned_post_3>

---
*Generated by LinkedIn Marketing Agent*
```

---

## Content Generation Rules

### Do's
✅ Keep posts under 1,300 characters for optimal readability
✅ Include 3-5 relevant hashtags per post
✅ Use emojis sparingly (2-4 per post)
✅ Include clear call-to-action (CTA)
✅ Tag relevant companies/people when appropriate
✅ Post during peak engagement hours
✅ Respond to comments within 24 hours

### Don'ts
❌ Over-promote (follow 80/20 rule: 80% value, 20% promotion)
❌ Use generic or irrelevant hashtags
❌ Post controversial or polarizing content
❌ Ignore comments and engagement
❌ Post inconsistently
❌ Use excessive emojis or slang
❌ Share confidential client information

---

## Audit Log Format

All actions logged to `Logs/linkedin_agent.log`:

```
[TIMESTAMP] | POST_ID | TYPE | SOURCE | ACTION | STATUS | ENGAGEMENT | NOTES
```

Example:
```
[2026-02-28T09:00:00Z] | LI_POST_001 | case_study | email | scheduled | success | pending | Client testimonial from john @company.com
[2026-02-28T12:00:15Z] | LI_POST_002 | educational | manual | posted | success | 245/12/3/1 | Industry tips post
[2026-03-01T08:00:00Z] | LI_POST_003 | promotional | whatsapp | posted | success | 189/8/1/0 | Limited offer announcement
```

---

## Integration Points

### Required Connections

| System | Purpose | Method |
|--------|---------|--------|
| Gmail Agent | Extract testimonials, success stories | File system watch |
| WhatsApp Agent | Capture feedback, quick wins | File system watch |
| LinkedIn MCP Server | Post content, fetch analytics | MCP protocol |
| Social Intelligence | Content approval workflow | Skill API |
| Analytics Engine | Track engagement metrics | API integration |

### File Locations

```
Skills/linkedin_marketing_agent.SKILL.md     ← This file
Vault/SocialMedia/LinkedInPosts/             ← All posts storage
Vault/SocialMedia/Reports/                   ← Engagement summaries
Logs/linkedin_agent.log                      ← Agent audit trail
```

---

## Error Handling

| Error Type | Response |
|------------|----------|
| LinkedIn API rate limit | Queue post, retry after cooldown |
| Post content violation | Flag for manual review, log warning |
| Media upload failure | Post text-only, log media error |
| MCP Server unavailable | Queue post, retry in 15 min |
| Engagement fetch failure | Use cached data, retry next cycle |

---

## Performance Metrics

| Metric | Target |
|--------|--------|
| Post Frequency | 3-4 posts/week |
| Avg Engagement Rate | ≥3% |
| Follower Growth | ≥5%/month |
| Post Reach | ≥1,000 impressions/post |
| Click-Through Rate | ≥2% |
| Lead Generation | ≥10 leads/month |

---

## Configuration

```json
{
  "posting_enabled": true,
  "post_frequency_days": 2,
  "optimal_posting_times": ["08:00", "12:00", "17:00"],
  "timezone": "UTC",
  "auto_hashtag_enabled": true,
  "hashtag_count": 4,
  "emoji_usage": "moderate",
  "engagement_tracking_enabled": true,
  "weekly_report_day": "Monday",
  "content_approval_required": false,
  "storage_path": "Vault/SocialMedia/LinkedInPosts",
  "log_path": "Logs/linkedin_agent.log"
}
```

---

## Hashtag Strategy

### Primary Hashtags (Brand)
```
#YourCompany
#YourBrand
#YourIndustry
```

### Secondary Hashtags (Content Type)
```
#ThoughtLeadership
#CaseStudy
#BusinessTips
#IndustryInsights
#ProfessionalDevelopment
```

### Trending Hashtags (Dynamic)
- Monitor trending industry hashtags weekly
- Incorporate relevant trending topics
- Avoid controversial or unrelated trends

---

## Compliance Notes

- Do not share confidential client information without permission
- Respect LinkedIn's Terms of Service and Community Guidelines
- Avoid automated connection requests or mass messaging
- Disclose sponsored content appropriately (#ad, #sponsored)
- Maintain professional tone at all times

---

*Skill Version: 1.0.0*  
*Last Updated: 2026-02-28*  
*Tier: GOLD*
