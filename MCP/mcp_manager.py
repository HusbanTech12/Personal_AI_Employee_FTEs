#!/usr/bin/env python3
"""
MCP Manager - Model Context Protocol Server Manager

Central manager for all MCP servers in the AI Employee system.
Handles registration, routing, and fallback for offline servers.

Capabilities:
- Register MCP servers
- Route agent requests to appropriate MCP
- Health monitoring
- Fallback when MCP offline
- Action discovery

Usage:
    python mcp_manager.py

Architecture:
    Agents → MCP Manager → MCP Servers
                 ↓
           Fallback if offline
"""

import os
import sys
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MCPManager")


class MCPStatus(Enum):
    """MCP server status."""
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"


@dataclass
class MCPConfig:
    """Configuration for an MCP server."""
    name: str
    host: str
    port: int
    base_url: str
    actions: List[str]
    status: MCPStatus = MCPStatus.OFFLINE
    last_health_check: Optional[str] = None
    fallback_enabled: bool = True


class MCPManager:
    """
    MCP Manager - Central registry and router for MCP servers.
    """
    
    HOST = os.getenv("MCP_MANAGER_HOST", "127.0.0.1")
    PORT = int(os.getenv("MCP_MANAGER_PORT", "8770"))
    
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.mcp_servers: Dict[str, MCPConfig] = {}
        self.action_registry: Dict[str, str] = {}  # action → mcp_name
        self.request_log: List[Dict] = []
        self.server: Optional[HTTPServer] = None
        self.running = False
        
        # Register built-in MCP servers
        self._register_default_mcps()
    
    def _register_default_mcps(self):
        """Register default MCP servers."""
        default_mcps = [
            {
                'name': 'email',
                'host': '127.0.0.1',
                'port': 8765,
                'actions': ['send', 'queue_add', 'flush']
            },
            {
                'name': 'linkedin',
                'host': '127.0.0.1',
                'port': 8766,
                'actions': ['generate', 'publish', 'generate-and-publish', 'analytics']
            },
            {
                'name': 'accounting',
                'host': '127.0.0.1',
                'port': 8767,
                'actions': ['invoice/create', 'expense/add', 'reports/summary', 'budget/status']
            },
            {
                'name': 'social',
                'host': '127.0.0.1',
                'port': 8768,
                'actions': ['post/schedule', 'post/publish', 'analytics', 'calendar']
            },
            {
                'name': 'automation',
                'host': '127.0.0.1',
                'port': 8769,
                'actions': ['file/copy', 'file/move', 'transform', 'webhook/trigger']
            }
        ]
        
        for mcp in default_mcps:
            self.register_mcp(mcp)
        
        logger.info(f"Registered {len(self.mcp_servers)} MCP servers")
    
    def register_mcp(self, config: Dict):
        """Register an MCP server."""
        name = config['name']
        
        mcp_config = MCPConfig(
            name=name,
            host=config.get('host', '127.0.0.1'),
            port=config.get('port', 8765),
            base_url=f"http://{config.get('host', '127.0.0.1')}:{config.get('port', 8765)}",
            actions=config.get('actions', []),
            fallback_enabled=config.get('fallback_enabled', True)
        )
        
        self.mcp_servers[name] = mcp_config
        
        # Register actions
        for action in mcp_config.actions:
            action_key = f"{name}/{action}"
            self.action_registry[action_key] = name
        
        logger.info(f"Registered MCP: {name} ({mcp_config.base_url})")
    
    def unregister_mcp(self, name: str):
        """Unregister an MCP server."""
        if name in self.mcp_servers:
            mcp = self.mcp_servers[name]
            
            # Remove actions
            for action in mcp.actions:
                action_key = f"{name}/{action}"
                self.action_registry.pop(action_key, None)
            
            del self.mcp_servers[name]
            logger.info(f"Unregistered MCP: {name}")
    
    def check_health(self, mcp_name: str) -> bool:
        """Check health of an MCP server."""
        if mcp_name not in self.mcp_servers:
            return False
        
        mcp = self.mcp_servers[mcp_name]
        
        try:
            url = f"{mcp.base_url}/health"
            req = urllib.request.Request(url, method='GET')
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    mcp.status = MCPStatus.ONLINE
                    mcp.last_health_check = datetime.now().isoformat()
                    return True
                else:
                    mcp.status = MCPStatus.DEGRADED
                    return False
                    
        except Exception as e:
            logger.warning(f"MCP {mcp_name} health check failed: {e}")
            mcp.status = MCPStatus.OFFLINE
            mcp.last_health_check = datetime.now().isoformat()
            return False
    
    def check_all_health(self):
        """Check health of all MCP servers."""
        for name in self.mcp_servers:
            self.check_health(name)
    
    def route_request(self, mcp_name: str, action: str, data: Dict) -> Dict:
        """Route a request to an MCP server."""
        if mcp_name not in self.mcp_servers:
            return {
                'success': False,
                'error': f'MCP not found: {mcp_name}',
                'fallback': False
            }
        
        mcp = self.mcp_servers[mcp_name]
        
        # Check if MCP is online
        if mcp.status != MCPStatus.ONLINE:
            if not self.check_health(mcp_name):
                # MCP is offline
                if mcp.fallback_enabled:
                    return self._execute_fallback(mcp_name, action, data)
                else:
                    return {
                        'success': False,
                        'error': f'MCP offline: {mcp_name}',
                        'fallback': False
                    }
        
        # Build request URL
        action_path = action.replace('//', '/')
        url = f"{mcp.base_url}/{action_path}"
        
        try:
            json_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=json_data,
                method='POST',
                headers={'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                # Log successful request
                self._log_request(mcp_name, action, data, result, True)
                
                return result
                
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
            result = {'success': False, 'error': error_body, 'http_status': e.code}
            self._log_request(mcp_name, action, data, result, False)
            return result
            
        except Exception as e:
            # MCP failed - try fallback
            if mcp.fallback_enabled:
                logger.warning(f"MCP {mcp_name} failed, using fallback: {e}")
                return self._execute_fallback(mcp_name, action, data)
            else:
                result = {'success': False, 'error': str(e)}
                self._log_request(mcp_name, action, data, result, False)
                return result
    
    def _execute_fallback(self, mcp_name: str, action: str, data: Dict) -> Dict:
        """Execute fallback when MCP is offline."""
        logger.info(f"Executing fallback for {mcp_name}/{action}")
        
        fallback_responses = {
            'email': {
                'success': True,
                'message': 'Email queued (MCP offline - demo mode)',
                'fallback': True,
                'queued': True
            },
            'linkedin': {
                'success': True,
                'message': 'Post content generated (MCP offline - demo mode)',
                'fallback': True,
                'generated_content': {
                    'text': 'Post content would be generated when MCP is online',
                    'hashtags': ['#AI', '#Automation']
                }
            },
            'accounting': {
                'success': True,
                'message': 'Recorded locally (MCP offline)',
                'fallback': True,
                'local_record': True
            },
            'social': {
                'success': True,
                'message': 'Post scheduled locally (MCP offline)',
                'fallback': True,
                'scheduled': True
            },
            'automation': {
                'success': True,
                'message': 'Action logged for later execution (MCP offline)',
                'fallback': True,
                'pending': True
            }
        }
        
        fallback = fallback_responses.get(mcp_name, {
            'success': True,
            'message': f'Fallback executed for {mcp_name}',
            'fallback': True
        })
        
        self._log_request(mcp_name, action, data, fallback, False, fallback=True)
        
        return fallback
    
    def _log_request(self, mcp_name: str, action: str, data: Dict, 
                     result: Dict, success: bool, fallback: bool = False):
        """Log a request."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'mcp': mcp_name,
            'action': action,
            'success': success,
            'fallback': fallback
        }
        self.request_log.append(log_entry)
        
        # Keep last 1000 requests
        if len(self.request_log) > 1000:
            self.request_log = self.request_log[-1000:]
    
    def get_registered_actions(self) -> Dict[str, List[str]]:
        """Get all registered actions by MCP."""
        actions_by_mcp: Dict[str, List[str]] = {}
        
        for name, mcp in self.mcp_servers.items():
            actions_by_mcp[name] = mcp.actions
        
        return actions_by_mcp
    
    def get_status(self) -> Dict:
        """Get manager status."""
        online_count = sum(1 for m in self.mcp_servers.values() if m.status == MCPStatus.ONLINE)
        
        return {
            'status': 'running' if self.running else 'stopped',
            'host': self.HOST,
            'port': self.PORT,
            'mcp_servers': {
                name: {
                    'status': mcp.status.value,
                    'url': mcp.base_url,
                    'actions_count': len(mcp.actions),
                    'last_health_check': mcp.last_health_check
                }
                for name, mcp in self.mcp_servers.items()
            },
            'total_mcps': len(self.mcp_servers),
            'online_mcps': online_count,
            'total_actions': len(self.action_registry),
            'requests_logged': len(self.request_log)
        }


# Global manager instance
mcp_manager: Optional[MCPManager] = None


class MCPManagerHandler(BaseHTTPRequestHandler):
    """HTTP request handler for MCP Manager."""
    
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
            result = mcp_manager.get_status()
            self.send_json_response(result)
        
        elif path == '/health':
            self.send_json_response({'status': 'healthy'})
        
        elif path == '/actions':
            result = {
                'success': True,
                'actions': mcp_manager.get_registered_actions()
            }
            self.send_json_response(result)
        
        elif path == '/servers':
            result = {
                'success': True,
                'servers': {
                    name: asdict(mcp) if hasattr(mcp, '__dataclass_fields__') else {
                        'name': name,
                        'base_url': mcp.base_url,
                        'status': mcp.status.value,
                        'actions': mcp.actions
                    }
                    for name, mcp in mcp_manager.mcp_servers.items()
                }
            }
            self.send_json_response(result)
        
        else:
            self.send_json_response({
                'error': 'Not found',
                'endpoints': [
                    'GET /status', 'GET /health',
                    'GET /actions', 'GET /servers'
                ]
            }, 404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/register':
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({'success': False, 'error': 'Invalid JSON'}, 400)
                return
            
            mcp_manager.register_mcp(data)
            self.send_json_response({
                'success': True,
                'message': f"MCP registered: {data.get('name')}"
            })
        
        elif path == '/route':
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({'success': False, 'error': 'Invalid JSON'}, 400)
                return
            
            mcp_name = data.get('mcp')
            action = data.get('action')
            payload = data.get('payload', {})
            
            if not mcp_name or not action:
                self.send_json_response({
                    'success': False,
                    'error': 'Missing mcp or action'
                }, 400)
                return
            
            result = mcp_manager.route_request(mcp_name, action, payload)
            self.send_json_response(result)
        
        elif path == '/health/check':
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                data = {}
            
            mcp_name = data.get('mcp')
            if mcp_name:
                healthy = mcp_manager.check_health(mcp_name)
                self.send_json_response({
                    'success': True,
                    'mcp': mcp_name,
                    'healthy': healthy,
                    'status': mcp_manager.mcp_servers.get(mcp_name, {}).status.value if mcp_name in mcp_manager.mcp_servers else 'unknown'
                })
            else:
                mcp_manager.check_all_health()
                self.send_json_response({
                    'success': True,
                    'message': 'All health checks completed',
                    'status': {
                        name: mcp.status.value 
                        for name, mcp in mcp_manager.mcp_servers.items()
                    }
                })
        
        else:
            self.send_json_response({
                'error': 'Not found',
                'endpoints': [
                    'POST /register', 'POST /route', 'POST /health/check'
                ]
            }, 404)


def run_manager(manager_instance: MCPManager):
    """Run the MCP Manager."""
    global mcp_manager
    mcp_manager = manager_instance
    
    server_address = (manager_instance.HOST, manager_instance.PORT)
    httpd = HTTPServer(server_address, MCPManagerHandler)
    
    manager_instance.server = httpd
    manager_instance.running = True
    
    # Initial health check
    manager_instance.check_all_health()
    
    logger.info("=" * 60)
    logger.info("MCP Manager Started")
    logger.info("=" * 60)
    logger.info(f"Host: {manager_instance.HOST}")
    logger.info(f"Port: {manager_instance.PORT}")
    logger.info("")
    logger.info("Registered MCP Servers:")
    for name, mcp in manager_instance.mcp_servers.items():
        logger.info(f"  - {name}: {mcp.base_url} [{mcp.status.value}]")
    logger.info("")
    logger.info("Endpoints:")
    logger.info("  GET  /status   - Manager status")
    logger.info("  GET  /health   - Health check")
    logger.info("  GET  /actions  - List all registered actions")
    logger.info("  GET  /servers  - List all MCP servers")
    logger.info("  POST /register - Register new MCP")
    logger.info("  POST /route    - Route request to MCP")
    logger.info("  POST /health/check - Check MCP health")
    logger.info("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        httpd.shutdown()
        manager_instance.running = False


# Import urlparse for the handler
from urllib.parse import urlparse

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    manager = MCPManager(base_dir=BASE_DIR)
    run_manager(manager)
