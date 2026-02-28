#!/usr/bin/env python3
"""
Odoo Accounting Agent - Gold Tier AI Employee

Manages business accounting through self-hosted Odoo Community ERP.
Connects via JSON-RPC API to create invoices, read transactions, and generate reports.

Capabilities:
- Create customer invoices
- Read account transactions
- Fetch account balances
- Generate weekly financial summaries
- Integrate with Accounting MCP server

Requirements:
    pip install requests

Usage:
    python accounting_agent.py

Stop:
    Press Ctrl+C to gracefully stop
"""

import os
import sys
import re
import json
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("OdooAccountingAgent")


class OdooConnector:
    """JSON-RPC connector for Odoo Community."""
    
    def __init__(self, config: Dict):
        self.url = f"{config.get('protocol', 'http')}://{config['host']}:{config['port']}/jsonrpc"
        self.db = config['database']
        self.username = config['username']
        self.api_key = config['api_key']
        self.uid = None
        self.connected = False
    
    def authenticate(self) -> bool:
        """Authenticate with Odoo via JSON-RPC."""
        try:
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
            
            response = requests.post(self.url, json=payload, timeout=10)
            result = response.json()
            
            if 'result' in result and result['result']:
                self.uid = result['result']
                self.connected = True
                logger.info(f"Authenticated with Odoo as user {self.uid}")
                return True
            else:
                logger.error(f"Authentication failed: {result.get('error', 'Unknown error')}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def execute(self, model: str, method: str, args: Optional[List] = None, 
                kwargs: Optional[Dict] = None) -> Any:
        """Execute Odoo model method."""
        if not self.connected:
            raise Exception("Not connected to Odoo")
        
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
        
        try:
            response = requests.post(self.url, json=payload, timeout=30)
            result = response.json()
            
            if 'result' in result:
                return result['result']
            else:
                error = result.get('error', {})
                raise Exception(f"Odoo error: {error.get('data', {}).get('message', error.get('message', 'Unknown error'))}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {e}")
    
    def search_read(self, model: str, domain: Optional[List] = None, 
                    fields: Optional[List] = None, limit: int = 100) -> List[Dict]:
        """Search and read records from Odoo."""
        return self.execute(model, 'search_read', 
                           args=[domain or [], fields], 
                           kwargs={'limit': limit})


