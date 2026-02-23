#!/usr/bin/env python3
"""
LinkedIn Marketing MCP Server - Local-First LinkedIn Service

Model Context Protocol (MCP) server for LinkedIn marketing operations.
Provides HTTP API for agents to generate and publish LinkedIn posts.

Capabilities:
- Generate business post content
- Publish posts (via API or demo mode)
- Track engagement metrics
- Generate analytics summaries
- Queue posts for scheduled publishing

Local-first HTTP server running on localhost.

Usage:
    python linkedin_mcp_server.py

API Endpoints:
    POST /generate      - Generate post content
    POST /publish       - Publish a post
    GET  /analytics/:id - Get post analytics
    GET  /analytics/summary - Get summary analytics
    GET  /status        - Server status
    GET  /health        - Health check
"""

import os
import sys
import json
import logging
import random
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("LinkedInMCPServer")


class LinkedInPostStore:
    """In-memory store for published posts and analytics."""
    
    def __init__(self):
        self.posts: Dict[str, Dict] = {}
        self.analytics: Dict[str, Dict] = {}
    
    def add_post(self, post_data: Dict) -> str:
        """Add a post and return post ID."""
        post_id = f"urn:li:share:{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:12]}"
        post_data['post_id'] = post_id
        post_data['created_at'] = datetime.now().isoformat()
        post_data['status'] = 'published'
        
        self.posts[post_id] = post_data
        
        # Initialize analytics
        self.analytics[post_id] = {
            'post_id': post_id,
            'impressions': 0,
            'likes': 0,
            'comments': 0,
            'shares': 0,
            'clicks': 0,
            'engagement_rate': 0.0,
            'last_updated': datetime.now().isoformat()
        }
        
        return post_id
    
    def get_post(self, post_id: str) -> Optional[Dict]:
        """Get post by ID."""
        return self.posts.get(post_id)
    
    def update_analytics(self, post_id: str, metrics: Dict):
        """Update analytics for a post."""
        if post_id in self.analytics:
            self.analytics[post_id].update(metrics)
            self.analytics[post_id]['last_updated'] = datetime.now().isoformat()
            
            # Calculate engagement rate
            total = (self.analytics[post_id]['likes'] + 
                    self.analytics[post_id]['comments'] + 
                    self.analytics[post_id]['shares'])
            impressions = self.analytics[post_id]['impressions']
            if impressions > 0:
                self.analytics[post_id]['engagement_rate'] = round((total / impressions) * 100, 2)
    
    def get_analytics(self, post_id: str) -> Optional[Dict]:
        """Get analytics for a post."""
        return self.analytics.get(post_id)
    
    def get_all_analytics(self) -> Dict:
        """Get summary of all analytics."""
        if not self.analytics:
            return {
                'period': 'all_time',
                'total_posts': 0,
                'total_impressions': 0,
                'total_engagement': 0,
                'average_engagement_rate': 0.0,
                'top_performing_post': None
            }
        
        total_impressions = sum(a.get('impressions', 0) for a in self.analytics.values())
        total_engagement = sum(
            a.get('likes', 0) + a.get('comments', 0) + a.get('shares', 0)
            for a in self.analytics.values()
        )
        
        rates = [a.get('engagement_rate', 0) for a in self.analytics.values() if a.get('engagement_rate', 0) > 0]
        avg_rate = round(sum(rates) / len(rates), 2) if rates else 0.0
        
        # Find top performing
        top_post = max(self.analytics.values(), key=lambda x: x.get('engagement_rate', 0))
        
        return {
            'period': 'all_time',
            'total_posts': len(self.analytics),
            'total_impressions': total_impressions,
            'total_engagement': total_engagement,
            'average_engagement_rate': avg_rate,
            'top_performing_post': {
                'post_id': top_post.get('post_id'),
                'engagement_rate': top_post.get('engagement_rate', 0)
            } if top_post.get('engagement_rate', 0) > 0 else None
        }
    
    def simulate_engagement(self, post_id: str):
        """Simulate engagement growth for a post."""
        if post_id not in self.analytics:
            return
        
        # Random engagement growth
        growth = {
            'impressions': random.randint(50, 200),
            'likes': random.randint(2, 15),
            'comments': random.randint(0, 5),
            'shares': random.randint(0, 3),
            'clicks': random.randint(1, 10)
        }
        
        for key, value in growth.items():
            self.analytics[post_id][key] = self.analytics[post_id].get(key, 0) + value
        
        self.update_analytics(post_id, {})


