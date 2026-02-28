# WhatsApp Autonomous Agent Skill

## Purpose

Autonomous WhatsApp messaging agent that processes business communications, handles customer queries, generates leads, and maintains conversation context with instant response capabilities.

---

## Responsibilities

### 1. Message Processing

- Process WhatsApp messages detected by `whatsapp_watcher`
- Support individual and group chat messages
- Handle text, images, documents, and voice notes
- Parse message metadata (sender, timestamp, chat ID)

### 2. Business Intent Understanding

Analyze messages for business intent:

| Intent | Description | Example |
|--------|-------------|---------|
| `PRODUCT_INQUIRY` | Questions about products/services | "What products do you offer?" |
| `PRICING_REQUEST` | Price quotes, cost information | "How much does this cost?" |
| `SUPPORT_ISSUE` | Technical problems, complaints | "My order hasn't arrived" |
| `AVAILABILITY_CHECK` | Service availability, scheduling | "Are you open on weekends?" |
| `LEAD_SIGNAL` | Purchase intent, serious interest | "I'd like to place an order" |
| `GENERAL_CHAT` | Casual conversation, greetings | "Hello", "Good morning" |

### 3. Professional Auto-Response

- Respond instantly with professional tone
- Match communication style to customer:
  - **Friendly**: New customers, general inquiries
  - **Professional**: Business partners, corporate clients
  - **Empathetic**: Support issues, complaints
- Use WhatsApp-appropriate formatting (emojis, brevity)
- Include call-to-action when relevant

### 4. Customer Query Handling

Handle common customer queries autonomously:

- Product information and specifications
- Pricing and package details
- Order status and tracking
- Business hours and location
- Return and refund policies
- Service availability

### 5. Lead Generation

- Identify and nurture potential leads
- Capture lead information:
  - Contact details
  - Interest level
  - Product/service of interest
  - Budget range (if mentioned)
- Qualify leads using BANT framework:
  - **B**udget
  - **A**uthority
  - **N**eed
  - **T**imeline

### 6. Query Escalation

Escalate complex queries when:

- Customer requests human agent
- Issue requires technical expertise
- Complaint involves legal/financial risk
- Multiple failed resolution attempts
- VIP customer detected

---

## Autonomous Behavior

### Instant Reply System

```
Message Received → Parse → Classify → Generate Response → Send (≤3 seconds)
```

**Response Time Targets:**
- Simple queries: <3 seconds
- Complex queries: <10 seconds (with acknowledgment)
- Escalations: <30 seconds (with handoff notice)

### Conversation Memory

Maintain conversation context using:

- **Short-term**: Current session messages (last 50 messages)
- **Medium-term**: Last 7 days conversation history
- **Long-term**: Customer profile and preferences

**Memory Structure:**
```json
{
  "chat_id": "string",
  "contact": {
    "name": "string",
    "phone": "string",
    "is_saved": "boolean"
  },
  "conversation_history": [],
  "customer_profile": {
    "segment": "string",
    "interests": ["string"],
    "past_purchases": ["string"],
    "preferences": {}
  },
  "open_tasks": [],
  "last_interaction": "ISO8601"
}
```

### Opportunity Detection

Create tasks when opportunity detected:

| Signal | Detected Pattern | Action |
|--------|------------------|--------|
| `HOT_LEAD` | "I want to buy", "Let's proceed" | Create SALES task immediately |
| `WARM_LEAD` | "Tell me more", "Send details" | Send info + schedule follow-up |
| `COLD_LEAD` | General inquiry, browsing | Add to nurture sequence |
| `REFERRAL` | "My friend needs", "Recommend to" | Create BUSINESS task |
| `PARTNERSHIP` | "Collaboration", "Partnership" | Create BUSINESS task |

---

## Workflow

```
┌──────────────────┐
│  Message         │
│  Detected        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Parse &         │ ← Extract text, media, metadata
│  Analyze         │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Classify        │ ← Intent, sentiment, urgency
│  Intent          │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Check Memory    │ ← Load conversation context
│  & Context       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Generate        │ ← Craft response, attach info
│  Response        │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  Send &          │ ← Deliver message, log action
│  Log             │
└──────────────────┘
```