class OdooAccountingAgent:
    """
    Odoo Accounting Agent - Business accounting via Odoo ERP.
    """
    
    # MCP Accounting Server
    MCP_HOST = os.getenv("ACCOUNTING_MCP_HOST", "127.0.0.1")
    MCP_PORT = int(os.getenv("ACCOUNTING_MCP_PORT", "8767"))
    MCP_URL = f"http://{MCP_HOST}:{MCP_PORT}"
    
    def __init__(self, needs_action_dir: Path, logs_dir: Path, mcp_dir: Optional[Path] = None):
        self.needs_action_dir = needs_action_dir
        self.logs_dir = logs_dir
        self.mcp_dir = mcp_dir or (logs_dir.parent / "MCP" / "accounting_mcp")
        
        self.odoo: Optional[OdooConnector] = None
        self.config: Optional[Dict] = None
        self.processed_tasks: set = set()
        
        # Accounting directory for reports
        self.accounting_dir = self.logs_dir / "Accounting"
        self.accounting_dir.mkdir(parents=True, exist_ok=True)
        
        # Load Odoo configuration
        self._load_config()
    
    def _load_config(self):
        """Load Odoo configuration."""
        config_file = self.mcp_dir / "odoo_config.json"
        
        # Also check environment variables
        self.config = {
            'host': os.getenv('ODOO_HOST', 'localhost'),
            'port': int(os.getenv('ODOO_PORT', '8069')),
            'database': os.getenv('ODOO_DATABASE', ''),
            'username': os.getenv('ODOO_USERNAME', ''),
            'api_key': os.getenv('ODOO_API_KEY', ''),
            'protocol': os.getenv('ODOO_PROTOCOL', 'http')
        }
        
        # Load from file if exists
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    file_config = json.load(f)
                    self.config.update(file_config)
                logger.info(f"Loaded Odoo config from {config_file}")
            except Exception as e:
                logger.error(f"Failed to load config file: {e}")
        
        # Validate configuration
        if not self.config['database'] or not self.config['username'] or not self.config['api_key']:
            logger.warning("Odoo credentials not fully configured - running in demo mode")
            self.config = None
    
    def connect_to_odoo(self) -> bool:
        """Connect to Odoo ERP."""
        if not self.config:
            logger.warning("No Odoo configuration - using demo mode")
            return False
        
        self.odoo = OdooConnector(self.config)
        
        if self.odoo.authenticate():
            logger.info("Connected to Odoo successfully")
            return True
        
        logger.warning("Failed to connect to Odoo - using demo mode")
        return False
    
    def read_task(self, file_path: Path) -> Tuple[str, Dict]:
        """Read task file and extract frontmatter + content."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        frontmatter = {}
        body = content
        
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if frontmatter_match:
            fm_text = frontmatter_match.group(1)
            for line in fm_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip()
            body = content[frontmatter_match.end():]
        
        return body, frontmatter
    
    def create_invoice(self, data: Dict) -> Dict:
        """Create invoice in Odoo."""
        if not self.odoo or not self.odoo.connected:
            # Demo mode
            logger.info(f"[DEMO] Would create invoice for {data.get('partner', 'Unknown')}")
            return {
                'success': True,
                'invoice': {
                    'id': f"DEMO-{datetime.now().strftime('%Y%m%d')}",
                    'name': f"INV/DEMO/{datetime.now().strftime('%Y/%m')}",
                    'partner': data.get('partner', 'Unknown'),
                    'amount_total': float(data.get('amount', 0)),
                    'state': 'demo',
                    'invoice_date': datetime.now().strftime('%Y-%m-%d'),
                    'due_date': data.get('due_date', datetime.now().strftime('%Y-%m-%d'))
                },
                'demo_mode': True
            }
        
        try:
            # Find or create partner
            partner_id = self._find_or_create_partner(data.get('partner', ''), data.get('email', ''))
            
            # Find journal
            journal_id = self._get_sales_journal()
            
            # Create invoice
            invoice_data = {
                'move_type': 'out_invoice',
                'partner_id': partner_id,
                'journal_id': journal_id,
                'invoice_date': data.get('date', datetime.now().strftime('%Y-%m-%d')),
                'invoice_date_due': data.get('due_date'),
                'invoice_line_ids': [(0, 0, {
                    'name': data.get('description', 'Services'),
                    'quantity': 1,
                    'price_unit': float(data.get('amount', 0)),
                })]
            }
            
            invoice_id = self.odoo.execute('account.move', 'create', args=[invoice_data])
            
            # Post invoice
            self.odoo.execute('account.move', 'action_post', args=[[invoice_id]])
            
            # Read invoice details
            invoice = self.odoo.search_read(
                'account.move',
                domain=[['id', '=', invoice_id]],
                fields=['name', 'partner_id', 'amount_total', 'state', 'invoice_date', 'invoice_date_due'],
                limit=1
            )
            
            if invoice:
                inv = invoice[0]
                return {
                    'success': True,
                    'invoice': {
                        'id': invoice_id,
                        'name': inv['name'],
                        'partner': inv['partner_id'][1] if inv.get('partner_id') else data.get('partner'),
                        'amount_total': inv['amount_total'],
                        'state': inv['state'],
                        'invoice_date': inv['invoice_date'],
                        'due_date': inv['invoice_date_due']
                    }
                }
            
            return {'success': False, 'error': 'Invoice created but could not read details'}
            
        except Exception as e:
            logger.error(f"Failed to create invoice: {e}")
            return {'success': False, 'error': str(e)}
    
    def _find_or_create_partner(self, name: str, email: str = '') -> int:
        """Find existing partner or create new one."""
        # Search for existing partner
        if email:
            partners = self.odoo.search_read(
                'res.partner',
                domain=[['email', '=', email]],
                fields=['id', 'name'],
                limit=1
            )
            if partners:
                return partners[0]['id']
        
        # Search by name
        if name:
            partners = self.odoo.search_read(
                'res.partner',
                domain=[['name', 'ilike', name]],
                fields=['id', 'name'],
                limit=1
            )
            if partners:
                return partners[0]['id']
        
        # Create new partner
        partner_data = {'name': name}
        if email:
            partner_data['email'] = email
        
        return self.odoo.execute('res.partner', 'create', args=[partner_data])
    
    def _get_sales_journal(self) -> int:
        """Get sales journal ID."""
        journals = self.odoo.search_read(
            'account.journal',
            domain=[['type', '=', 'sale']],
            fields=['id', 'name'],
            limit=1
        )
        
        if journals:
            return journals[0]['id']
        
        # Fallback to any journal
        journals = self.odoo.search_read('account.journal', domain=[], fields=['id'], limit=1)
        return journals[0]['id'] if journals else 1
    
    def read_transactions(self, date_from: Optional[str] = None, 
                          date_to: Optional[str] = None,
                          limit: int = 50) -> Dict:
        """Read account transactions from Odoo."""
        if not self.odoo or not self.odoo.connected:
            # Demo mode
            logger.info("[DEMO] Would fetch transactions")
            return {
                'success': True,
                'transactions': [
                    {'id': 'DEMO-001', 'name': 'Demo Invoice', 'date': datetime.now().strftime('%Y-%m-%d'), 
                     'type': 'out_invoice', 'amount': 1000.00, 'state': 'posted'},
                    {'id': 'DEMO-002', 'name': 'Demo Bill', 'date': datetime.now().strftime('%Y-%m-%d'),
                     'type': 'in_invoice', 'amount': 500.00, 'state': 'posted'}
                ],
                'demo_mode': True
            }
        
        try:
            domain = [['state', '=', 'posted']]
            
            if date_from:
                domain.append(['date', '>=', date_from])
            if date_to:
                domain.append(['date', '<=', date_to])
            
            transactions = self.odoo.search_read(
                'account.move',
                domain=domain,
                fields=['id', 'name', 'date', 'move_type', 'amount_total', 'state', 'partner_id'],
                limit=limit
            )
            
            # Format transactions
            formatted = []
            for t in transactions:
                formatted.append({
                    'id': t['id'],
                    'name': t['name'],
                    'date': t['date'],
                    'type': t['move_type'],
                    'amount': t['amount_total'],
                    'state': t['state'],
                    'partner': t['partner_id'][1] if t.get('partner_id') else ''
                })
            
            return {
                'success': True,
                'transactions': formatted,
                'count': len(formatted)
            }
            
        except Exception as e:
            logger.error(f"Failed to read transactions: {e}")
            return {'success': False, 'error': str(e)}
    
    def fetch_balances(self) -> Dict:
        """Fetch account balances from Odoo."""
        if not self.odoo or not self.odoo.connected:
            # Demo mode
            return {
                'success': True,
                'balances': {
                    'accounts_receivable': 5000.00,
                    'accounts_payable': 2500.00,
                    'bank': 10000.00,
                    'net': 12500.00
                },
                'demo_mode': True
            }
        
        try:
            # Get account types
            balances = {}
            
            # Accounts Receivable
            ar_accounts = self.odoo.search_read(
                'account.account',
                domain=[['account_type', '=', 'asset_receivable']],
                fields=['id', 'name', 'balance']
            )
            balances['accounts_receivable'] = sum(a.get('balance', 0) for a in ar_accounts)
            
            # Accounts Payable
            ap_accounts = self.odoo.search_read(
                'account.account',
                domain=[['account_type', '=', 'liability_payable']],
                fields=['id', 'name', 'balance']
            )
            balances['accounts_payable'] = sum(a.get('balance', 0) for a in ap_accounts)
            
            # Bank accounts
            bank_accounts = self.odoo.search_read(
                'account.account',
                domain=[['account_type', '=', 'asset_cash']],
                fields=['id', 'name', 'balance']
            )
            balances['bank'] = sum(a.get('balance', 0) for a in bank_accounts)
            
            # Net calculation
            balances['net'] = balances['bank'] + balances['accounts_receivable'] - balances['accounts_payable']
            
            return {
                'success': True,
                'balances': balances
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch balances: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_weekly_summary(self) -> Dict:
        """Generate weekly financial summary."""
        try:
            # Calculate date range
            today = datetime.now()
            week_start = today - timedelta(days=today.weekday())
            week_end = week_start + timedelta(days=6)
            
            # Fetch transactions for the week
            transactions_result = self.read_transactions(
                date_from=week_start.strftime('%Y-%m-%d'),
                date_to=week_end.strftime('%Y-%m-%d'),
                limit=200
            )
            
            if not transactions_result.get('success'):
                return transactions_result
            
            transactions = transactions_result.get('transactions', [])
            
            # Calculate totals
            total_income = sum(t['amount'] for t in transactions if t['type'] == 'out_invoice')
            total_expenses = sum(t['amount'] for t in transactions if t['type'] == 'in_invoice')
            net_income = total_income - total_expenses
            
            # Fetch balances
            balances_result = self.fetch_balances()
            balances = balances_result.get('balances', {})
            
            # Generate summary markdown
            summary_md = self._create_summary_markdown(
                week_start=week_start,
                week_end=week_end,
                total_income=total_income,
                total_expenses=total_expenses,
                net_income=net_income,
                transactions=transactions,
                balances=balances
            )
            
            # Save summary
            summary_file = self.accounting_dir / f"weekly_financial_summary_{week_start.strftime('%Y%m%d')}.md"
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary_md)
            
            logger.info(f"Weekly summary saved: {summary_file.name}")
            
            return {
                'success': True,
                'summary_file': str(summary_file),
                'period': f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}",
                'total_income': total_income,
                'total_expenses': total_expenses,
                'net_income': net_income
            }
            
        except Exception as e:
            logger.error(f"Failed to generate weekly summary: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_summary_markdown(self, week_start: datetime, week_end: datetime,
                                  total_income: float, total_expenses: float,
                                  net_income: float, transactions: List[Dict],
                                  balances: Dict) -> str:
        """Create weekly summary markdown content."""
        week_number = week_start.isocalendar()[1]
        
        # Separate invoices and bills
        invoices = [t for t in transactions if t['type'] == 'out_invoice']
        bills = [t for t in transactions if t['type'] == 'in_invoice']
        
        content = f"""# Weekly Financial Summary

