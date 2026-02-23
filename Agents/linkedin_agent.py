#!/usr/bin/env python3
"""
LinkedIn Agent - Silver Tier AI Employee

Specialized agent for LinkedIn marketing via the LinkedIn MCP Server.
Generates business posts, publishes via MCP, and logs engagement summaries.

Capabilities:
- Read business tasks from Needs_Action
- Generate LinkedIn post content via MCP
- Publish posts to LinkedIn
- Track engagement metrics
- Save summaries to /Logs/Marketing/

MCP Server:
- Host: localhost
- Port: 8766
- Endpoints: /generate, /publish, /analytics

Usage:
    python linkedin_agent.py

Stop:
    Press Ctrl+C to gracefully stop
"""

import os
import sys
import re
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime
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
logger = logging.getLogger("LinkedInAgent")


class LinkedInAgent:
    """
    LinkedIn Agent - Manages LinkedIn marketing via MCP server.
    
    All LinkedIn operations are routed through the LinkedIn MCP Server
    for centralized management and analytics tracking.
    """
    
    # MCP Server configuration
    MCP_HOST = os.getenv("LINKEDIN_MCP_HOST", "127.0.0.1")
    MCP_PORT = int(os.getenv("LINKEDIN_MCP_PORT", "8766"))
    MCP_GENERATE_URL = f"http://{MCP_HOST}:{MCP_PORT}/generate"
    MCP_PUBLISH_URL = f"http://{MCP_HOST}:{MCP_PORT}/publish"
    MCP_COMBINED_URL = f"http://{MCP_HOST}:{MCP_PORT}/generate-and-publish"
    MCP_ANALYTICS_URL = f"http://{MCP_HOST}:{MCP_PORT}/analytics"
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    def __init__(self, needs_action_dir: Path, logs_dir: Path, marketing_dir: Path):
        self.needs_action_dir = needs_action_dir
        self.logs_dir = logs_dir
        self.marketing_dir = marketing_dir
        self.processed_tasks: set = set()
        
        # Ensure directories exist
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.marketing_dir.mkdir(parents=True, exist_ok=True)
    
    def check_mcp_server(self) -> bool:
        """Check if MCP server is running."""
        try:
            url = f"http://{self.MCP_HOST}:{self.MCP_PORT}/health"
            req = urllib.request.Request(url, method='GET')
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    logger.info("LinkedIn MCP server is healthy")
                    return True
        except Exception as e:
            logger.warning(f"LinkedIn MCP server not available: {e}")
        
        return False
    
    def read_task(self, file_path: Path) -> Tuple[str, Dict]:
        """Read task file and extract frontmatter + content."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        frontmatter = {}
        body = content
        
        # Parse frontmatter
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if frontmatter_match:
            fm_text = frontmatter_match.group(1)
            for line in fm_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip()
            body = content[frontmatter_match.end():]
        
        return body, frontmatter
    
    def parse_linkedin_details(self, content: str, frontmatter: Dict) -> Dict:
        """Parse LinkedIn post details from task content."""
        post_data = {
            'topic': frontmatter.get('topic', frontmatter.get('title', 'Business Update')),
            'audience': frontmatter.get('audience', 'Business professionals'),
            'goal': frontmatter.get('goal', 'Share information'),
            'tone': frontmatter.get('tone', 'professional'),
            'key_points': [],
            'post_type': frontmatter.get('type', 'business'),
            'campaign_id': frontmatter.get('campaign_id')
        }
        
        # Extract key points from content
        key_points = []
        
        # Look for bullet points
        bullets = re.findall(r'^[-*•]\s*(.+)$', content, re.MULTILINE)
        key_points.extend([b.strip() for b in bullets[:5]])
        
        # Look for numbered lists
        numbered = re.findall(r'^\d+\.\s*(.+)$', content, re.MULTILINE)
        key_points.extend([n.strip() for n in numbered[:5]])
        
        # Extract from Content Brief section
        brief_match = re.search(r'## Content Brief\s*\n(.*?)(?=## |$)', content, re.DOTALL)
        if brief_match:
            brief_text = brief_match.group(1)
            sentences = re.split(r'[.!?]', brief_text)
            for sentence in sentences:
                sentence = sentence.strip()
                if 20 < len(sentence) < 200 and sentence not in key_points:
                    key_points.append(sentence)
        
        post_data['key_points'] = key_points[:5]
        
        return post_data
    
    def generate_and_publish(self, post_data: Dict) -> Dict:
        """Generate and publish post via MCP server."""
        # Prepare request
        request_data = {
            'topic': post_data['topic'],
            'audience': post_data['audience'],
            'goal': post_data['goal'],
            'key_points': post_data['key_points'],
            'tone': post_data['tone'],
            'visibility': 'PUBLIC',
            'campaign_id': post_data.get('campaign_id')
        }
        
        # Build HTTP request
        json_data = json.dumps(request_data).encode('utf-8')
        req = urllib.request.Request(
            self.MCP_COMBINED_URL,
            data=json_data,
            method='POST',
            headers={'Content-Type': 'application/json'}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else str(e)
            try:
                error_result = json.loads(error_body)
            except json.JSONDecodeError:
                error_result = {'error': error_body}
            
            return {
                'success': False,
                'error': error_result.get('error', str(e)),
                'http_status': e.code
            }
        except urllib.error.URLError as e:
            return {
                'success': False,
                'error': f"Connection failed: {e.reason}",
                'http_status': 0
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'http_status': 0
            }
    
    def get_analytics(self, post_id: str) -> Dict:
        """Get analytics for a published post."""
        try:
            url = f"{self.MCP_ANALYTICS_URL}/{post_id}"
            req = urllib.request.Request(url, method='GET')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result
        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")
            return {'success': False, 'error': str(e)}
    
    def save_engagement_summary(self, task_name: str, post_data: Dict, 
                                 result: Dict, analytics: Dict):
        """Save engagement summary to Marketing logs."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        today = datetime.now().strftime('%Y-%m-%d')
        
        summary_file = self.marketing_dir / f"linkedin_summary_{today}.md"
        
        # Build summary content
        summary = f"""
---

## Post Summary: {timestamp}

**Task:** {task_name}
**Post ID:** {result.get('post_id', 'N/A')}
**Status:** {'✅ Published' if result.get('success') else '❌ Failed'}

---

### Post Content

**Topic:** {post_data.get('topic', 'N/A')}
**Audience:** {post_data.get('audience', 'N/A')}
**Goal:** {post_data.get('goal', 'N/A')}
**Tone:** {post_data.get('tone', 'N/A')}

**Generated Content:**
```
{result.get('generated_content', {}).get('text', 'N/A')[:500]}
```

**Hashtags:** {' '.join(result.get('generated_content', {}).get('hashtags', []))}

---

### Engagement Summary

| Metric | Value |
|--------|-------|
| Impressions | {analytics.get('impressions', 0)} |
| Likes | {analytics.get('likes', 0)} |
| Comments | {analytics.get('comments', 0)} |
| Shares | {analytics.get('shares', 0)} |
| Clicks | {analytics.get('clicks', 0)} |
| **Engagement Rate** | **{analytics.get('engagement_rate', 0)}%** |

---

### Post URL

{result.get('post_url', 'N/A')}

---

### Notes

- Demo Mode: {result.get('demo_mode', False)}
- Generated by: AI Employee LinkedIn Agent
- Content prediction: {result.get('generated_content', {}).get('engagement_prediction', 'N/A')}

---
"""
        
        try:
            if summary_file.exists():
                with open(summary_file, 'a', encoding='utf-8') as f:
                    f.write(summary)
            else:
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(f"# LinkedIn Marketing Summary - {today}\n")
                    f.write(f"\n**Generated by:** AI Employee LinkedIn Agent\n")
                    f.write(f"\n---\n")
                    f.write(summary)
            
            logger.info(f"Engagement summary saved: {summary_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to save engagement summary: {e}")
    
    def update_task_file(self, task_file: Path, result: Dict, analytics: Dict):
        """Update task file with publishing result."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if result.get('success'):
                # Add success section
                result_md = f"""
