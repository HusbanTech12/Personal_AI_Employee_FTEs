# MCP Architecture Documentation

## Overview

The AI Employee uses a **Model Context Protocol (MCP)** architecture for secure, modular service integration. All external operations (email, social media, accounting, automation) are routed through MCP servers.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI Employee System                                  │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
    │   Agents    │ ──→ │   MCP       │ ──→ │   MCP       │
    │  (email,    │     │   Manager   │     │   Servers   │
    │   linkedin, │     │  (Port 8770)│     │             │
    │   etc.)     │     │             │     │             │
    └─────────────┘     └──────┬──────┘     └─────────────┘
                               │
                               │ Routes requests
                               │ Handles fallback
                               │
                               ▼
         ┌─────────────────────────────────────────────────────────┐
         │                                                         │
         ▼                 ▼                 ▼                     ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐
│   Email MCP     │ │ Accounting  │ │  Social MCP │ │  Automation MCP │
│   (Port 8765)   │ │ MCP         │ │  (Port 8768)│ │  (Port 8769)    │
│                 │ │ (Port 8767) │ │             │ │                 │
│ - send          │ │ - invoice   │ │ - post      │ │ - file/copy     │
│ - queue_add     │ │ - expense   │ │ - analytics │ │ - file/move     │
│ - flush         │ │ - reports   │ │ - calendar  │ │ - transform     │
│                 │ │ - budget    │ │             │ │ - webhook       │
└─────────────────┘ └─────────────┘ └─────────────┘ └─────────────────┘
         │                 │                 │                     │
         │                 │                 │                     │
         ▼                 ▼                 ▼                     ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐
│   SMTP Server   │ │  Data Files │ │   Social    │ │   File System   │
│   or Demo Mode  │ │  (JSON)     │ │   APIs      │ │   Operations    │
└─────────────────┘ └─────────────┘ └─────────────┘ └─────────────────┘
```

---

## MCP Servers

### 1. Email MCP (Port 8765)

**File:** `MCP/email_mcp/email_mcp_server.py`

| Action | Method | Description |
|--------|--------|-------------|
| `/send` | POST | Send an email |
| `/queue/add` | POST | Add to send queue |
| `/flush` | POST | Send queued emails |
| `/status` | GET | Server status |
| `/health` | GET | Health check |

**Example Request:**
```json
POST http://localhost:8765/send
{
  "to": "user@example.com",
  "subject": "Hello",
  "body": "Message content",
  "agent_id": "email_agent"
}
```

---

### 2. LinkedIn MCP (Port 8766)

**File:** `MCP/linkedin_mcp/linkedin_mcp_server.py`

| Action | Method | Description |
|--------|--------|-------------|
| `/generate` | POST | Generate post content |
| `/publish` | POST | Publish a post |
| `/generate-and-publish` | POST | Generate and publish |
| `/analytics/:id` | GET | Get post analytics |
| `/analytics/summary` | GET | Get summary analytics |

---

### 3. Accounting MCP (Port 8767)

**File:** `MCP/accounting_mcp/accounting_mcp_server.py`

| Action | Method | Description |
|--------|--------|-------------|
| `/invoice/create` | POST | Create new invoice |
| `/expense/add` | POST | Add expense record |
| `/reports/summary` | GET | Get financial summary |
| `/budget/status` | GET | Get budget status |

**Example Request:**
```json
POST http://localhost:8767/invoice/create
{
  "to": "client@example.com",
  "amount": 1500.00,
  "description": "Consulting services",
  "due_date": "2026-03-01"
}
```

---

### 4. Social MCP (Port 8768)

**File:** `MCP/social_mcp/social_mcp_server.py`

| Action | Method | Description |
|--------|--------|-------------|
| `/post/schedule` | POST | Schedule a post |
| `/post/publish` | POST | Publish immediately |
| `/analytics` | GET | Get engagement metrics |
| `/calendar` | GET | Get content calendar |

---

### 5. Automation MCP (Port 8769)

**File:** `MCP/automation_mcp/automation_mcp_server.py`

| Action | Method | Description |
|--------|--------|-------------|
| `/file/copy` | POST | Copy file |
| `/file/move` | POST | Move file |
| `/transform` | POST | Transform data |
| `/webhook/trigger/:id` | POST | Trigger webhook |

---

## MCP Manager (Port 8770)

**File:** `MCP/mcp_manager.py`

Central registry and router for all MCP servers.

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/status` | GET | Manager status |
| `/health` | GET | Health check |
| `/actions` | GET | List all registered actions |
| `/servers` | GET | List all MCP servers |
| `/register` | POST | Register new MCP |
| `/route` | POST | Route request to MCP |
| `/health/check` | POST | Check MCP health |