**Week:** {week_number}, {week_start.year}
**Period:** {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}

---

## Summary

| Metric | Amount |
|--------|--------|
| Total Income | ${total_income:,.2f} |
| Total Expenses | ${total_expenses:,.2f} |
| **Net Income** | **${net_income:,.2f}** |

---

## Invoices Created

"""
        
        if invoices:
            content += "| Invoice | Customer | Amount | Status |\n"
            content += "|---------|----------|--------|--------|\n"
            for inv in invoices[:10]:  # Limit to 10
                content += f"| {inv['name']} | {inv.get('partner', 'N/A')} | ${inv['amount']:,.2f} | {inv['state']} |\n"
        else:
            content += "*No invoices this week*\n"
        
        content += "\n---\n\n## Bills Paid\n\n"
        
        if bills:
            content += "| Bill | Vendor | Amount | Status |\n"
            content += "|------|--------|--------|--------|\n"
            for bill in bills[:10]:  # Limit to 10
                content += f"| {bill['name']} | {bill.get('partner', 'N/A')} | ${bill['amount']:,.2f} | {bill['state']} |\n"
        else:
            content += "*No bills this week*\n"
        
        content += "\n---\n\n## Account Balances\n\n"
        
        if balances:
            content += "| Account | Balance |\n"
            content += "|---------|---------|\n"
            content += f"| Accounts Receivable | ${balances.get('accounts_receivable', 0):,.2f} |\n"
            content += f"| Accounts Payable | ${balances.get('accounts_payable', 0):,.2f} |\n"
            content += f"| Bank | ${balances.get('bank', 0):,.2f} |\n"
            content += f"| **Net** | **${balances.get('net', 0):,.2f}** |\n"
        else:
            content += "*Balance data not available*\n"
        
        content += f"""