---

## LinkedIn Post Published

**Status:** ✅ Published
**Post ID:** {result.get('post_id', 'N/A')}
**Published:** {timestamp}
**URL:** {result.get('post_url', 'N/A')}
**Demo Mode:** {result.get('demo_mode', False)}

### Generated Content

```
{result.get('generated_content', {}).get('text', 'N/A')[:500]}
```

### Hashtags

{' '.join(result.get('generated_content', {}).get('hashtags', []))}

### Engagement Metrics

| Metric | Value |
|--------|-------|
| Impressions | {analytics.get('impressions', 0)} |
| Likes | {analytics.get('likes', 0)} |
| Comments | {analytics.get('comments', 0)} |
| Shares | {analytics.get('shares', 0)} |
| Engagement Rate | {analytics.get('engagement_rate', 0)}% |

"""
                # Update frontmatter status
                content = re.sub(
                    r'(status:\s*)[^\n]+',
                    r'\1done',
                    content,
                    flags=re.MULTILINE
                )
                if 'completed:' not in content:
                    content = re.sub(
                        r'(status:\s*done)',
                        f'\\1\ncompleted: {timestamp}',
                        content
                    )
            else:
                # Add failure section
                result_md = f"""
---

## LinkedIn Post Failed

**Status:** ❌ Failed
**Error:** {result.get('error', 'Unknown error')}

