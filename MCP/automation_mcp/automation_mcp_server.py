#!/usr/bin/env python3
"""
Automation MCP Server - General Automation Service

Model Context Protocol (MCP) server for general automation tasks.
Provides HTTP API for agents to trigger automated workflows.

Capabilities:
- File operations (copy, move, rename)
- Data transformation
- Webhook triggers
- Scheduled task management
- System commands (sandboxed)

Local-first HTTP server running on localhost.

Usage:
    python automation_mcp_server.py

API Endpoints:
    POST /file/copy       - Copy file
    POST /file/move       - Move file
    POST /transform       - Transform data
    POST /webhook/trigger - Trigger webhook
    GET  /tasks/list      - List scheduled tasks
    GET  /status          - Server status
    GET  /health          - Health check
"""

import os
import sys
import json
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs
import uuid
import urllib.request

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("AutomationMCPServer")


class AutomationStore:
    """Store for automation tasks and logs."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.tasks: Dict[str, Dict] = {}
        self.logs: List[Dict] = []
        self.webhooks: Dict[str, Dict] = {}
        
        self._load_data()
    
    def _load_data(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tasks_file = self.data_dir / "tasks.json"
        if tasks_file.exists():
            try:
                with open(tasks_file, 'r') as f:
                    self.tasks = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load tasks: {e}")
    
    def _save_data(self):
        try:
            with open(self.data_dir / "tasks.json", 'w') as f:
                json.dump(self.tasks, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
    
    def add_task(self, task_data: Dict) -> Dict:
        """Add a scheduled task."""
        task_id = f"AUTO-{uuid.uuid4().hex[:8].upper()}"
        
        task = {
            'id': task_id,
            'created_at': datetime.now().isoformat(),
            'status': 'pending',
            **task_data
        }
        
        self.tasks[task_id] = task
        self._save_data()
        
        return task
    
    def log_action(self, action: str, result: Dict):
        """Log an automation action."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'result': result
        }
        self.logs.append(log_entry)
        
        # Keep last 1000 logs
        if len(self.logs) > 1000:
            self.logs = self.logs[-1000:]
    
    def register_webhook(self, webhook_data: Dict) -> Dict:
        """Register a webhook."""
        webhook_id = f"WH-{uuid.uuid4().hex[:8].upper()}"
        
        webhook = {
            'id': webhook_id,
            'created_at': datetime.now().isoformat(),
            'status': 'active',
            **webhook_data
        }
        
        self.webhooks[webhook_id] = webhook
        
        return webhook
    
    def trigger_webhook(self, webhook_id: str, payload: Dict) -> Dict:
        """Trigger a webhook."""
        webhook = self.webhooks.get(webhook_id)
        
        if not webhook:
            return {'success': False, 'error': 'Webhook not found'}
        
        url = webhook.get('url')
        if not url:
            return {'success': False, 'error': 'No URL configured'}
        
        try:
            json_data = json.dumps(payload).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=json_data,
                method='POST',
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
            
            self.log_action('webhook_trigger', {
                'webhook_id': webhook_id,
                'success': True
            })
            
            return {'success': True, 'response': result}
            
        except Exception as e:
            self.log_action('webhook_trigger', {
                'webhook_id': webhook_id,
                'success': False,
                'error': str(e)
            })
            
            return {'success': False, 'error': str(e)}