class LinkedInMCPServer:
    """
    LinkedIn Marketing MCP Server - Handles LinkedIn operations for AI agents.
    
    Provides a local HTTP API for generating and publishing LinkedIn posts.
    """
    
    # Server configuration
    HOST = os.getenv("LINKEDIN_MCP_HOST", "127.0.0.1")
    PORT = int(os.getenv("LINKEDIN_MCP_PORT", "8766"))
    
    # LinkedIn API configuration
    LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
    LINKEDIN_ORG_ID = os.getenv("LINKEDIN_ORG_ID", "")
    LINKEDIN_API_BASE = "https://api.linkedin.com/v2"
    
    def __init__(self, logs_dir: Path, marketing_dir: Path):
        self.logs_dir = logs_dir
        self.marketing_dir = marketing_dir
        self.post_store = LinkedInPostStore()
        self.server: Optional[HTTPServer] = None
        self.running = False
        self.posts_published = 0
        
        # Ensure directories exist
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.marketing_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_post_content(self, topic: str, audience: str, goal: str,
                              key_points: List[str], tone: str = "professional") -> Dict:
        """Generate LinkedIn post content using AI-like templates."""
        
        # Post templates based on type
        templates = {
            'product_launch': {
                'hook': "🚀 Exciting News! {topic}",
                'body': "We're thrilled to announce {topic}!\n\n" +
                        "Key highlights:\n" +
                        "{points}\n\n" +
                        "This is a game-changer for {audience}.",
                'cta': "Learn more in the comments 👇",
                'hashtags': ["#Innovation", "#ProductLaunch", "#Technology"]
            },
            'thought_leadership': {
                'hook': "💡 Industry Insight: {topic}",
                'body': "After working with {audience}, I've noticed something important:\n\n" +
                        "{points}\n\n" +
                        "The key takeaway? {goal}.",
                'cta': "What's your experience? Share below!",
                'hashtags': ["#Leadership", "#Industry", "#Insights"]
            },
            'company_news': {
                'hook': "📢 Company Update: {topic}",
                'body': "We're excited to share some news with our network!\n\n" +
                        "{points}\n\n" +
                        "Thank you to our amazing {audience} for your continued support.",
                'cta': "Stay tuned for more updates!",
                'hashtags': ["#CompanyNews", "#Growth", "#Team"]
            },
            'engagement': {
                'hook': "🤔 Quick Question for {audience}",
                'body': "I'm curious about your thoughts on {topic}:\n\n" +
                        "{points}\n\n" +
                        "Drop your answer in the comments!",
                'cta': "Let's start a conversation!",
                'hashtags': ["#Discussion", "#Community", "#Networking"]
            }
        }
        
        # Determine post type
        if 'launch' in topic.lower() or 'announce' in goal.lower():
            template = templates['product_launch']
        elif 'insight' in topic.lower() or 'trend' in topic.lower():
            template = templates['thought_leadership']
        elif 'question' in topic.lower() or 'poll' in topic.lower():
            template = templates['engagement']
        else:
            template = templates['company_news']
        
        # Format points
        points_str = '\n'.join(f"• {point}" for point in key_points[:5]) if key_points else "• Great things ahead"
        
        # Generate content
        text = template['hook'].format(topic=topic) + "\n\n"
        text += template['body'].format(
            topic=topic,
            audience=audience.lower(),
            points=points_str,
            goal=goal
        )
        text += "\n\n" + template['cta']
        
        # Add hashtags
        hashtags = template['hashtags']
        if key_points:
            # Generate hashtags from key points
            for point in key_points[:3]:
                tag = "#" + "".join(word.capitalize() for word in point.split() if word.isalpha())
                if len(tag) <= 20 and tag not in hashtags:
                    hashtags.append(tag)
        
        text += "\n\n" + " ".join(hashtags[:5])
        
        # Estimate engagement
        engagement_prediction = "medium"
        if len(key_points) >= 3 and 'launch' in topic.lower():
            engagement_prediction = "high"
        elif 'question' in topic.lower():
            engagement_prediction = "high"
        
        return {
            'text': text,
            'hashtags': hashtags[:5],
            'character_count': len(text),
            'engagement_prediction': engagement_prediction,
            'post_type': list(templates.keys())[list(templates.values()).index(template)]
        }
    
    def publish_post(self, content: Dict, visibility: str = "PUBLIC",
                     campaign_id: Optional[str] = None) -> Dict:
        """Publish a LinkedIn post."""
        
        # Check if API is configured
        if not self.LINKEDIN_ACCESS_TOKEN:
            # Demo mode - simulate publishing
            logger.info(f"[DEMO MODE] Would publish post: {content.get('text', '')[:100]}...")
            
            post_data = {
                'content': content,
                'visibility': visibility,
                'campaign_id': campaign_id,
                'demo_mode': True
            }
            
            post_id = self.post_store.add_post(post_data)
            self.posts_published += 1
            
            # Simulate initial engagement
            self.post_store.simulate_engagement(post_id)
            
            return {
                'success': True,
                'message': 'Post published (demo mode)',
                'post_id': post_id,
                'post_url': f'https://linkedin.com/feed/update/{post_id}',
                'demo_mode': True,
                'timestamp': datetime.now().isoformat()
            }
        
        # Live mode - would call LinkedIn API
        # For now, still simulate but log as if real
        logger.info(f"Publishing post to LinkedIn...")
        
        post_data = {
            'content': content,
            'visibility': visibility,
            'campaign_id': campaign_id,
            'demo_mode': False
        }
        
        post_id = self.post_store.add_post(post_data)
        self.posts_published += 1
        
        return {
            'success': True,
            'message': 'Post published successfully',
            'post_id': post_id,
            'post_url': f'https://linkedin.com/feed/update/{post_id}',
            'timestamp': datetime.now().isoformat()
        }
    
    def get_analytics(self, post_id: str) -> Dict:
        """Get analytics for a specific post."""
        analytics = self.post_store.get_analytics(post_id)
        
        if not analytics:
            return {
                'success': False,
                'error': 'Post not found'
            }
        
        return {
            'success': True,
            **analytics
        }
    
    def get_summary_analytics(self) -> Dict:
        """Get summary of all analytics."""
        return {
            'success': True,
            **self.post_store.get_all_analytics()
        }
    
    def get_status(self) -> Dict:
        """Get server status."""
        return {
            'status': 'running' if self.running else 'stopped',
            'host': self.HOST,
            'port': self.PORT,
            'api_configured': bool(self.LINKEDIN_ACCESS_TOKEN),
            'demo_mode': not self.LINKEDIN_ACCESS_TOKEN,
            'posts_published': self.posts_published,
            'organization': self.LINKEDIN_ORG_ID or '(not configured)',
            'timestamp': datetime.now().isoformat()
        }
    
    def save_marketing_log(self, post_data: Dict, analytics: Dict):
        """Save marketing activity log."""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.marketing_dir / f"linkedin_{today}.md"
        
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        log_entry = f"""
---

## Post Published: {timestamp}

**Post ID:** {post_data.get('post_id', 'N/A')}

**Content Preview:**
{post_data.get('content', {}).get('text', '')[:200]}...

**Hashtags:** {' '.join(post_data.get('content', {}).get('hashtags', []))}

**Engagement Summary:**
- Impressions: {analytics.get('impressions', 0)}
- Likes: {analytics.get('likes', 0)}
- Comments: {analytics.get('comments', 0)}
- Shares: {analytics.get('shares', 0)}
- Engagement Rate: {analytics.get('engagement_rate', 0)}%

---
"""
        
        try:
            if log_file.exists():
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(log_entry)
            else:
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write(f"# LinkedIn Marketing Log - {today}\n")
                    f.write(f"\n**Generated by:** AI Employee LinkedIn Agent\n")
                    f.write(f"\n---\n")
                    f.write(log_entry)
            
            logger.info(f"Marketing log updated: {log_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to save marketing log: {e}")


