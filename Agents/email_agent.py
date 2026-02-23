#!/usr/bin/env python3
"""
Email Agent - Silver Tier AI Employee

Specialized agent for sending emails via the Email MCP Server.
Does not send emails directly - always routes through MCP server.

Capabilities:
- Read email tasks from Needs_Action
- Parse email details (to, subject, body, cc, bcc)
- Call MCP server HTTP API
- Handle success/failure responses
- Log email activity

MCP Server:
- Host: localhost
- Port: 8765
- Endpoint: POST /send

Usage:
    python email_agent.py

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
logger = logging.getLogger("EmailAgent")


class EmailAgent:
    """
    Email Agent - Sends emails via MCP server.
    
    All email operations are routed through the Email MCP Server
    for security and centralized management.
    """
    
    # MCP Server configuration
    MCP_HOST = os.getenv("EMAIL_MCP_HOST", "127.0.0.1")
    MCP_PORT = int(os.getenv("EMAIL_MCP_PORT", "8765"))
    MCP_URL = f"http://{MCP_HOST}:{MCP_PORT}/send"
    
    # Retry configuration
    MAX_RETRIES = 3
    RETRY_DELAY = 5  # seconds
    
    def __init__(self, needs_action_dir: Path, logs_dir: Path):
        self.needs_action_dir = needs_action_dir
        self.logs_dir = logs_dir
        self.processed_tasks: set = set()
        
        # Ensure directories exist
        self.needs_action_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
    
    def check_mcp_server(self) -> bool:
        """Check if MCP server is running."""
        try:
            url = f"http://{self.MCP_HOST}:{self.MCP_PORT}/health"
            req = urllib.request.Request(url, method='GET')
            
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    logger.info("MCP server is healthy")
                    return True
        except Exception as e:
            logger.warning(f"MCP server not available: {e}")
        
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
    
    def parse_email_details(self, content: str, frontmatter: Dict) -> Dict:
        """Parse email details from task content."""
        email_data = {
            'to': frontmatter.get('to', ''),
            'subject': frontmatter.get('subject', ''),
            'body': '',
            'html': frontmatter.get('html', 'false').lower() == 'true',
            'cc': frontmatter.get('cc'),
            'bcc': frontmatter.get('bcc'),
            'priority': frontmatter.get('priority', 'normal')
        }
        
        # Try to extract from content if not in frontmatter
        if not email_data['to']:
            to_match = re.search(r'\*\*To:\*\*\s*([^\n]+)', content)
            if to_match:
                email_data['to'] = to_match.group(1).strip()
        
        if not email_data['subject']:
            subject_match = re.search(r'\*\*Subject:\*\*\s*([^\n]+)', content)
            if subject_match:
                email_data['subject'] = subject_match.group(1).strip()
        
        # Extract body from content
        body_match = re.search(r'## Content\s*\n(.*?)(?=## |$)', content, re.DOTALL)
        if body_match:
            email_data['body'] = body_match.group(1).strip()
        else:
            # Use remaining content as body
            email_data['body'] = content.strip()
        
        # If still no body, use title
        if not email_data['body']:
            email_data['body'] = frontmatter.get('title', 'Email from AI Employee')
        
        return email_data
    
    def send_via_mcp(self, email_data: Dict) -> Dict:
        """Send email via MCP server HTTP API."""
        # Prepare request
        request_data = {
            'to': email_data['to'],
            'subject': email_data['subject'],
            'body': email_data['body'],
            'html': email_data['html'],
            'priority': email_data['priority'],
            'agent_id': 'email_agent'
        }
        
        if email_data.get('cc'):
            request_data['cc'] = email_data['cc']
        if email_data.get('bcc'):
            request_data['bcc'] = email_data['bcc']
        
        # Build HTTP request
        json_data = json.dumps(request_data).encode('utf-8')
        req = urllib.request.Request(
            self.MCP_URL,
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
    
    def update_task_file(self, task_file: Path, result: Dict):
        """Update task file with email send result."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if result.get('success'):
                # Add success section
                result_md = f"""
---

## Email Sent

**Status:** ✅ Delivered
**To:** {result.get('to', 'Unknown')}
**Subject:** {result.get('subject', 'Unknown')}
**Sent:** {timestamp}
**Demo Mode:** {result.get('demo', False)}

### Response

```json
{json.dumps(result, indent=2)}
```
"""
            else:
                # Add failure section
                result_md = f"""
---

## Email Failed

**Status:** ❌ Failed
**Error:** {result.get('error', 'Unknown error')}

### Retry Information

- Check MCP server is running
- Verify recipient email address
- Check SMTP configuration
"""
            
            # Update frontmatter status
            if result.get('success'):
                content = re.sub(
                    r'(status:\s*)[^\n]+',
                    r'\1done',
                    content,
                    flags=re.MULTILINE
                )
                # Add completed timestamp
                if 'completed:' not in content:
                    content = re.sub(
                        r'(status:\s*done)',
                        f'\\1\ncompleted: {timestamp}',
                        content
                    )
            
            # Append result
            new_content = content + result_md
            
            with open(task_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"Task file updated: {task_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to update task file: {e}")
    
    def write_activity_log(self, email_data: Dict, result: Dict):
        """Write email activity to log."""
        try:
            log_file = self.logs_dir / "activity_log.md"
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Create log file if doesn't exist
            if not log_file.exists():
                with open(log_file, 'w', encoding='utf-8') as f:
                    f.write("timestamp | action | file | status\n")
            
            # Write entry
            status = "email_sent" if result.get('success') else "email_failed"
            to_addr = email_data.get('to', 'unknown')
            log_entry = f"{timestamp} | {status} | {to_addr} | {result.get('message', result.get('error', ''))}\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
            logger.debug("Activity log updated")
            
        except Exception as e:
            logger.error(f"Failed to write activity log: {e}")
    
    def process_email_task(self, task_file: Path) -> bool:
        """Process a single email task."""
        task_name = task_file.name
        logger.info(f"Processing email task: {task_name}")
        
        # Read task
        content, frontmatter = self.read_task(task_file)
        
        # Parse email details
        email_data = self.parse_email_details(content, frontmatter)
        
        logger.info(f"  To: {email_data['to']}")
        logger.info(f"  Subject: {email_data['subject']}")
        logger.info(f"  Priority: {email_data['priority']}")
        
        # Validate required fields
        if not email_data['to']:
            logger.error("Missing recipient email address")
            self.update_task_file(task_file, {
                'success': False,
                'error': 'Missing recipient email address (to)'
            })
            return False
        
        if not email_data['subject']:
            email_data['subject'] = frontmatter.get('title', 'Email from AI Employee')
        
        # Send with retry logic
        retries = 0
        result = None
        
        while retries < self.MAX_RETRIES:
            result = self.send_via_mcp(email_data)
            
            if result.get('success'):
                logger.info(f"Email sent successfully to: {email_data['to']}")
                break
            
            retries += 1
            logger.warning(f"Retry {retries}/{self.MAX_RETRIES} for {task_name}")
            
            if retries < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY)
        
        # Update task file
        self.update_task_file(task_file, result)
        
        # Write activity log
        self.write_activity_log(email_data, result)
        
        # Mark as processed
        self.processed_tasks.add(task_name)
        
        return result.get('success', False)
    
    def scan_for_email_tasks(self) -> List[Path]:
        """Scan Needs_Action for email tasks."""
        email_tasks = []
        
        if not self.needs_action_dir.exists():
            return email_tasks
        
        for file_path in self.needs_action_dir.iterdir():
            if (file_path.is_file() and 
                file_path.suffix.lower() == '.md' and
                file_path.name not in self.processed_tasks):
                
                # Check if it's an email task
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check skill or email indicators
                is_email_task = (
                    'skill: email' in content.lower() or
                    'skill:email' in content.lower() or
                    ('send' in content.lower() and 'email' in content.lower())
                )
                
                if is_email_task:
                    email_tasks.append(file_path)
        
        return email_tasks
    
    def run(self):
        """Main email agent loop."""
        logger.info("=" * 60)
        logger.info("Email Agent started")
        logger.info(f"MCP Server: {self.MCP_URL}")
        logger.info(f"Monitoring: {self.needs_action_dir}")
        logger.info("=" * 60)
        
        # Check MCP server
        if not self.check_mcp_server():
            logger.warning("MCP server not running - starting in standalone mode")
            logger.warning("Emails will fail until MCP server is started")
            logger.info("")
            logger.info("To start MCP server:")
            logger.info("  python MCP/email_mcp/email_mcp_server.py")
            logger.info("")
        
        while True:
            try:
                # Scan for email tasks
                tasks = self.scan_for_email_tasks()
                
                if tasks:
                    logger.info(f"Found {len(tasks)} email task(s)")
                    
                    for task_file in tasks:
                        self.process_email_task(task_file)
                    
                    logger.info("Waiting for more tasks...")
                
                # Wait before next scan
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("")
                logger.info("Email Agent stopping...")
                break
            except Exception as e:
                logger.error(f"Error in email agent loop: {e}")
                time.sleep(5)


# Import time for retry logic
import time

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    agent = EmailAgent(
        needs_action_dir=BASE_DIR / "Needs_Action",
        logs_dir=BASE_DIR / "Logs"
    )
    agent.run()
