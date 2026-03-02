#!/usr/bin/env python3
"""
Odoo Cloud Agent - PLATINUM Tier

Integrates with Odoo Community Edition on Cloud VM for accounting operations.

Capabilities:
- Draft invoices (Cloud can create)
- Read balances (Cloud can read)
- Generate reports (Cloud can generate)

Restrictions:
- Cloud creates drafts ONLY
- Invoice posting requires Local approval
- Uses MCP accounting server for all operations

Zone Enforcement:
- CLOUD: create_draft_invoice, read_balance, generate_report
- LOCAL: post_invoice, approve_invoice, finalize_accounting
"""

import os
import sys
import json
import logging
import threading
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import xmlrpc.client

# Import zone policy validator
sys.path.insert(0, str(Path(__file__).parent))
from zone_policy_validator import ZonePolicyValidator, ZoneViolationError, EnforcementLevel

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.parent.resolve()
VAULT_PATH = BASE_DIR / "notes"
CLOUD_RUNTIME_DIR = Path(__file__).parent.resolve()
LOGS_DIR = BASE_DIR / "Logs"
DRAFTS_DIR = VAULT_PATH / "Drafts"
APPROVAL_REQUESTS_DIR = VAULT_PATH / "Approval_Requests"

# Odoo Configuration
ODOO_CONFIG_FILE = CLOUD_RUNTIME_DIR / "odoo_config.json"

# MCP Accounting Server
MCP_ACCOUNTING_HOST = "127.0.0.1"
MCP_ACCOUNTING_PORT = 8767

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to both file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"odoo_cloud_agent_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("OdooCloudAgent")


logger = setup_logging()


# =============================================================================
# Enums and Data Classes
# =============================================================================

class InvoiceStatus(Enum):
    """Odoo invoice status."""
    DRAFT = "draft"
    POSTED = "posted"
    CANCEL = "cancel"


class ReportType(Enum):
    """Accounting report types."""
    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    AGED_RECEIVABLE = "aged_receivable"
    AGED_PAYABLE = "aged_payable"
    TRIAL_BALANCE = "trial_balance"
    GENERAL_LEDGER = "general_ledger"


@dataclass
class OdooInvoice:
    """Represents an Odoo invoice."""
    invoice_id: Optional[int]
    move_type: str  # 'out_invoice', 'in_invoice', 'out_refund', 'in_refund'
    partner_id: int
    partner_name: str
    invoice_date: str
    due_date: str
    amount_total: float
    amount_untaxed: float
    amount_tax: float
    currency: str = "USD"
    status: InvoiceStatus = InvoiceStatus.DRAFT
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    narration: str = ""
    draft_file: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'invoice_id': self.invoice_id,
            'move_type': self.move_type,
            'partner_id': self.partner_id,
            'partner_name': self.partner_name,
            'invoice_date': self.invoice_date,
            'due_date': self.due_date,
            'amount_total': self.amount_total,
            'amount_untaxed': self.amount_untaxed,
            'amount_tax': self.amount_tax,
            'currency': self.currency,
            'status': self.status.value,
            'line_items': self.line_items,
            'narration': self.narration,
        }


@dataclass
class AccountBalance:
    """Represents an account balance."""
    account_code: str
    account_name: str
    balance: float
    credit: float
    debit: float
    currency: str = "USD"
    date: str = ""


@dataclass
class AccountingReport:
    """Represents an accounting report."""
    report_id: str
    report_type: ReportType
    generated_at: datetime
    period_start: str
    period_end: str
    data: Dict[str, Any]
    summary: str = ""


# =============================================================================
# Odoo Connection Manager
# =============================================================================