---

## Notes

- Summary generated automatically by AI Employee Odoo Accounting Agent
- All amounts in USD
- Data sourced from Odoo ERP

---

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
        
        return content
    
    def execute(self, task_input: Dict) -> Dict:
        """Execute accounting task."""
        action = task_input.get('action', '')
        
        logger.info(f"Executing accounting action: {action}")
        
        # Connect to Odoo (or use demo mode)
        self.connect_to_odoo()
        
        if action == 'create_invoice':
            invoice_data = {
                'partner': task_input.get('customer', task_input.get('partner', '')),
                'amount': task_input.get('amount', 0),
                'description': task_input.get('description', 'Services'),
                'due_date': task_input.get('due_date'),
                'email': task_input.get('email', '')
            }
            return self.create_invoice(invoice_data)
        
        elif action == 'read_transactions':
            return self.read_transactions(
                date_from=task_input.get('date_from'),
                date_to=task_input.get('date_to'),
                limit=int(task_input.get('limit', 50))
            )
        
        elif action == 'fetch_balances':
            return self.fetch_balances()
        
        elif action == 'generate_summary' or action == 'weekly_summary':
            return self.generate_weekly_summary()
        
        else:
            # Default: try to determine action from content
            content = task_input.get('content', '')
            
            if 'invoice' in content.lower():
                # Extract invoice details from content
                amount_match = re.search(r'\$?([\d,]+\.?\d*)', content)
                amount = float(amount_match.group(1).replace(',', '')) if amount_match else 0
                
                return self.create_invoice({
                    'partner': task_input.get('title', 'Unknown Customer'),
                    'amount': amount,
                    'description': content[:200]
                })
            
            elif 'summary' in content.lower() or 'report' in content.lower():
                return self.generate_weekly_summary()
            
            elif 'balance' in content.lower():
                return self.fetch_balances()
            
            elif 'transaction' in content.lower() or 'transaction' in content.lower():
                return self.read_transactions()
            
            else:
                return {
                    'success': False,
                    'error': f'Unknown accounting action: {action}'
                }
    
    def scan_for_accounting_tasks(self) -> List[Path]:
        """Scan Needs_Action for accounting tasks."""
        tasks = []
        
        if not self.needs_action_dir.exists():
            return tasks
        
        for file_path in self.needs_action_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.md':
                if file_path.name in self.processed_tasks:
                    continue
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for accounting task indicators
                is_accounting = (
                    'skill: odoo_accounting' in content.lower() or
                    'skill:accounting' in content.lower() or
                    ('invoice' in content.lower() and 'create' in content.lower()) or
                    ('financial' in content.lower() and 'summary' in content.lower()) or
                    ('balance' in content.lower())
                )
                
                if is_accounting:
                    tasks.append(file_path)
        
        return tasks
    
    def update_task_file(self, task_file: Path, result: Dict):
        """Update task file with execution result."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if result.get('success'):
                # Add success section
                if 'invoice' in result:
                    inv = result['invoice']
                    result_md = f"""
