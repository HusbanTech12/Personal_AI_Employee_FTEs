# Skill: Odoo Accounting

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | `odoo_accounting` |
| **Tier** | Gold |
| **Version** | 1.0 |
| **Status** | Active |
| **Category** | Business - Accounting |
| **Backend** | Odoo Community (v19+) |
| **Protocol** | JSON-RPC |

---

## Purpose

Manage business accounting operations through self-hosted Odoo Community ERP. This skill:

1. **Connects** to Odoo via JSON-RPC API
2. **Creates** and manages invoices
3. **Reads** transactions and account moves
4. **Fetches** account balances
5. **Generates** financial summaries and reports
6. **Integrates** with Accounting MCP server

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│ Accounting      │ ──→ │  Accounting MCP  │ ──→ │  Odoo Community │
│ Agent           │     │  Server (8767)   │     │  (JSON-RPC)     │
│                 │     │                  │     │  Port: 8069     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## Configuration

### Odoo Connection

Store credentials in `MCP/accounting_mcp/odoo_config.json`:

```json
{
  "host": "localhost",
  "port": 8069,
  "database": "your_database",
  "username": "your_username",
  "api_key": "your_api_key",
  "protocol": "http"
}
```

### Environment Variables

```bash
export ODOO_HOST="localhost"
export ODOO_PORT="8069"
export ODOO_DATABASE="your_database"
export ODOO_USERNAME="your_username"
export ODOO_API_KEY="your_api_key"
```

---

## Accepted Inputs

| Input Type | Description | Examples |
|------------|-------------|----------|
| **Create Invoice** | Generate customer invoice | Invoice for services, product sale |
| **Read Transactions** | Query account moves | Get recent transactions, filter by date |
| **Fetch Balances** | Get account balances | Current balance, receivable, payable |
| **Generate Summary** | Create financial report | Weekly summary, monthly report |

**Task Format:**
```markdown
---
title: Create Invoice
status: needs_action
skill: odoo_accounting
action: create_invoice
---

## Invoice Details

**Customer:** Client Name
**Amount:** $1,500.00
**Description:** Consulting services
**Due Date:** 2026-03-01
```

---

## JSON-RPC API Integration

### Connection Method

```python
import requests

class OdooConnector:
    def __init__(self, config):
        self.url = f"{config['protocol']}://{config['host']}:{config['port']}/jsonrpc"
        self.db = config['database']
        self.username = config['username']
        self.api_key = config['api_key']
        self.uid = None
    
    def authenticate(self):
        """Authenticate with Odoo."""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "common",
                "method": "authenticate",
                "args": [self.db, self.username, self.api_key, {}]
            },
            "id": 1
        }
        
        response = requests.post(self.url, json=payload)
        result = response.json()
        
        if 'result' in result:
            self.uid = result['result']
            return True
        return False
    
    def execute(self, model, method, args=None, kwargs=None):
        """Execute Odoo model method."""
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute_kw",
                "args": [
                    self.db,
                    self.uid,
                    self.api_key,
                    model,
                    method,
                    args or [],
                    kwargs or {}
                ]
            },
            "id": 2
        }
        
        response = requests.post(self.url, json=payload)
        result = response.json()
        
        if 'result' in result:
            return result['result']
        raise Exception(result.get('error', 'Unknown error'))
```

---

## Execution Steps

### Step 1: Connect to Odoo

```
Load configuration
↓
Authenticate via JSON-RPC
↓
Get user ID (uid)
↓
Verify connection
```

### Step 2: Create Invoice

```
Prepare invoice data
↓
Call account.move.create
↓
Add invoice lines
↓
Post invoice
↓
Return invoice details
```

### Step 3: Read Transactions

```
Define date range
↓
Search account.move records
↓
Filter by type (invoice, payment)
↓
Return transaction list
```

### Step 4: Fetch Balances

```
Query account.account
↓
Filter by account type
↓
Calculate balances
↓
Return balance summary
```

