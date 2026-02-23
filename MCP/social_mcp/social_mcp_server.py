#!/usr/bin/env python3
"""
Social MCP Server - Social Media Operations Service

Model Context Protocol (MCP) server for social media management.
Provides HTTP API for agents to manage multiple social platforms.

Capabilities:
- Schedule posts (Twitter, Facebook, Instagram)
- Get engagement metrics
- Generate content calendars
- Cross-post management

Local-first HTTP server running on localhost.

Usage:
    python social_mcp_server.py

API Endpoints:
    POST /post/schedule   - Schedule a post
    POST /post/publish    - Publish immediately
    GET  /analytics       - Get engagement metrics
    GET  /calendar        - Get content calendar
    GET  /status          - Server status
    GET  /health          - Health check
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
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
logger = logging.getLogger("SocialMCPServer")


class SocialStore:
    """In-memory store for social media data."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.posts: Dict[str, Dict] = {}
        self.analytics: Dict[str, Dict] = {}
        self.platforms = ['twitter', 'facebook', 'instagram', 'linkedin']
        
        self._load_data()
    
    def _load_data(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
        posts_file = self.data_dir / "posts.json"
        if posts_file.exists():
            try:
                with open(posts_file, 'r') as f:
                    self.posts = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load posts: {e}")
    
    def _save_data(self):
        try:
            with open(self.data_dir / "posts.json", 'w') as f:
                json.dump(self.posts, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
    
    def schedule_post(self, post_data: Dict) -> Dict:
        """Schedule a post."""
        post_id = f"POST-{uuid.uuid4().hex[:8].upper()}"
        
        post = {
            'id': post_id,
            'created_at': datetime.now().isoformat(),
            'status': 'scheduled',
            'platforms': post_data.get('platforms', ['twitter']),
            'content': post_data.get('content', ''),
            'scheduled_for': post_data.get('scheduled_for'),
            'hashtags': post_data.get('hashtags', [])
        }
        
        self.posts[post_id] = post
        self._save_data()
        
        return post
    
    def publish_post(self, post_data: Dict) -> Dict:
        """Publish a post immediately."""
        post_id = f"POST-{uuid.uuid4().hex[:8].upper()}"
        
        post = {
            'id': post_id,
            'created_at': datetime.now().isoformat(),
            'published_at': datetime.now().isoformat(),
            'status': 'published',
            'platforms': post_data.get('platforms', ['twitter']),
            'content': post_data.get('content', ''),
            'hashtags': post_data.get('hashtags', [])
        }
        
        self.posts[post_id] = post
        
        # Simulate analytics
        self.analytics[post_id] = {
            'impressions': 0,
            'likes': 0,
            'shares': 0,
            'comments': 0
        }
        
        self._save_data()
        
        return post
    
    def get_analytics(self, post_id: Optional[str] = None) -> Dict:
        """Get analytics for posts."""
        if post_id:
            return self.analytics.get(post_id, {'error': 'Post not found'})
        
        # Aggregate analytics
        total_impressions = sum(a.get('impressions', 0) for a in self.analytics.values())
        total_engagement = sum(
            a.get('likes', 0) + a.get('shares', 0) + a.get('comments', 0)
            for a in self.analytics.values()
        )
        
        return {
            'total_posts': len(self.posts),
            'total_impressions': total_impressions,
            'total_engagement': total_engagement,
            'posts': [
                {
                    'id': pid,
                    'content': p.get('content', '')[:50],
                    'analytics': self.analytics.get(pid, {})
                }
                for pid, p in list(self.posts.items())[-10:]
            ]
        }
    
    def get_calendar(self, days: int = 7) -> List[Dict]:
        """Get content calendar."""
        calendar = []
        now = datetime.now()
        
        for post_id, post in self.posts.items():
            if post.get('status') == 'scheduled':
                scheduled = post.get('scheduled_for')
                if scheduled:
                    try:
                        sched_date = datetime.fromisoformat(scheduled)
                        if sched_date <= now + timedelta(days=days):
                            calendar.append({
                                'id': post_id,
                                'scheduled_for': scheduled,
                                'platforms': post.get('platforms'),
                                'content': post.get('content', '')[:100]
                            })
                    except ValueError:
                        pass
        
        return sorted(calendar, key=lambda x: x['scheduled_for'])


class SocialMCPServer:
    """
    Social MCP Server - Handles social media operations for AI agents.
    """
    
    HOST = os.getenv("SOCIAL_MCP_HOST", "127.0.0.1")
    PORT = int(os.getenv("SOCIAL_MCP_PORT", "8768"))
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.store = SocialStore(data_dir)
        self.server: Optional[HTTPServer] = None
        self.running = False
    
    def schedule_post(self, data: Dict) -> Dict:
        """Schedule post action."""
        required = ['content', 'scheduled_for']
        for field in required:
            if field not in data:
                return {'success': False, 'error': f'Missing: {field}'}
        
        post = self.store.schedule_post(data)
        
        return {
            'success': True,
            'post': post,
            'message': f"Post {post['id']} scheduled for {post['scheduled_for']}"
        }
    
    def publish_post(self, data: Dict) -> Dict:
        """Publish post action."""
        required = ['content']
        for field in required:
            if field not in data:
                return {'success': False, 'error': f'Missing: {field}'}
        
        post = self.store.publish_post(data)
        
        return {
            'success': True,
            'post': post,
            'message': f"Post {post['id']} published"
        }
    
    def get_analytics(self, post_id: Optional[str] = None) -> Dict:
        """Get analytics."""
        return {
            'success': True,
            **self.store.get_analytics(post_id)
        }
    
    def get_calendar(self, days: int = 7) -> Dict:
        """Get content calendar."""
        return {
            'success': True,
            'calendar': self.store.get_calendar(days)
        }
    
    def get_status(self) -> Dict:
        """Get server status."""
        return {
            'status': 'running' if self.running else 'stopped',
            'host': self.HOST,
            'port': self.PORT,
            'total_posts': len(self.store.posts),
            'platforms': self.store.platforms,
            'timestamp': datetime.now().isoformat()
        }


# Global server instance
social_server: Optional[SocialMCPServer] = None


class MCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Social MCP."""
    
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
            result = social_server.get_status()
            self.send_json_response(result)
        
        elif path == '/health':
            self.send_json_response({'status': 'healthy'})
        
        elif path == '/analytics':
            query = parse_qs(parsed.query)
            post_id = query.get('post_id', [None])[0]
            result = social_server.get_analytics(post_id)
            self.send_json_response(result)
        
        elif path == '/calendar':
            query = parse_qs(parsed.query)
            days = int(query.get('days', ['7'])[0])
            result = social_server.get_calendar(days)
            self.send_json_response(result)
        
        else:
            self.send_json_response({
                'error': 'Not found',
                'endpoints': [
                    'GET /status', 'GET /health',
                    'GET /analytics', 'GET /calendar'
                ]
            }, 404)
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/post/schedule':
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({'success': False, 'error': 'Invalid JSON'}, 400)
                return
            
            result = social_server.schedule_post(data)
            self.send_json_response(result, 200 if result.get('success') else 400)
        
        elif path == '/post/publish':
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({'success': False, 'error': 'Invalid JSON'}, 400)
                return
            
            result = social_server.publish_post(data)
            self.send_json_response(result, 200 if result.get('success') else 400)
        
        else:
            self.send_json_response({
                'error': 'Not found',
                'endpoints': ['POST /post/schedule', 'POST /post/publish']
            }, 404)


def run_server(server_instance: SocialMCPServer):
    """Run the MCP server."""
    global social_server
    social_server = server_instance
    
    server_address = (server_instance.HOST, server_instance.PORT)
    httpd = HTTPServer(server_address, MCPRequestHandler)
    
    server_instance.server = httpd
    server_instance.running = True
    
    logger.info("=" * 60)
    logger.info("Social MCP Server Started")
    logger.info("=" * 60)
    logger.info(f"Host: {server_instance.HOST}")
    logger.info(f"Port: {server_instance.PORT}")
    logger.info(f"Platforms: {', '.join(server_instance.store.platforms)}")
    logger.info("")
    logger.info("Actions:")
    logger.info("  POST /post/schedule  - Schedule a post")
    logger.info("  POST /post/publish   - Publish immediately")
    logger.info("  GET  /analytics      - Get engagement metrics")
    logger.info("  GET  /calendar       - Get content calendar")
    logger.info("  GET  /status         - Server status")
    logger.info("  GET  /health         - Health check")
    logger.info("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        httpd.shutdown()
        server_instance.running = False


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent.parent
    server = SocialMCPServer(data_dir=BASE_DIR / "MCP" / "social_mcp" / "data")
    run_server(server)
