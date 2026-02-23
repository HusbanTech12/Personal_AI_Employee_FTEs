#!/usr/bin/env python3
"""
Email MCP Server - Local-First Email Service

Model Context Protocol (MCP) server for email operations.
Provides HTTP API for agents to send emails without direct SMTP access.

Capabilities:
- Send email
- Receive commands from agents
- Return success/failure status
- Queue emails for offline sending

Local-first HTTP server running on localhost.

Usage:
    python email_mcp_server.py

API Endpoints:
    POST /send          - Send an email
    GET  /status        - Server status
    GET  /queue         - View queued emails
    POST /flush         - Send queued emails
"""

import os
import sys
import json
import logging
import smtplib
import threading
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from urllib.parse import parse_qs
import queue

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("EmailMCPServer")


class EmailQueue:
    """Thread-safe email queue for offline sending."""
    
    def __init__(self):
        self._queue: List[Dict] = []
        self._lock = threading.Lock()
    
    def add(self, email_data: Dict):
        """Add email to queue."""
        with self._lock:
            email_data['queued_at'] = datetime.now().isoformat()
            email_data['status'] = 'queued'
            self._queue.append(email_data)
            logger.info(f"Email queued: {email_data.get('to', 'unknown')}")
    
    def get_all(self) -> List[Dict]:
        """Get all queued emails."""
        with self._lock:
            return list(self._queue)
    
    def clear(self):
        """Clear all queued emails."""
        with self._lock:
            self._queue.clear()
    
    def mark_sent(self, index: int):
        """Mark email as sent."""
        with self._lock:
            if 0 <= index < len(self._queue):
                self._queue[index]['status'] = 'sent'
                self._queue[index]['sent_at'] = datetime.now().isoformat()
    
    def mark_failed(self, index: int, error: str):
        """Mark email as failed."""
        with self._lock:
            if 0 <= index < len(self._queue):
                self._queue[index]['status'] = 'failed'
                self._queue[index]['error'] = error