class AutomationMCPServer:
    """
    Automation MCP Server - Handles automation tasks for AI agents.
    """
    
    HOST = os.getenv("AUTOMATION_MCP_HOST", "127.0.0.1")
    PORT = int(os.getenv("AUTOMATION_MCP_PORT", "8769"))
    
    # Allowed directories for file operations (security)
    ALLOWED_DIRS = [
        Path(__file__).parent.parent.parent  # Project root
    ]
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.store = AutomationStore(data_dir)
        self.server: Optional[HTTPServer] = None
        self.running = False
    
    def _is_allowed_path(self, path: Path) -> bool:
        """Check if path is within allowed directories."""
        try:
            resolved = path.resolve()
            for allowed in self.ALLOWED_DIRS:
                try:
                    resolved.relative_to(allowed.resolve())
                    return True
                except ValueError:
                    continue
            return False
        except Exception:
            return False
    
    def copy_file(self, data: Dict) -> Dict:
        """Copy file action."""
        try:
            src = Path(data.get('source', ''))
            dst = Path(data.get('destination', ''))
            
            if not self._is_allowed_path(src) or not self._is_allowed_path(dst):
                return {'success': False, 'error': 'Path not allowed'}
            
            if not src.exists():
                return {'success': False, 'error': 'Source file not found'}
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            
            self.store.log_action('copy_file', {'source': str(src), 'destination': str(dst)})
            
            return {'success': True, 'message': f'Copied {src} to {dst}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def move_file(self, data: Dict) -> Dict:
        """Move file action."""
        try:
            src = Path(data.get('source', ''))
            dst = Path(data.get('destination', ''))
            
            if not self._is_allowed_path(src) or not self._is_allowed_path(dst):
                return {'success': False, 'error': 'Path not allowed'}
            
            if not src.exists():
                return {'success': False, 'error': 'Source file not found'}
            
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            
            self.store.log_action('move_file', {'source': str(src), 'destination': str(dst)})
            
            return {'success': True, 'message': f'Moved {src} to {dst}'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def transform_data(self, data: Dict) -> Dict:
        """Transform data action."""
        try:
            transform_type = data.get('type', 'json_to_csv')
            input_data = data.get('input', '')
            
            if transform_type == 'json_to_csv':
                import csv
                import io
                
                json_data = json.loads(input_data)
                if not isinstance(json_data, list):
                    json_data = [json_data]
                
                if not json_data:
                    return {'success': False, 'error': 'Empty data'}
                
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=json_data[0].keys())
                writer.writeheader()
                writer.writerows(json_data)
                
                return {
                    'success': True,
                    'output': output.getvalue(),
                    'format': 'csv'
                }
            
            elif transform_type == 'uppercase':
                return {
                    'success': True,
                    'output': input_data.upper(),
                    'format': 'text'
                }
            
            elif transform_type == 'lowercase':
                return {
                    'success': True,
                    'output': input_data.lower(),
                    'format': 'text'
                }
            
            else:
                return {'success': False, 'error': f'Unknown transform: {transform_type}'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def trigger_webhook(self, webhook_id: str, payload: Dict) -> Dict:
        """Trigger webhook action."""
        return self.store.trigger_webhook(webhook_id, payload)
    
    def list_tasks(self) -> Dict:
        """List scheduled tasks."""
        return {
            'success': True,
            'tasks': list(self.store.tasks.values())
        }
    
    def get_status(self) -> Dict:
        """Get server status."""
        return {
            'status': 'running' if self.running else 'stopped',
            'host': self.HOST,
            'port': self.PORT,
            'tasks_count': len(self.store.tasks),
            'webhooks_count': len(self.store.webhooks),
            'logs_count': len(self.store.logs),
            'timestamp': datetime.now().isoformat()
        }


# Global server instance
automation_server: Optional[AutomationMCPServer] = None


class MCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Automation MCP."""
    
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
            result = automation_server.get_status()
            self.send_json_response(result)
        
        elif path == '/health':
            self.send_json_response({'status': 'healthy'})
        
        elif path == '/tasks/list':
            result = automation_server.list_tasks()
            self.send_json_response(result)
        
        else:
            self.send_json_response({
                'error': 'Not found',
                'endpoints': [
                    'GET /status', 'GET /health', 'GET /tasks/list'
                ]
            }, 404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/file/copy':
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({'success': False, 'error': 'Invalid JSON'}, 400)
                return
            
            result = automation_server.copy_file(data)
            self.send_json_response(result, 200 if result.get('success') else 400)
        
        elif path == '/file/move':
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({'success': False, 'error': 'Invalid JSON'}, 400)
                return
            
            result = automation_server.move_file(data)
            self.send_json_response(result, 200 if result.get('success') else 400)
        
        elif path == '/transform':
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({'success': False, 'error': 'Invalid JSON'}, 400)
                return
            
            result = automation_server.transform_data(data)
            self.send_json_response(result, 200 if result.get('success') else 400)
        
        elif path.startswith('/webhook/trigger/'):
            webhook_id = path.split('/webhook/trigger/')[-1]
            body = self.rfile.read(content_length)
            try:
                payload = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                payload = {}
            
            result = automation_server.trigger_webhook(webhook_id, payload)
            self.send_json_response(result, 200 if result.get('success') else 400)
        
        else:
            self.send_json_response({
                'error': 'Not found',
                'endpoints': [
                    'POST /file/copy', 'POST /file/move',
                    'POST /transform', 'POST /webhook/trigger/:id'
                ]
            }, 404)


def run_server(server_instance: AutomationMCPServer):
    """Run the MCP server."""
    global automation_server
    automation_server = server_instance
    
    server_address = (server_instance.HOST, server_instance.PORT)
    httpd = HTTPServer(server_address, MCPRequestHandler)
    
    server_instance.server = httpd
    server_instance.running = True
    
    logger.info("=" * 60)
    logger.info("Automation MCP Server Started")
    logger.info("=" * 60)
    logger.info(f"Host: {server_instance.HOST}")
    logger.info(f"Port: {server_instance.PORT}")
    logger.info("")
    logger.info("Actions:")
    logger.info("  POST /file/copy          - Copy file")
    logger.info("  POST /file/move          - Move file")
    logger.info("  POST /transform          - Transform data")
    logger.info("  POST /webhook/trigger/:id - Trigger webhook")
    logger.info("  GET  /tasks/list         - List scheduled tasks")
    logger.info("  GET  /status             - Server status")
    logger.info("  GET  /health             - Health check")
    logger.info("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        httpd.shutdown()
        server_instance.running = False


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent.parent
    server = AutomationMCPServer(data_dir=BASE_DIR / "MCP" / "automation_mcp" / "data")
    run_server(server)