---

## Input Schema

```json
{
  "message_id": "string",
  "chat_id": "string",
  "chat_type": "individual|group",
  "from": {
    "name": "string",
    "phone": "string",
    "is_business": "boolean",
    "is_saved_contact": "boolean"
  },
  "content": {
    "type": "text|image|document|voice|video",
    "text": "string|null",
    "caption": "string|null",
    "media_url": "string|null",
    "mime_type": "string|null"
  },
  "timestamp": "ISO8601",
  "is_forwarded": "boolean",
  "reply_to": "string|null",
  "mentions": ["string"]
}
```

---

## Output Schema

```json
{
  "task_id": "string",
  "message_id": "string",
  "chat_id": "string",
  "classification": {
    "intent": "string",
    "sentiment": "positive|neutral|negative",
    "urgency": "low|medium|high|critical",
    "confidence": "float"
  },
  "lead_detection": {
    "is_lead": "boolean",
    "lead_quality": "cold|warm|hot",
    "lead_score": "integer (0-100)",
    "opportunity_type": "string|null"
  },
  "action": {
    "type": "reply|escalate|create_task|ignore",
    "response_text": "string|null",
    "response_media": ["string"],
    "task_created": "string|null",
    "escalation_target": "string|null"
  },
  "memory_updated": "boolean",
  "logged": "boolean"
}
```

---

## Response Templates

### Greeting Responses
```
👋 Hi [Name]! Thanks for reaching out to [Company]. 
How can we help you today?
```

### Product Inquiry Response
```
Great question! [Product Name] is [brief description].

Key features:
✨ [Feature 1]
✨ [Feature 2]
✨ [Feature 3]

Would you like more details or a quote?
```

### Pricing Request Response
```
Thanks for your interest! 💼

[Product/Service] starts at [price range].
The exact price depends on [factors].

Can you tell me more about your requirements 
so I can give you an accurate quote?
```

### Support Issue Response
```
I'm sorry to hear you're experiencing this issue. 
Let me help you resolve it. 🔧

[Troubleshooting steps or solution]

If this doesn't work, I can connect you with 
our technical team right away.
```

### Lead Capture Response
```
That sounds like a great fit! 🎯

To make sure I connect you with the right solution, 
could you share:
1. What's your main goal?
2. What's your timeline?
3. Do you have a budget in mind?

This helps me serve you better!
```

### Escalation Notice
```
Let me connect you with a specialist who can 
assist you better. One moment please... 🤝

[Agent Name] will be with you shortly.
```

---

## Task Creation Examples

### Example 1: Price Inquiry → Product Info
```
Incoming: "How much is your premium package?"

Action: 
- Send pricing information
- Log interaction
- No task created (informational)
```

### Example 2: Interest Detected → SALES Task
```
Incoming: "I'm interested in signing up for the annual plan"

Action:
- Send confirmation and next steps
- Create SALES task: "Follow up with [Name] - Annual Plan Interest"
- Update lead score to HOT
- Log to CRM
```

### Example 3: Complex Issue → Escalation
```
Incoming: "This is the third time my order is delayed. 
           I want to speak to a manager."

Action:
- Send empathetic acknowledgment
- Create URGENT support ticket
- Escalate to human agent
- Flag conversation for review
```

---

## Lead Scoring System

| Score Range | Classification | Action |
|-------------|----------------|--------|
| 0-30 | Cold Lead | Nurture sequence, monthly follow-up |
| 31-60 | Warm Lead | Weekly check-in, send relevant content |
| 61-85 | Hot Lead | Daily follow-up, prioritize response |
| 86-100 | Ready to Buy | Immediate sales handoff, call within 1 hour |

**Scoring Factors:**
- Explicit purchase intent (+30)
- Budget mentioned (+20)
- Timeline specified (+20)
- Decision maker confirmed (+20)
- Previous customer (+10)

