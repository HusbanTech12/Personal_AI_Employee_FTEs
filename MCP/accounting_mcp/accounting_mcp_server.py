#!/usr/bin/env python3
"""
Accounting MCP Server - Financial Operations Service

Model Context Protocol (MCP) server for accounting and financial operations.
Provides HTTP API for agents to perform financial tasks.

Capabilities:
- Create invoice
- Track expenses
- Generate financial reports
- Budget management
- Payment tracking

Local-first HTTP server running on localhost.

Usage:
    python accounting_mcp_server.py

API Endpoints:
    POST /invoice/create    - Create new invoice
    POST /expense/add       - Add expense record
    GET  /reports/summary   - Get financial summary
    GET  /budget/status     - Get budget status
    GET  /status            - Server status
    GET  /health            - Health check
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AccountingMCPServer")


class AccountingStore:
    """In-memory store for accounting data."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.invoices: Dict[str, Dict] = {}
        self.expenses: Dict[str, Dict] = {}
        self.budgets: Dict[str, Dict] = {}
        
        # Load existing data
        self._load_data()
    
    def _load_data(self):
        """Load data from files."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Load invoices
        invoices_file = self.data_dir / "invoices.json"
        if invoices_file.exists():
            try:
                with open(invoices_file, 'r') as f:
                    self.invoices = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load invoices: {e}")
        
        # Load expenses
        expenses_file = self.data_dir / "expenses.json"
        if expenses_file.exists():
            try:
                with open(expenses_file, 'r') as f:
                    self.expenses = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load expenses: {e}")
    
    def _save_data(self):
        """Save data to files."""
        try:
            with open(self.data_dir / "invoices.json", 'w') as f:
                json.dump(self.invoices, f, indent=2)
            with open(self.data_dir / "expenses.json", 'w') as f:
                json.dump(self.expenses, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
    
    def create_invoice(self, invoice_data: Dict) -> Dict:
        """Create a new invoice."""
        invoice_id = f"INV-{uuid.uuid4().hex[:8].upper()}"
        
        invoice = {
            'id': invoice_id,
            'created_at': datetime.now().isoformat(),
            'status': 'draft',
            'amount': 0,
            **invoice_data
        }
        
        self.invoices[invoice_id] = invoice
        self._save_data()
        
        logger.info(f"Created invoice: {invoice_id}")
        return invoice
    
    def add_expense(self, expense_data: Dict) -> Dict:
        """Add an expense record."""
        expense_id = f"EXP-{uuid.uuid4().hex[:8].upper()}"
        
        expense = {
            'id': expense_id,
            'created_at': datetime.now().isoformat(),
            'status': 'recorded',
            **expense_data
        }
        
        self.expenses[expense_id] = expense
        self._save_data()
        
        logger.info(f"Added expense: {expense_id}")
        return expense
    
    def get_financial_summary(self) -> Dict:
        """Get financial summary."""
        total_invoices = sum(
            inv.get('amount', 0) 
            for inv in self.invoices.values()
        )
        total_expenses = sum(
            exp.get('amount', 0) 
            for exp in self.expenses.values()
        )
        
        return {
            'total_invoices': len(self.invoices),
            'total_invoice_amount': total_invoices,
            'total_expenses': len(self.expenses),
            'total_expense_amount': total_expenses,
            'net': total_invoices - total_expenses,
            'timestamp': datetime.now().isoformat()
        }
    
    def get_budget_status(self, budget_id: str = 'default') -> Dict:
        """Get budget status."""
        budget = self.budgets.get(budget_id, {
            'id': budget_id,
            'total': 0,
            'spent': 0,
            'categories': {}
        })
        
        spent = sum(
            exp.get('amount', 0) 
            for exp in self.expenses.values()
        )
        
        return {
            'budget_id': budget_id,
            'total': budget.get('total', 0),
            'spent': spent,
            'remaining': budget.get('total', 0) - spent,
            'percentage_used': round((spent / budget.get('total', 1)) * 100, 2) if budget.get('total') else 0
        }


class AccountingMCPServer:
    """
    Accounting MCP Server - Handles financial operations for AI agents.
    """
    
    HOST = os.getenv("ACCOUNTING_MCP_HOST", "127.0.0.1")
    PORT = int(os.getenv("ACCOUNTING_MCP_PORT", "8767"))
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.store = AccountingStore(data_dir)
        self.server: Optional[HTTPServer] = None
        self.running = False
    
    def create_invoice(self, data: Dict) -> Dict:
        """Create invoice action."""
        required = ['to', 'amount', 'description']
        for field in required:
            if field not in data:
                return {
                    'success': False,
                    'error': f'Missing required field: {field}',
                    'required_fields': required
                }
        
        invoice = self.store.create_invoice({
            'to': data['to'],
            'amount': float(data['amount']),
            'description': data['description'],
            'due_date': data.get('due_date'),
            'items': data.get('items', [])
        })
        
        return {
            'success': True,
            'invoice': invoice,
            'message': f'Invoice {invoice["id"]} created'
        }
    
    def add_expense(self, data: Dict) -> Dict:
        """Add expense action."""
        required = ['amount', 'category', 'description']
        for field in required:
            if field not in data:
                return {
                    'success': False,
                    'error': f'Missing required field: {field}',
                    'required_fields': required
                }
        
        expense = self.store.add_expense({
            'amount': float(data['amount']),
            'category': data['category'],
            'description': data['description'],
            'vendor': data.get('vendor'),
            'date': data.get('date', datetime.now().strftime('%Y-%m-%d'))
        })
        
        return {
            'success': True,
            'expense': expense,
            'message': f'Expense {expense["id"]} recorded'
        }
    
    def get_summary(self) -> Dict:
        """Get financial summary."""
        return {
            'success': True,
            **self.store.get_financial_summary()
        }
    
    def get_budget_status(self, budget_id: str = 'default') -> Dict:
        """Get budget status."""
        return {
            'success': True,
            **self.store.get_budget_status(budget_id)
        }
    
    def get_status(self) -> Dict:
        """Get server status."""
        summary = self.store.get_financial_summary()
        
        return {
            'status': 'running' if self.running else 'stopped',
            'host': self.HOST,
            'port': self.PORT,
            'invoices_count': summary['total_invoices'],
            'expenses_count': summary['total_expenses'],
            'net': summary['net'],
            'timestamp': datetime.now().isoformat()
        }


# Global server instance
accounting_server: Optional[AccountingMCPServer] = None


class MCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Accounting MCP."""
    
    def log_message(self, format, *args):
        logger.debug(f"HTTP: {args[0]}")
    
    def send_json_response(self, data: Dict, status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/status':
            result = accounting_server.get_status()
            self.send_json_response(result)
        
        elif path == '/health':
            self.send_json_response({'status': 'healthy'})
        
        elif path == '/reports/summary':
            result = accounting_server.get_summary()
            self.send_json_response(result)
        
        elif path.startswith('/budget/status'):
            query = parse_qs(parsed.query)
            budget_id = query.get('id', ['default'])[0]
            result = accounting_server.get_budget_status(budget_id)
            self.send_json_response(result)
        
        else:
            self.send_json_response({
                'error': 'Not found',
                'endpoints': [
                    'GET /status',
                    'GET /health',
                    'GET /reports/summary',
                    'GET /budget/status'
                ]
            }, 404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/invoice/create':
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({'success': False, 'error': 'Invalid JSON'}, 400)
                return
            
            result = accounting_server.create_invoice(data)
            status = 200 if result.get('success') else 400
            self.send_json_response(result, status)
        
        elif path == '/expense/add':
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({'success': False, 'error': 'Invalid JSON'}, 400)
                return
            
            result = accounting_server.add_expense(data)
            status = 200 if result.get('success') else 400
            self.send_json_response(result, status)
        
        else:
            self.send_json_response({
                'error': 'Not found',
                'endpoints': [
                    'POST /invoice/create',
                    'POST /expense/add'
                ]
            }, 404)


def run_server(server_instance: AccountingMCPServer):
    """Run the MCP server."""
    global accounting_server
    accounting_server = server_instance
    
    server_address = (server_instance.HOST, server_instance.PORT)
    httpd = HTTPServer(server_address, MCPRequestHandler)
    
    server_instance.server = httpd
    server_instance.running = True
    
    logger.info("=" * 60)
    logger.info("Accounting MCP Server Started")
    logger.info("=" * 60)
    logger.info(f"Host: {server_instance.HOST}")
    logger.info(f"Port: {server_instance.PORT}")
    logger.info(f"Data Directory: {server_instance.data_dir}")
    logger.info("")
    logger.info("Actions:")
    logger.info("  POST /invoice/create  - Create new invoice")
    logger.info("  POST /expense/add     - Add expense record")
    logger.info("  GET  /reports/summary - Get financial summary")
    logger.info("  GET  /budget/status   - Get budget status")
    logger.info("  GET  /status          - Server status")
    logger.info("  GET  /health          - Health check")
    logger.info("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        httpd.shutdown()
        server_instance.running = False


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent.parent
    server = AccountingMCPServer(data_dir=BASE_DIR / "MCP" / "accounting_mcp" / "data")
    run_server(server)