### Retry Options

- Check MCP server is running
- Verify task has required fields
- Retry publishing
"""
            
            new_content = content + result_md
            
            with open(task_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"Task file updated: {task_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to update task file: {e}")
    
    def write_activity_log(self, post_data: Dict, result: Dict):
        """Write LinkedIn activity to log."""
        try:
            log_file = self.logs_dir / "activity_log.md"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Create log file if doesn't exist
            if not log_file.exists():
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write("timestamp | action | file | status\n")
            
            # Write entry
            status = "linkedin_posted" if result.get('success') else "linkedin_failed"
            topic = post_data.get('topic', 'unknown')
            log_entry = f"{timestamp} | {status} | {topic} | {result.get('message', result.get('error', ''))}\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            logger.debug("Activity log updated")
            
        except Exception as e:
            logger.error(f"Failed to write activity log: {e}")
    
    def process_linkedin_task(self, task_file: Path) -> bool:
        """Process a single LinkedIn marketing task."""
        task_name = task_file.name
        logger.info(f"Processing LinkedIn task: {task_name}")
        
        # Read task
        content, frontmatter = self.read_task(task_file)
        
        # Parse post details
        post_data = self.parse_linkedin_details(content, frontmatter)
        
        logger.info(f"  Topic: {post_data['topic']}")
        logger.info(f"  Audience: {post_data['audience']}")
        logger.info(f"  Key Points: {len(post_data['key_points'])}")
        
        # Generate and publish with retry logic
        retries = 0
        result = None
        analytics = {}
        
        while retries < self.MAX_RETRIES:
            result = self.generate_and_publish(post_data)
            
            if result.get('success'):
                logger.info(f"Post published successfully")
                
                # Get analytics
                post_id = result.get('post_id')
                if post_id:
                    analytics = self.get_analytics(post_id)
                
                break
            
            retries += 1
            logger.warning(f"Retry {retries}/{self.MAX_RETRIES} for {task_name}")
            
            if retries < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY)
        
        # Update task file
        self.update_task_file(task_file, result, analytics)
        
        # Save engagement summary
        self.save_engagement_summary(task_name, post_data, result, analytics)
        
        # Write activity log
        self.write_activity_log(post_data, result)
        
        # Mark as processed
        self.processed_tasks.add(task_name)
        
        return result.get('success', False)
    
    def scan_for_linkedin_tasks(self) -> List[Path]:
        """Scan Needs_Action for LinkedIn marketing tasks."""
        linkedin_tasks = []
        
        if not self.needs_action_dir.exists():
            return linkedin_tasks
        
        for file_path in self.needs_action_dir.iterdir():
            if (file_path.is_file() and 
                file_path.suffix.lower() == '.md' and
                file_path.name not in self.processed_tasks):
                
                # Check if it's a LinkedIn task
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check skill or LinkedIn indicators
                is_linkedin_task = (
                    'skill: linkedin_marketing' in content.lower() or
                    'skill:linkedin_marketing' in content.lower() or
                    ('linkedin' in content.lower() and 
                     ('post' in content.lower() or 'publish' in content.lower()))
                )
                
                if is_linkedin_task:
                    linkedin_tasks.append(file_path)
        
        return linkedin_tasks
    
    def run(self):
        """Main LinkedIn agent loop."""
        logger.info("=" * 60)
        logger.info("LinkedIn Agent started")
        logger.info(f"MCP Server: {self.MCP_HOST}:{self.MCP_PORT}")
        logger.info(f"Monitoring: {self.needs_action_dir}")
        logger.info(f"Marketing Logs: {self.marketing_dir}")
        logger.info("=" * 60)
        
        # Check MCP server
        if not self.check_mcp_server():
            logger.warning("LinkedIn MCP server not running")
            logger.info("")
            logger.info("To start MCP server:")
            logger.info("  python MCP/linkedin_mcp/linkedin_mcp_server.py")
            logger.info("")
        
        while True:
            try:
                # Scan for LinkedIn tasks
                tasks = self.scan_for_linkedin_tasks()
                
                if tasks:
                    logger.info(f"Found {len(tasks)} LinkedIn task(s)")
                    
                    for task_file in tasks:
                        self.process_linkedin_task(task_file)
                    
                    logger.info("Waiting for more tasks...")
                
                # Wait before next scan
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("")
                logger.info("LinkedIn Agent stopping...")
                break
            except Exception as e:
                logger.error(f"Error in LinkedIn agent loop: {e}")
                time.sleep(5)


# Import time for retry logic
import time

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    agent = LinkedInAgent(
        needs_action_dir=BASE_DIR / "Needs_Action",
        logs_dir=BASE_DIR / "Logs",
        marketing_dir=BASE_DIR / "Logs" / "Marketing"
    )
    agent.run()