### Step 5: Generate Summary

```
Fetch transactions for period
↓
Calculate totals (income, expenses)
↓
Generate weekly_financial_summary.md
↓
Save to Logs/Accounting/
```

---

## Odoo Models Used

| Model | Purpose | Methods |
|-------|---------|---------|
| `account.move` | Invoices & bills | create, read, search, action_post |
| `account.move.line` | Invoice lines | create, read, search |
| `account.account` | Chart of accounts | read, search |
| `res.partner` | Customers/Vendors | read, search, create |
| `account.journal` | Journals | read, search |

---

## Output Format

### Invoice Creation Response

```json
{
  "success": true,
  "invoice": {
    "id": 12345,
    "name": "INV/2026/0001",
    "partner": "Client Name",
    "amount_total": 1500.00,
    "state": "posted",
    "invoice_date": "2026-02-24",
    "due_date": "2026-03-01"
  }
}
```

### Transaction List

```json
{
  "success": true,
  "transactions": [
    {
      "id": 12345,
      "name": "INV/2026/0001",
      "date": "2026-02-24",
      "type": "out_invoice",
      "amount": 1500.00,
      "state": "posted"
    }
  ]
}
```

### Balance Summary

```json
{
  "success": true,
  "balances": {
    "accounts_receivable": 5000.00,
    "accounts_payable": 2500.00,
    "bank": 10000.00,
    "net": 12500.00
  }
}
```

---

## Weekly Financial Summary

### Generated File: `Logs/Accounting/weekly_financial_summary.md`

```markdown
# Weekly Financial Summary

**Week:** 8, 2026
**Period:** 2026-02-17 to 2026-02-24

---

## Summary

| Metric | Amount |
|--------|--------|
| Total Income | $15,000.00 |
| Total Expenses | $8,500.00 |
| Net Income | $6,500.00 |

---

## Invoices Created

| Invoice | Customer | Amount | Status |
|---------|----------|--------|--------|
| INV/2026/0001 | Client A | $1,500.00 | Posted |
| INV/2026/0002 | Client B | $2,000.00 | Posted |

---

## Bills Paid

| Bill | Vendor | Amount | Status |
|------|--------|--------|--------|
| BILL/2026/0001 | Supplier X | $500.00 | Paid |

---

## Account Balances

| Account | Balance |
|---------|---------|
| Accounts Receivable | $5,000.00 |
| Accounts Payable | $2,500.00 |
| Bank | $10,000.00 |

---

*Generated by AI Employee Odoo Accounting Agent*
```

---

## Completion Rules

An accounting task is **complete** when:

- [ ] **Odoo connected** - Authentication successful
- [ ] **Action executed** - Invoice created / data fetched
- [ ] **Response validated** - Odoo returned success
- [ ] **Logged** - Activity logged to MCP
- [ ] **Summary generated** - Weekly summary updated (if applicable)

---

## Error Handling

| Error | Handling |
|-------|----------|
| Authentication failed | Check credentials, retry |
| Connection timeout | Retry with backoff |
| Invoice creation failed | Log error, return details |
| Model not found | Verify Odoo version compatibility |

---

## Security

### Credential Storage

- Credentials stored in `MCP/accounting_mcp/odoo_config.json`
- File permissions: 600 (owner read/write only)
- API key used instead of password

### Access Control

- Read-only access for reports
- Write access limited to invoice creation
- No delete operations allowed

---

## Integration with Other Skills

| Scenario | Handoff To | Information Passed |
|----------|------------|-------------------|
| Invoice needs approval | `approval` | Invoice details for approval |
| Financial report | `documentation` | Summary data for formatting |
| Payment reminder | `email` | Customer email, invoice details |

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Can't connect to Odoo | Check host/port, verify Odoo is running |
| Authentication fails | Verify API key in Odoo settings |
| Invoice creation fails | Check account journal configuration |
| Model not found | Verify Odoo version (requires 19+) |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-24 | Initial Odoo accounting integration |