---

## Audit Log Format

All actions logged to `Logs/whatsapp_agent.log`:

```
[TIMESTAMP] | CHAT_ID | FROM | INTENT | SENTIMENT | ACTION | TASK_ID | LEAD_SCORE | NOTES
```

Example:
```
[2026-02-28T14:20:00Z] | chat_abc123 | +1234567890 | PRICING_REQUEST | neutral | reply | none | 45 | Sent pricing info
[2026-02-28T14:22:30Z] | chat_def456 | +0987654321 | LEAD_SIGNAL | positive | create_task | SALES_001 | 85 | Hot lead - annual plan
[2026-02-28T14:25:15Z] | chat_ghi789 | +1122334455 | SUPPORT_ISSUE | negative | escalate | SUP_002 | 60 | Escalated to manager
```

---

## Conversation Memory Storage

```
Vault/Conversations/WhatsApp/
├── chat_<chat_id>.json      ← Full conversation history
├── contacts/
│   └── <phone_number>.json  ← Contact profile and preferences
└── leads/
    └── lead_<timestamp>.md  ← Captured lead details
```

**Lead Capture Format:**
```markdown
# Lead: <LEAD_ID>

## Captured
<Timestamp>

## Contact
- **Name**: <name>
- **Phone**: <phone>
- **Chat ID**: <chat_id>

## Opportunity
- **Interest**: <product/service>
- **Budget**: <budget if mentioned>
- **Timeline**: <timeline if mentioned>
- **Lead Score**: <score>/100
- **Quality**: <cold|warm|hot>

## Conversation Summary
<summary of relevant conversation>

## Next Steps
- [ ] <action_1>
- [ ] <action_2>
- [ ] <action_3>

## Assigned To
<agent_name>

---
*Captured by WhatsApp Autonomous Agent*
```

---

## Integration Points

### Required Connections

| System | Purpose | Method |
|--------|---------|--------|
| whatsapp_watcher | Message detection | File system watch / Webhook |
| WhatsApp Business API | Send messages | API calls |
| Social Intelligence | Intent classification | Skill API |
| CRM System | Lead management | API integration |
| Task Executor | Task creation | Plan file generation |

### File Locations

```
Skills/whatsapp_autonomous_agent.SKILL.md  ← This file
Vault/Conversations/WhatsApp/              ← Conversation memory
Vault/Conversations/WhatsApp/leads/        ← Captured leads
Logs/whatsapp_agent.log                    ← Agent audit trail
```

---

## Error Handling

| Error Type | Response |
|------------|----------|
| WhatsApp API rate limit | Queue message, retry after cooldown |
| Message parse failure | Send generic acknowledgment, log error |
| Classification low confidence | Send "Let me connect you..." response |
| Memory load failure | Continue without context, log warning |
| Send failure | Retry 3x, then escalate |

---

## Performance Metrics

- **Response Time**: Target <3 seconds (avg)
- **Classification Accuracy**: Target ≥90%
- **Lead Capture Rate**: Target ≥15% of conversations
- **Escalation Rate**: Target <10% (auto-resolved ≥90%)
- **Customer Satisfaction**: Target ≥4.5/5 (when rated)

---

## Configuration

```json
{
  "instant_reply_enabled": true,
  "max_response_time_seconds": 3,
  "conversation_memory_days": 30,
  "lead_scoring_enabled": true,
  "auto_escalation_threshold": 3,
  "business_hours_only": false,
  "emoji_usage": "moderate",
  "log_path": "Logs/whatsapp_agent.log",
  "memory_path": "Vault/Conversations/WhatsApp"
}
```

---

## Compliance Notes

- Store conversations per WhatsApp data policies
- Respect opt-out requests immediately
- Do not send unsolicited promotional messages
- Maintain customer data privacy (GDPR/CCPA compliant)
- Log consent for marketing communications

---

*Skill Version: 1.0.0*  
*Last Updated: 2026-02-28*  
*Tier: GOLD*