class OdooConnectionManager:
    """
    Manages connection to Odoo Community server via XML-RPC.
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.url = config.get('url', 'http://localhost:8069')
        self.db = config.get('database', 'odoo')
        self.username = config.get('username', 'admin')
        self.password = config.get('password', '')
        self.uid = None
        self.connected = False
        
    def connect(self) -> bool:
        """Establish connection to Odoo server."""
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.password)
            
            if self.uid:
                self.connected = True
                logger.info(f"Connected to Odoo: {self.url}/{self.db} as {self.username}")
                return True
            else:
                logger.error("Odoo authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to Odoo: {e}")
            return False
    
    def execute(self, model: str, method: str, *args, **kwargs) -> Any:
        """Execute a method on an Odoo model."""
        if not self.connected:
            raise ConnectionError("Not connected to Odoo server")
        
        try:
            objects = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            return objects.execute_kw(
                self.db, self.uid, self.password,
                model, method, *args, **kwargs
            )
        except Exception as e:
            logger.error(f"Odoo execute error ({model}.{method}): {e}")
            raise
    
    def search_read(self, model: str, domain: List, fields: Optional[List[str]] = None, 
                    limit: int = 80, offset: int = 0) -> List[Dict]:
        """Search and read records from Odoo."""
        return self.execute(model, 'search_read', [domain], fields=fields, 
                           limit=limit, offset=offset)
    
    def create_record(self, model: str, values: Dict) -> int:
        """Create a record in Odoo."""
        return self.execute(model, 'create', [values])
    
    def write_record(self, model: str, record_id: int, values: Dict) -> bool:
        """Update a record in Odoo."""
        return self.execute(model, 'write', [record_id, values])
    
    def action_post(self, model: str, record_ids: List[int]) -> bool:
        """Post accounting records (requires approval)."""
        return self.execute(model, 'action_post', [record_ids])


# =============================================================================
# MCP Accounting Client
# =============================================================================

class MCPAccountingClient:
    """
    Client for MCP Accounting Server.
    Provides standardized interface for accounting operations.
    """
    
    def __init__(self, host: str = MCP_ACCOUNTING_HOST, port: int = MCP_ACCOUNTING_PORT):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.connected = False
    
    def connect(self) -> bool:
        """Connect to MCP accounting server."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            self.connected = response.status_code == 200
            return self.connected
        except Exception as e:
            logger.warning(f"MCP Accounting server not available: {e}")
            return False
    
    def create_draft_invoice(self, invoice: OdooInvoice) -> Dict[str, Any]:
        """Create draft invoice via MCP server."""
        payload = {
            'action': 'invoice/create',
            'params': invoice.to_dict()
        }
        
        response = requests.post(f"{self.base_url}/rpc", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    
    def get_account_balance(self, account_code: str, date: Optional[str] = None) -> AccountBalance:
        """Get account balance via MCP server."""
        payload = {
            'action': 'balance/get',
            'params': {
                'account_code': account_code,
                'date': date or datetime.now().strftime('%Y-%m-%d')
            }
        }
        
        response = requests.post(f"{self.base_url}/rpc", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        return AccountBalance(
            account_code=data.get('account_code', ''),
            account_name=data.get('account_name', ''),
            balance=data.get('balance', 0.0),
            credit=data.get('credit', 0.0),
            debit=data.get('debit', 0.0),
            currency=data.get('currency', 'USD'),
            date=data.get('date', '')
        )
    
    def generate_report(self, report_type: str, period_start: str, 
                       period_end: str) -> AccountingReport:
        """Generate accounting report via MCP server."""
        payload = {
            'action': 'reports/generate',
            'params': {
                'report_type': report_type,
                'period_start': period_start,
                'period_end': period_end
            }
        }
        
        response = requests.post(f"{self.base_url}/rpc", json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        return AccountingReport(
            report_id=data.get('report_id', ''),
            report_type=ReportType(report_type),
            generated_at=datetime.now(),
            period_start=period_start,
            period_end=period_end,
            data=data.get('data', {}),
            summary=data.get('summary', '')
        )
    
    def request_invoice_posting(self, invoice_id: int, draft_file: str) -> Dict[str, Any]:
        """Request invoice posting (requires local approval)."""
        payload = {
            'action': 'invoice/request_post',
            'params': {
                'invoice_id': invoice_id,
                'draft_file': draft_file
            }
        }
        
        response = requests.post(f"{self.base_url}/rpc", json=payload, timeout=30)
        response.raise_for_status()
        return response.json()


# =============================================================================
# Odoo Cloud Agent
# =============================================================================

class OdooCloudAgent:
    """
    Odoo Cloud Agent for PLATINUM Tier.
    
    CLOUD CAPABILITIES (Allowed):
    - create_draft_invoice() - Create draft invoices
    - read_balance() - Read account balances
    - generate_report() - Generate accounting reports
    - list_partners() - List business partners
    - list_products() - List products/services
    
    LOCAL CAPABILITIES (Requires Approval):
    - post_invoice() - Post draft invoices
    - approve_and_post() - Approve and post invoices
    - cancel_invoice() - Cancel posted invoices
    - finalize_accounting() - Finalize accounting periods
    """
    
    def __init__(self):
        # Zone policy validator with HARD enforcement
        self.zone_validator = ZonePolicyValidator(EnforcementLevel.HARD)
        self.zone = "cloud"
        
        # Connection managers
        self.odoo: Optional[OdooConnectionManager] = None
        self.mcp_client: Optional[MCPAccountingClient] = None
        
        # Configuration
        self.config = self._load_config()
        
        # Statistics
        self.stats = {
            'drafts_created': 0,
            'balances_read': 0,
            'reports_generated': 0,
            'posting_requests': 0,
            'zone_violations_blocked': 0,
        }
        self.lock = threading.Lock()
        
        logger.info("OdooCloudAgent initialized (CLOUD zone)")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load Odoo configuration."""
        default_config = {
            'url': 'http://localhost:8069',
            'database': 'odoo',
            'username': 'admin',
            'password': '',
            'company_id': 1,
        }
        
        if ODOO_CONFIG_FILE.exists():
            try:
                with open(ODOO_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                return {**default_config, **config}
            except Exception as e:
                logger.warning(f"Failed to load Odoo config: {e}")
        
        return default_config
    
    def connect(self) -> bool:
        """Connect to Odoo and MCP servers."""
        # Connect to Odoo
        self.odoo = OdooConnectionManager(self.config)
        odoo_connected = self.odoo.connect()
        
        # Connect to MCP Accounting
        self.mcp_client = MCPAccountingClient()
        mcp_connected = self.mcp_client.connect()
        
        if odoo_connected or mcp_connected:
            logger.info("OdooCloudAgent connected successfully")
            return True
        else:
            logger.warning("No accounting backend available")
            return False
    
    # =========================================================================
    # CLOUD-ALLOWED OPERATIONS
    # =========================================================================
    
    def create_draft_invoice(self, partner_id: int, partner_name: str,
                             line_items: List[Dict[str, Any]], 
                             invoice_date: Optional[str] = None,
                             due_date: Optional[str] = None,
                             narration: str = "") -> Tuple[bool, str]:
        """
        Create a draft invoice (CLOUD ALLOWED).
        
        Args:
            partner_id: Odoo partner ID
            partner_name: Partner name
            line_items: List of invoice lines
            invoice_date: Invoice date (default: today)
            due_date: Due date
            narration: Additional notes
            
        Returns:
            Tuple of (success, message)
        """
        # ZONE ENFORCEMENT: Validate this action is allowed in cloud
        try:
            self.zone_validator.validate_action('cloud', 'create_draft_invoice')
        except ZoneViolationError:
            with self.lock:
                self.stats['zone_violations_blocked'] += 1
            raise
        
        logger.info(f"Creating draft invoice for {partner_name}")
        
        # Calculate amounts
        amount_untaxed = sum(item.get('price_subtotal', 0) for item in line_items)
        amount_tax = sum(item.get('price_tax', 0) for item in line_items)
        amount_total = amount_untaxed + amount_tax
        
        # Create invoice object
        invoice = OdooInvoice(
            invoice_id=None,  # Will be assigned by Odoo
            move_type='out_invoice',
            partner_id=partner_id,
            partner_name=partner_name,
            invoice_date=invoice_date or datetime.now().strftime('%Y-%m-%d'),
            due_date=due_date or invoice_date or datetime.now().strftime('%Y-%m-%d'),
            amount_total=amount_total,
            amount_untaxed=amount_untaxed,
            amount_tax=amount_tax,
            line_items=line_items,
            narration=narration,
            status=InvoiceStatus.DRAFT,
        )
        
        # Create via MCP or directly via Odoo
        invoice_id = None
        try:
            if self.mcp_client and self.mcp_client.connected:
                result = self.mcp_client.create_draft_invoice(invoice)
                invoice_id = result.get('invoice_id')
            elif self.odoo and self.odoo.connected:
                invoice_values = {
                    'move_type': 'out_invoice',
                    'partner_id': partner_id,
                    'invoice_date': invoice.invoice_date,
                    'invoice_date_due': invoice.due_date,
                    'narration': narration,
                    'invoice_line_ids': [(0, 0, item) for item in line_items],
                }
                invoice_id = self.odoo.create_record('account.move', invoice_values)
        except Exception as e:
            logger.error(f"Failed to create draft invoice: {e}")
            return False, f"Failed to create draft invoice: {e}"
        
        if invoice_id:
            invoice.invoice_id = invoice_id
            
            # Save draft to file
            draft_file = self._save_invoice_draft(invoice)
            invoice.draft_file = draft_file
            
            # Create approval request for posting
            approval_request = self._create_posting_approval_request(invoice)
            
            with self.lock:
                self.stats['drafts_created'] += 1
            
            logger.info(f"Draft invoice created: ID={invoice_id}, Draft={draft_file}")
            return True, f"Draft invoice created: {invoice_id}. Approval request: {approval_request}"
        else:
            return False, "Failed to create draft invoice"
    
    def read_balance(self, account_code: str, 
                     date: Optional[str] = None) -> Optional[AccountBalance]:
        """
        Read account balance (CLOUD ALLOWED).
        
        Args:
            account_code: Account code (e.g., '1100' for Cash)
            date: Balance date (default: today)
            
        Returns:
            AccountBalance or None
        """
        # ZONE ENFORCEMENT: Validate this action is allowed in cloud
        try:
            self.zone_validator.validate_action('cloud', 'read_balance')
        except ZoneViolationError:
            with self.lock:
                self.stats['zone_violations_blocked'] += 1
            raise
        
        logger.info(f"Reading balance for account {account_code}")
        
        try:
            if self.mcp_client and self.mcp_client.connected:
                balance = self.mcp_client.get_account_balance(account_code, date)
            elif self.odoo and self.odoo.connected:
                # Search for account
                accounts = self.odoo.search_read(
                    'account.account',
                    [['code', '=', account_code]],
                    fields=['id', 'name', 'code']
                )
                
                if not accounts:
                    logger.warning(f"Account not found: {account_code}")
                    return None
                
                account_id = accounts[0]['id']
                
                # Get balance from trial balance
                domain = [
                    ('account_id', '=', account_id),
                    ('date', '<=', date or datetime.now().strftime('%Y-%m-%d'))
                ]
                
                move_lines = self.odoo.search_read(
                    'account.move.line',
                    domain,
                    fields=['debit', 'credit', 'balance']
                )
                
                debit = sum(line.get('debit', 0) for line in move_lines)
                credit = sum(line.get('credit', 0) for line in move_lines)
                balance = sum(line.get('balance', 0) for line in move_lines)
                
                balance = AccountBalance(
                    account_code=account_code,
                    account_name=accounts[0]['name'],
                    balance=balance,
                    debit=debit,
                    credit=credit,
                    date=date or datetime.now().strftime('%Y-%m-%d')
                )
            else:
                logger.warning("No accounting backend connected")
                return None
            
            with self.lock:
                self.stats['balances_read'] += 1
            
            return balance
            
        except Exception as e:
            logger.error(f"Failed to read balance: {e}")
            return None
    
    def generate_report(self, report_type: ReportType, 
                       period_start: str, 
                       period_end: str) -> Optional[AccountingReport]:
        """
        Generate accounting report (CLOUD ALLOWED).
        
        Args:
            report_type: Type of report
            period_start: Start date (YYYY-MM-DD)
            period_end: End date (YYYY-MM-DD)
            
        Returns:
            AccountingReport or None
        """
        # ZONE ENFORCEMENT: Validate this action is allowed in cloud
        try:
            self.zone_validator.validate_action('cloud', 'generate_report')
        except ZoneViolationError:
            with self.lock:
                self.stats['zone_violations_blocked'] += 1
            raise
        
        logger.info(f"Generating {report_type.value} report: {period_start} to {period_end}")
        
        try:
            if self.mcp_client and self.mcp_client.connected:
                report = self.mcp_client.generate_report(
                    report_type.value, period_start, period_end
                )
            elif self.odoo and self.odoo.connected:
                report = self._generate_report_odoo(report_type, period_start, period_end)
            else:
                logger.warning("No accounting backend connected")
                return None
            
            # Save report to file
            report_file = self._save_report(report)
            
            with self.lock:
                self.stats['reports_generated'] += 1
            
            logger.info(f"Report generated: {report_file}")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            return None
    
    def list_partners(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List business partners (CLOUD ALLOWED)."""
        try:
            self.zone_validator.validate_action('cloud', 'list_partners')
        except ZoneViolationError:
            with self.lock:
                self.stats['zone_violations_blocked'] += 1
            raise
        
        if not self.odoo or not self.odoo.connected:
            return []
        
        partners = self.odoo.search_read(
            'res.partner',
            [['customer', '=', True]],
            fields=['id', 'name', 'email', 'phone', 'vat'],
            limit=limit
        )
        
        return partners
    
    def list_products(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List products/services (CLOUD ALLOWED)."""
        try:
            self.zone_validator.validate_action('cloud', 'list_products')
        except ZoneViolationError:
            with self.lock:
                self.stats['zone_violations_blocked'] += 1
            raise
        
        if not self.odoo or not self.odoo.connected:
            return []
        
        products = self.odoo.search_read(
            'product.template',
            [['sale_ok', '=', True]],
            fields=['id', 'name', 'list_price', 'default_code'],
            limit=limit
        )
        
        return products
    
    # =========================================================================
    # LOCAL-ONLY OPERATIONS (BLOCKED IN CLOUD)
    # =========================================================================
    
    def post_invoice(self, invoice_id: int) -> Tuple[bool, str]:
        """
        Post an invoice (LOCAL ONLY - BLOCKED IN CLOUD).
        
        This method will ALWAYS fail when called from cloud zone.
        Invoice posting requires local approval.
        """
        # ZONE ENFORCEMENT: This will fail in cloud zone
        try:
            self.zone_validator.validate_action('cloud', 'post_invoice')
            # If we get here, zone enforcement is disabled
        except ZoneViolationError:
            with self.lock:
                self.stats['zone_violations_blocked'] += 1
            raise ZoneViolationError(
                "Invoice posting requires LOCAL approval. "
                "Cloud can only create drafts.",
                'cloud', 'post_invoice'
            )
        
        # This code only runs if zone enforcement is disabled
        if self.odoo and self.odoo.connected:
            try:
                self.odoo.action_post('account.move', [invoice_id])
                return True, f"Invoice {invoice_id} posted"
            except Exception as e:
                return False, f"Failed to post invoice: {e}"
        
        return False, "Not connected to Odoo"
    
    def approve_and_post(self, draft_file: str) -> Tuple[bool, str]:
        """
        Approve and post a draft invoice (LOCAL ONLY).
        
        This is the proper workflow for posting invoices:
        1. Cloud creates draft
        2. Local reviews and approves
        3. Local calls approve_and_post()
        """
        # ZONE ENFORCEMENT: This will fail in cloud zone
        try:
            self.zone_validator.validate_action('cloud', 'approve_and_post')
        except ZoneViolationError:
            with self.lock:
                self.stats['zone_violations_blocked'] += 1
            raise ZoneViolationError(
                "Invoice approval and posting is LOCAL zone only",
                'cloud', 'approve_and_post'
            )
        
        # Local implementation would:
        # 1. Read draft file
        # 2. Verify approval
        # 3. Post to Odoo
        # 4. Update status
        
        return False, "approve_and_post() requires LOCAL zone"
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _save_invoice_draft(self, invoice: OdooInvoice) -> str:
        """Save invoice draft to file."""
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
        
        draft_file = DRAFTS_DIR / f"invoice_draft_{invoice.invoice_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
        
        content = f"""---
draft_type: invoice
invoice_id: {invoice.invoice_id}
partner_id: {invoice.partner_id}
partner_name: {invoice.partner_name}
invoice_date: {invoice.invoice_date}
due_date: {invoice.due_date}
amount_total: {invoice.amount_total}
amount_untaxed: {invoice.amount_untaxed}
amount_tax: {invoice.amount_tax}
currency: {invoice.currency}
status: {invoice.status.value}
created_at: {datetime.now().isoformat()}
---

# Draft Invoice

**Partner:** {invoice.partner_name}  
**Date:** {invoice.invoice_date}  
**Due:** {invoice.due_date}

---

## Line Items

| Description | Quantity | Unit Price | Tax | Subtotal |
|-------------|----------|------------|-----|----------|
"""
        
        for item in invoice.line_items:
            content += f"| {item.get('name', '')} | {item.get('quantity', 1)} | {item.get('price_unit', 0)} | {item.get('price_tax', 0)} | {item.get('price_subtotal', 0)} |\n"
        
        content += f"""
---

## Totals

- **Subtotal:** {invoice.amount_untaxed} {invoice.currency}
- **Tax:** {invoice.amount_tax} {invoice.currency}
- **Total:** {invoice.amount_total} {invoice.currency}

---

## Notes

{invoice.narration or 'No additional notes.'}

---

## Approval Required

This is a DRAFT invoice. Posting requires LOCAL approval.

To approve and post:
1. Review the invoice details above
2. Verify amounts and line items
3. Call approve_and_post() from LOCAL zone

---
"""
        
        with open(draft_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(draft_file)
    
    def _create_posting_approval_request(self, invoice: OdooInvoice) -> str:
        """Create approval request for invoice posting."""
        APPROVAL_REQUESTS_DIR.mkdir(parents=True, exist_ok=True)
        
        request_id = f"invoice_post_{invoice.invoice_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        request_file = APPROVAL_REQUESTS_DIR / f"{request_id}.md"
        
        content = f"""---
request_id: {request_id}
request_type: invoice_posting
invoice_id: {invoice.invoice_id}
partner_name: {invoice.partner_name}
amount_total: {invoice.amount_total}
currency: {invoice.currency}
priority: normal
status: pending
created_at: {datetime.now().isoformat()}
---

# Invoice Posting Approval Request

## Invoice Details

- **Invoice ID:** {invoice.invoice_id}
- **Partner:** {invoice.partner_name}
- **Date:** {invoice.invoice_date}
- **Due:** {invoice.due_date}
- **Amount:** {invoice.amount_total} {invoice.currency}

## Draft File

{invoice.draft_file or 'N/A'}

---

## Approval Required

This invoice has been created as a DRAFT by the Cloud Agent.

**Posting requires LOCAL zone approval.**

### To Approve:
1. Review the draft invoice
2. Verify all amounts and line items
3. Change status below to APPROVED
4. The system will post the invoice to Odoo

### To Reject:
1. Add rejection reason below
2. Change status to REJECTED

---

## Response

**Status:** [PENDING]

**Approved By:** _______________

**Date:** _______________

**Comments:** _______________

---
*Cloud agents cannot post invoices. Local approval required.*
"""
        
        with open(request_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(request_file)
    
    def _generate_report_odoo(self, report_type: ReportType, 
                              period_start: str, period_end: str) -> AccountingReport:
        """Generate report using Odoo directly."""
        report_data = {}
        summary = ""
        
        if report_type == ReportType.BALANCE_SHEET:
            # Get asset and liability accounts
            assets = self.odoo.search_read(
                'account.account',
                [['account_type', '=', 'asset']],
                fields=['code', 'name']
            )
            liabilities = self.odoo.search_read(
                'account.account',
                [['account_type', '=', 'liability']],
                fields=['code', 'name']
            )
            
            report_data = {'assets': assets, 'liabilities': liabilities}
            summary = f"Balance Sheet: {len(assets)} asset accounts, {len(liabilities)} liability accounts"
            
        elif report_type == ReportType.INCOME_STATEMENT:
            # Get income and expense accounts
            income = self.odoo.search_read(
                'account.account',
                [['account_type', '=', 'income']],
                fields=['code', 'name']
            )
            expenses = self.odoo.search_read(
                'account.account',
                [['account_type', '=', 'expense']],
                fields=['code', 'name']
            )
            
            report_data = {'income': income, 'expenses': expenses}
            summary = f"Income Statement: {len(income)} income accounts, {len(expenses)} expense accounts"
        
        return AccountingReport(
            report_id=f"report_{report_type.value}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            report_type=report_type,
            generated_at=datetime.now(),
            period_start=period_start,
            period_end=period_end,
            data=report_data,
            summary=summary
        )
    
    def _save_report(self, report: AccountingReport) -> str:
        """Save report to file."""
        reports_dir = DRAFTS_DIR / "Reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        
        report_file = reports_dir / f"{report.report_id}.md"
        
        content = f"""---
report_id: {report.report_id}
report_type: {report.report_type.value}
generated_at: {report.generated_at.isoformat()}
period_start: {report.period_start}
period_end: {report.period_end}
---

# {report.report_type.value.replace('_', ' ').title()}

**Period:** {report.period_start} to {report.period_end}  
**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}

---

## Summary

{report.summary}

---

## Data

```json
{json.dumps(report.data, indent=2)}
```

---
*Generated by OdooCloudAgent (PLATINUM Tier)*
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return str(report_file)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        with self.lock:
            stats = self.stats.copy()
        
        stats['zone'] = self.zone
        stats['odoo_connected'] = self.odoo.connected if self.odoo else False
        stats['mcp_connected'] = self.mcp_client.connected if self.mcp_client else False
        
        return stats


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    """Main entry point for Odoo Cloud Agent."""
    print("=" * 60)
    print("Odoo Cloud Agent - PLATINUM Tier")
    print("=" * 60)
    print()
    print("Cloud Capabilities (Allowed):")
    print("  - create_draft_invoice() - Create draft invoices")
    print("  - read_balance() - Read account balances")
    print("  - generate_report() - Generate accounting reports")
    print("  - list_partners() - List business partners")
    print("  - list_products() - List products/services")
    print()
    print("Local Capabilities (Requires Approval):")
    print("  - post_invoice() - Post draft invoices")
    print("  - approve_and_post() - Approve and post invoices")
    print()
    print("Zone Enforcement: HARD")
    print("  Cloud CANNOT post invoices directly")
    print()
    print("=" * 60)

    agent = OdooCloudAgent()
    
    # Connect to backends
    if agent.connect():
        print("\n✅ Connected to accounting backend")
    else:
        print("\n⚠️  No accounting backend available (running in demo mode)")
    
    # Show stats
    stats = agent.get_stats()
    print(f"\nAgent Statistics:")
    print(f"  Zone: {stats['zone']}")
    print(f"  Drafts Created: {stats['drafts_created']}")
    print(f"  Balances Read: {stats['balances_read']}")
    print(f"  Reports Generated: {stats['reports_generated']}")
    print(f"  Violations Blocked: {stats['zone_violations_blocked']}")
    
    print("\nOdoo Cloud Agent ready. Press Ctrl+C to stop.")
    
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nOdoo Cloud Agent stopped.")


if __name__ == "__main__":
    main()