class EmailMCPServer:
    """
    Email MCP Server - Handles email operations for AI agents.
    
    Provides a local HTTP API for sending emails without exposing
    SMTP credentials to individual agents.
    """
    
    # Server configuration
    HOST = os.getenv("EMAIL_MCP_HOST", "127.0.0.1")
    PORT = int(os.getenv("EMAIL_MCP_PORT", "8765"))
    
    # SMTP configuration (set via environment or config file)
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    FROM_EMAIL = os.getenv("FROM_EMAIL", "")
    
    def __init__(self, logs_dir: Path):
        self.logs_dir = logs_dir
        self.email_queue = EmailQueue()
        self.server: Optional[HTTPServer] = None
        self.running = False
        
        # Ensure logs directory exists
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def send_email_smtp(self, to: str, subject: str, body: str, 
                        html: bool = False, cc: Optional[str] = None,
                        bcc: Optional[str] = None) -> Dict[str, Any]:
        """
        Send email via SMTP.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            html: Whether body is HTML
            cc: CC recipients (comma-separated)
            bcc: BCC recipients (comma-separated)
        
        Returns:
            Dict with success status and message
        """
        try:
            # Check if SMTP is configured
            if not self.SMTP_USER or not self.SMTP_PASSWORD:
                # Demo mode - simulate sending
                logger.info(f"[DEMO MODE] Would send email to: {to}")
                logger.info(f"  Subject: {subject}")
                logger.info(f"  Body: {body[:100]}...")
                
                return {
                    'success': True,
                    'message': 'Email sent (demo mode)',
                    'demo': True,
                    'to': to,
                    'subject': subject,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.FROM_EMAIL or self.SMTP_USER
            msg['To'] = to
            
            if cc:
                msg['Cc'] = cc
            
            # Attach body
            content_type = 'html' if html else 'plain'
            msg.attach(MIMEText(body, content_type))
            
            # Build recipient list
            recipients = [to]
            if cc:
                recipients.extend([r.strip() for r in cc.split(',')])
            if bcc:
                recipients.extend([r.strip() for r in bcc.split(',')])
            
            # Send email
            with smtplib.SMTP(self.SMTP_SERVER, self.SMTP_PORT) as server:
                server.starttls()
                server.login(self.SMTP_USER, self.SMTP_PASSWORD)
                server.sendmail(self.FROM_EMAIL or self.SMTP_USER, recipients, msg.as_string())
            
            logger.info(f"Email sent successfully to: {to}")
            
            return {
                'success': True,
                'message': 'Email sent successfully',
                'to': to,
                'subject': subject,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                'success': False,
                'message': str(e),
                'to': to,
                'subject': subject,
                'timestamp': datetime.now().isoformat()
            }
    
    def handle_send_request(self, data: Dict) -> Dict:
        """Handle email send request from agent."""
        # Validate required fields
        required = ['to', 'subject', 'body']
        for field in required:
            if field not in data:
                return {
                    'success': False,
                    'error': f'Missing required field: {field}',
                    'required_fields': required
                }
        
        # Extract fields
        to = data.get('to', '')
        subject = data.get('subject', '')
        body = data.get('body', '')
        html = data.get('html', False)
        cc = data.get('cc')
        bcc = data.get('bcc')
        priority = data.get('priority', 'normal')
        agent_id = data.get('agent_id', 'unknown')
        
        logger.info(f"Email request from agent: {agent_id}")
        logger.info(f"  To: {to}")
        logger.info(f"  Subject: {subject}")
        logger.info(f"  Priority: {priority}")
        
        # Send email
        result = self.send_email_smtp(to, subject, body, html, cc, bcc)
        
        # Add agent metadata
        result['agent_id'] = agent_id
        result['priority'] = priority
        
        return result
    
    def get_status(self) -> Dict:
        """Get server status."""
        queued_emails = self.email_queue.get_all()
        
        return {
            'status': 'running' if self.running else 'stopped',
            'host': self.HOST,
            'port': self.PORT,
            'smtp_configured': bool(self.SMTP_USER and self.SMTP_PASSWORD),
            'demo_mode': not (self.SMTP_USER and self.SMTP_PASSWORD),
            'queued_emails': len(queued_emails),
            'from_email': self.FROM_EMAIL or self.SMTP_USER,
            'timestamp': datetime.now().isoformat()
        }


# Global server instance for request handler
email_server: Optional[EmailMCPServer] = None


class MCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MCP server."""
    
    def log_message(self, format, *args):
        """Override to use our logger."""
        logger.debug(f"HTTP: {args[0]}")
    
    def send_json_response(self, data: Dict, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/status':
            result = email_server.get_status()
            self.send_json_response(result)
        
        elif self.path == '/queue':
            queued = email_server.email_queue.get_all()
            self.send_json_response({
                'queued_emails': queued,
                'count': len(queued)
            })
        
        elif self.path == '/health':
            self.send_json_response({'status': 'healthy'})
        
        else:
            self.send_json_response({
                'error': 'Not found',
                'endpoints': ['/status', '/queue', '/health']
            }, 404)
    
    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        
        if self.path == '/send':
            # Read request body
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({
                    'success': False,
                    'error': 'Invalid JSON'
                }, 400)
                return
            
            # Handle send request
            result = email_server.handle_send_request(data)
            
            status = 200 if result.get('success') else 400
            self.send_json_response(result, status)
        
        elif self.path == '/flush':
            # Send all queued emails
            queued = email_server.email_queue.get_all()
            results = []
            
            for email_data in queued:
                result = email_server.send_email_smtp(
                    email_data.get('to', ''),
                    email_data.get('subject', ''),
                    email_data.get('body', ''),
                    email_data.get('html', False)
                )
                results.append(result)
            
            email_server.email_queue.clear()
            
            self.send_json_response({
                'flushed': len(results),
                'results': results
            })
        
        elif self.path == '/queue/add':
            # Add email to queue
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({
                    'success': False,
                    'error': 'Invalid JSON'
                }, 400)
                return
            
            email_server.email_queue.add(data)
            
            self.send_json_response({
                'success': True,
                'message': 'Email queued',
                'queue_size': len(email_server.email_queue.get_all())
            })
        
        else:
            self.send_json_response({
                'error': 'Not found',
                'endpoints': ['/send', '/queue/add', '/flush']
            }, 404)


def run_server(server_instance: EmailMCPServer):
    """Run the MCP server."""
    global email_server
    email_server = server_instance
    
    server_address = (server_instance.HOST, server_instance.PORT)
    httpd = HTTPServer(server_address, MCPRequestHandler)
    
    server_instance.server = httpd
    server_instance.running = True
    
    logger.info("=" * 60)
    logger.info("Email MCP Server Started")
    logger.info("=" * 60)
    logger.info(f"Host: {server_instance.HOST}")
    logger.info(f"Port: {server_instance.PORT}")
    logger.info(f"SMTP Server: {server_instance.SMTP_SERVER}:{server_instance.SMTP_PORT}")
    logger.info(f"From Email: {server_instance.FROM_EMAIL or server_instance.SMTP_USER or '(not configured)'}")
    logger.info("")
    logger.info("Mode: " + ("LIVE" if server_instance.SMTP_USER else "DEMO"))
    logger.info("")
    logger.info("API Endpoints:")
    logger.info("  POST /send     - Send an email")
    logger.info("  GET  /status   - Server status")
    logger.info("  GET  /queue    - View queued emails")
    logger.info("  POST /flush    - Send queued emails")
    logger.info("  GET  /health   - Health check")
    logger.info("")
    logger.info("Example request:")
    logger.info('  curl -X POST http://localhost:8765/send \\')
    logger.info('    -H "Content-Type: application/json" \\')
    logger.info('    -d \'{"to": "user@example.com", "subject": "Test", "body": "Hello"}\'')
    logger.info("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down server...")
        httpd.shutdown()
        server_instance.running = False


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent.parent
    server = EmailMCPServer(logs_dir=BASE_DIR / "Logs")
    run_server(server)