---

## Invoice Created

**Status:** ✅ Created
**Invoice:** {inv.get('name', 'N/A')}
**Customer:** {inv.get('partner', 'N/A')}
**Amount:** ${inv.get('amount_total', 0):,.2f}
**Due Date:** {inv.get('due_date', 'N/A')}
**Demo Mode:** {inv.get('demo_mode', False)}
"""
                elif 'summary_file' in result:
                    result_md = f"""
---

## Summary Generated

**Status:** ✅ Generated
**File:** {result.get('summary_file', 'N/A')}
**Period:** {result.get('period', 'N/A')}
**Net Income:** ${result.get('net_income', 0):,.2f}
"""
                else:
                    result_md = f"""
---

## Task Completed

**Status:** ✅ Success
**Time:** {timestamp}
**Result:** {json.dumps(result, indent=2)}
"""
                
                # Update status
                content = re.sub(r'(status:\s*)[^\n]+', r'\1done', content, flags=re.MULTILINE)
                if 'completed:' not in content:
                    content = re.sub(r'(status:\s*done)', f'\\1\ncompleted: {timestamp}', content)
            else:
                result_md = f"""
---

## Task Failed

**Status:** ❌ Failed
**Error:** {result.get('error', 'Unknown error')}
"""
            
            new_content = content + result_md
            
            with open(task_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"Task file updated: {task_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to update task file: {e}")
    
    def run(self):
        """Main accounting agent loop."""
        logger.info("=" * 60)
        logger.info("Odoo Accounting Agent started")
        logger.info(f"Odoo Host: {self.config['host'] if self.config else 'Not configured'}:{self.config['port'] if self.config else 'N/A'}")
        logger.info(f"Accounting Logs: {self.accounting_dir}")
        logger.info("=" * 60)
        
        # Test connection
        if self.connect_to_odoo():
            logger.info("Connected to Odoo successfully")
        else:
            logger.warning("Running in demo mode - no live Odoo connection")
        
        while True:
            try:
                tasks = self.scan_for_accounting_tasks()
                
                if tasks:
                    logger.info(f"Found {len(tasks)} accounting task(s)")
                    
                    for task_file in tasks:
                        logger.info(f"Processing: {task_file.name}")
                        
                        content, frontmatter = self.read_task(task_file)
                        
                        result = self.execute({
                            'action': frontmatter.get('action', ''),
                            'title': frontmatter.get('title', ''),
                            'customer': frontmatter.get('customer', frontmatter.get('to', '')),
                            'amount': frontmatter.get('amount', 0),
                            'description': content[:500],
                            'content': content,
                            'due_date': frontmatter.get('due_date')
                        })
                        
                        self.update_task_file(task_file, result)
                        self.processed_tasks.add(task_file.name)
                    
                    logger.info("Waiting for more tasks...")
                
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("")
                logger.info("Odoo Accounting Agent stopping...")
                break
            except Exception as e:
                logger.error(f"Error in accounting agent loop: {e}")
                time.sleep(5)


# Import time for the run loop
import time

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    VAULT_PATH = BASE_DIR / "notes"
    agent = OdooAccountingAgent(
        needs_action_dir=VAULT_PATH / "Needs_Action",
        logs_dir=BASE_DIR / "Logs"
    )
    agent.run()