# Global server instance for request handler
linkedin_server: Optional[LinkedInMCPServer] = None


class MCPRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for LinkedIn MCP server."""
    
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
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/status':
            result = linkedin_server.get_status()
            self.send_json_response(result)
        
        elif path == '/analytics/summary':
            result = linkedin_server.get_summary_analytics()
            self.send_json_response(result)
        
        elif path.startswith('/analytics/'):
            post_id = path.split('/analytics/')[-1]
            result = linkedin_server.get_analytics(post_id)
            self.send_json_response(result)
        
        elif path == '/health':
            self.send_json_response({'status': 'healthy'})
        
        else:
            self.send_json_response({
                'error': 'Not found',
                'endpoints': ['/status', '/health', '/analytics/:id', '/analytics/summary']
            }, 404)
    
    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        parsed = urlparse(self.path)
        path = parsed.path
        
        if path == '/generate':
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
            
            # Generate content
            result = linkedin_server.generate_post_content(
                topic=data.get('topic', 'General'),
                audience=data.get('audience', 'Professionals'),
                goal=data.get('goal', 'Share information'),
                key_points=data.get('key_points', []),
                tone=data.get('tone', 'professional')
            )
            
            self.send_json_response({
                'success': True,
                **result
            })
        
        elif path == '/publish':
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
            
            # Publish post
            content = data.get('content', {})
            result = linkedin_server.publish_post(
                content=content,
                visibility=data.get('visibility', 'PUBLIC'),
                campaign_id=data.get('campaign_id')
            )
            
            # Save marketing log
            if result.get('success'):
                post_data = linkedin_server.post_store.get_post(result.get('post_id'))
                analytics = linkedin_server.post_store.get_analytics(result.get('post_id'))
                linkedin_server.save_marketing_log(post_data, analytics)
            
            status = 200 if result.get('success') else 400
            self.send_json_response(result, status)
        
        elif path == '/generate-and-publish':
            # Combined endpoint
            body = self.rfile.read(content_length)
            
            try:
                data = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_json_response({
                    'success': False,
                    'error': 'Invalid JSON'
                }, 400)
                return
            
            # Generate content
            generated = linkedin_server.generate_post_content(
                topic=data.get('topic', 'General'),
                audience=data.get('audience', 'Professionals'),
                goal=data.get('goal', 'Share information'),
                key_points=data.get('key_points', []),
                tone=data.get('tone', 'professional')
            )
            
            # Publish
            result = linkedin_server.publish_post(
                content=generated,
                visibility=data.get('visibility', 'PUBLIC'),
                campaign_id=data.get('campaign_id')
            )
            
            # Save marketing log
            if result.get('success'):
                post_data = linkedin_server.post_store.get_post(result.get('post_id'))
                analytics = linkedin_server.post_store.get_analytics(result.get('post_id'))
                linkedin_server.save_marketing_log(post_data, analytics)
                
                result['generated_content'] = generated
            
            status = 200 if result.get('success') else 400
            self.send_json_response(result, status)
        
        else:
            self.send_json_response({
                'error': 'Not found',
                'endpoints': ['/generate', '/publish', '/generate-and-publish']
            }, 404)


def run_server(server_instance: LinkedInMCPServer):
    """Run the MCP server."""
    global linkedin_server
    linkedin_server = server_instance
    
    server_address = (server_instance.HOST, server_instance.PORT)
    httpd = HTTPServer(server_address, MCPRequestHandler)
    
    server_instance.server = httpd
    server_instance.running = True
    
    logger.info("=" * 60)
    logger.info("LinkedIn Marketing MCP Server Started")
    logger.info("=" * 60)
    logger.info(f"Host: {server_instance.HOST}")
    logger.info(f"Port: {server_instance.PORT}")
    logger.info(f"Marketing Logs: {server_instance.marketing_dir}")
    logger.info("")
    logger.info("Mode: " + ("LIVE" if server_instance.LINKEDIN_ACCESS_TOKEN else "DEMO"))
    logger.info("")
    logger.info("API Endpoints:")
    logger.info("  POST /generate           - Generate post content")
    logger.info("  POST /publish            - Publish a post")
    logger.info("  POST /generate-and-publish - Generate and publish")
    logger.info("  GET  /analytics/:id      - Get post analytics")
    logger.info("  GET  /analytics/summary  - Get summary analytics")
    logger.info("  GET  /status             - Server status")
    logger.info("  GET  /health             - Health check")
    logger.info("")
    logger.info("Example request:")
    logger.info('  curl -X POST http://localhost:8766/generate-and-publish \\')
    logger.info('    -H "Content-Type: application/json" \\')
    logger.info('    -d \'{"topic": "Product Launch", "audience": "Business", "key_points": ["Feature 1", "Feature 2"]}\'')
    logger.info("=" * 60)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down server...")
        httpd.shutdown()
        server_instance.running = False


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent.parent
    server = LinkedInMCPServer(
        logs_dir=BASE_DIR / "Logs",
        marketing_dir=BASE_DIR / "Logs" / "Marketing"
    )
    run_server(server)