### Example: Route Request

```json
POST http://localhost:8770/route
{
  "mcp": "email",
  "action": "send",
  "payload": {
    "to": "user@example.com",
    "subject": "Test"
  }
}
```

### Example: Register New MCP

```json
POST http://localhost:8770/register
{
  "name": "custom_mcp",
  "host": "127.0.0.1",
  "port": 9000,
  "actions": ["action1", "action2"]
}
```

---

## Integration Flow

### Agent → MCP Communication

```
1. Agent needs to send email
         ↓
2. Agent calls MCP Manager
   POST http://localhost:8770/route
   {
     "mcp": "email",
     "action": "send",
     "payload": {...}
   }
         ↓
3. MCP Manager routes to Email MCP
   POST http://localhost:8765/send
         ↓
4. Email MCP processes request
   - If online: Send via SMTP
   - If offline: Use fallback (queue)
         ↓
5. Response returned to Agent
   {
     "success": true,
     "message": "Email sent"
   }
```

### Fallback Flow

```
1. MCP Manager routes request
         ↓
2. Email MCP is offline (health check fails)
         ↓
3. MCP Manager executes fallback
   - Queue email for later
   - Return success with fallback: true
         ↓
4. Agent receives response
   {
     "success": true,
     "message": "Email queued (MCP offline)",
     "fallback": true
   }
```

---

## Running MCP Servers

### Start Individual Servers

```bash
# Terminal 1 - Email MCP
python MCP/email_mcp/email_mcp_server.py

# Terminal 2 - LinkedIn MCP
python MCP/linkedin_mcp/linkedin_mcp_server.py

# Terminal 3 - Accounting MCP
python MCP/accounting_mcp/accounting_mcp_server.py

# Terminal 4 - Social MCP
python MCP/social_mcp/social_mcp_server.py

# Terminal 5 - Automation MCP
python MCP/automation_mcp/automation_mcp_server.py

# Terminal 6 - MCP Manager
python MCP/mcp_manager.py
```

### Start All MCPs

```bash
# Create a startup script or use tmux/screen
tmux new-session -d -s mcp_email "python MCP/email_mcp/email_mcp_server.py"
tmux new-session -d -s mcp_linkedin "python MCP/linkedin_mcp/linkedin_mcp_server.py"
# ... etc
```

---

## Health Monitoring

MCP Manager automatically monitors all registered MCPs:

```json
GET http://localhost:8770/status

{
  "status": "running",
  "mcp_servers": {
    "email": {
      "status": "online",
      "url": "http://127.0.0.1:8765",
      "actions_count": 3,
      "last_health_check": "2026-02-24T01:00:00"
    },
    "accounting": {
      "status": "offline",
      "url": "http://127.0.0.1:8767",
      "actions_count": 4
    }
  },
  "online_mcps": 4,
  "total_mcps": 5
}
```

---

## Security

### Path Restrictions (Automation MCP)

File operations are restricted to allowed directories:

```python
ALLOWED_DIRS = [
    Path(__file__).parent.parent.parent  # Project root
]
```

### Demo Mode

All MCPs run in demo mode when credentials are not configured:

- Email: Logs instead of sending
- LinkedIn: Generates content, doesn't publish
- Accounting: Stores locally
- Social: Simulates engagement

---

## Adding New MCP Servers

### Step 1: Create MCP Server

```python
# MCP/custom_mcp/custom_mcp_server.py

class CustomMCPServer:
    HOST = "127.0.0.1"
    PORT = 9000
    
    def custom_action(self, data: Dict) -> Dict:
        # Implementation
        return {'success': True}
```

### Step 2: Register with MCP Manager

```bash
curl -X POST http://localhost:8770/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "custom",
    "host": "127.0.0.1",
    "port": 9000,
    "actions": ["custom_action"]
  }'
```

### Step 3: Use from Agents

```python
# In your agent
result = mcp_manager.route_request('custom', 'custom_action', payload)
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| MCP won't start | Check port is available |
| Health check fails | Verify MCP is running |
| Fallback always triggers | Check MCP configuration |
| Request timeout | Increase timeout in route_request |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial MCP architecture |
