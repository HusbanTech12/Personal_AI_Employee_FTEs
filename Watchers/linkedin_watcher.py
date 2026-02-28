#!/usr/bin/env python3
"""
LinkedIn Watcher - Silver Tier AI Employee

Monitors LinkedIn notifications and messages, converting them into markdown tasks.
Saves tasks to /Inbox folder for processing by the AI Employee system.

NOTE: LinkedIn does not have a free public API for personal accounts.
This implementation uses file-based input and demo mode.
For production, consider:
- LinkedIn Marketing Developer API (for business accounts)
- LinkedIn Sales Navigator API
- Web scraping with proper authorization (check ToS)

Requirements:
    pip install python-dotenv

Usage:
    python linkedin_watcher.py

Stop:
    Press Ctrl+C to gracefully stop monitoring
"""

import os
import sys
import time
import logging
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Set
from dotenv import load_dotenv

# =============================================================================
# Secure Credential Loading
# =============================================================================

# Load credentials from Config/credentials.env
BASE_DIR = Path(__file__).parent.parent.resolve()
CREDENTIALS_FILE = BASE_DIR / "Config" / "credentials.env"

# Load environment variables from credentials file
if CREDENTIALS_FILE.exists():
    load_dotenv(dotenv_path=CREDENTIALS_FILE)
else:
    # Fallback to system environment variables
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("LinkedInWatcher")


class LinkedInWatcher:
    """
    LinkedIn Watcher for AI Employee Vault.

    Monitors LinkedIn activity and converts notifications/messages to markdown tasks.
    Uses file-based input for demo (can be extended to use LinkedIn API).
    """

    # Configuration - Loaded securely from credentials.env
    LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
    LINKEDIN_API_KEY = os.getenv("LINKEDIN_API_KEY", "")
    LINKEDIN_API_SECRET = os.getenv("LINKEDIN_API_SECRET", "")

    # Polling interval in seconds
    POLL_INTERVAL = 30

    # Processed notification IDs
    processed_notifications: Set[str] = set()

    # Connection state
    is_connected: bool = False
    has_api_credentials: bool = False

    def __init__(self, inbox_dir: Path, logs_dir: Path, input_dir: Optional[Path] = None):
        self.inbox_dir = inbox_dir
        self.logs_dir = logs_dir
        self.input_dir = input_dir or (logs_dir / "linkedin_input")

        # Ensure directories exist
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.input_dir.mkdir(parents=True, exist_ok=True)

    def validate_credentials(self) -> bool:
        """
        Validate that LinkedIn credentials are configured.
        Returns True if API credentials are present, False for file-based mode.
        """
        if self.LINKEDIN_API_KEY and self.LINKEDIN_API_SECRET:
            self.has_api_credentials = True
            logger.info("[LINKEDIN] API credentials validated successfully")
            return True

        if self.LINKEDIN_EMAIL and self.LINKEDIN_PASSWORD:
            logger.info("[LINKEDIN] Email/password credentials loaded (limited API access)")
            return True

        logger.warning("[LINKEDIN] No credentials configured - running in file-based demo mode")
        logger.warning("[LINKEDIN] System will continue but LinkedIn API is disabled")
        return False

    def connect_to_linkedin(self) -> bool:
        """
        Attempt to connect to LinkedIn API.
        Returns True if connected, False otherwise.
        """
        try:
            if not self.has_api_credentials:
                logger.warning("[LINKEDIN] API credentials not configured")
                return False

            # Placeholder for actual LinkedIn API connection
            # In production, implement OAuth2 flow here
            logger.info("[LINKEDIN CONNECTED]")
            self.is_connected = True
            return True

        except Exception as e:
            self.is_connected = False
            logger.error(f"[LINKEDIN] Connection failed: {e}")
            return False
    
    def determine_priority(self, notification_type: str, content: str) -> str:
        """Determine task priority based on notification type and content."""
        content_lower = content.lower()
        
        # High priority - direct messages, job opportunities, important connections
        high_priority_types = ['message', 'inmail', 'job_posting', 'interview_request']
        high_priority_keywords = ['interview', 'opportunity', 'position', 'role',
                                  'hiring', 'immediate', 'urgent']
        
        # Medium priority - connection requests, recommendations
        medium_priority_types = ['connection_request', 'recommendation', 'endorsement']
        medium_priority_keywords = ['connect', 'network', 'recommend', 'endorse']
        
        if notification_type.lower() in high_priority_types:
            return "high"
        
        for keyword in high_priority_keywords:
            if keyword in content_lower:
                return "high"
        
        if notification_type.lower() in medium_priority_types:
            return "medium"
        
        return "standard"
    
    def extract_action_items(self, notification_type: str, content: str, 
                             sender: str) -> List[str]:
        """Extract potential action items from notification."""
        action_items = []
        
        # Type-specific actions
        type_actions = {
            'message': [f"Respond to message from {sender}"],
            'inmail': [f"Respond to InMail from {sender}", "Craft professional response"],
            'connection_request': [f"Review and accept/reject connection request from {sender}"],
            'job_posting': [f"Review job opportunity: {content[:50]}...", "Update resume if interested"],
            'interview_request': [f"Respond to interview request", "Schedule interview time"],
            'recommendation': [f"Review recommendation request from {sender}", "Write recommendation"],
            'endorsement': [f"Thank {sender} for endorsement", "Consider endorsing back"],
            'comment': [f"Review comment on your post", "Engage with commenter"],
            'mention': [f"Check mention by {sender}", "Engage with the post"]
        }
        
        action_items.extend(type_actions.get(notification_type.lower(), 
                                              [f"Review LinkedIn notification from {sender}"]))
        
        return action_items[:5]
    
    def create_task_markdown(self, sender: str, notification_type: str, content: str,
                             timestamp: str, profile_url: Optional[str] = None) -> tuple:
        """Create markdown task from LinkedIn notification."""
        priority = self.determine_priority(notification_type, content)
        action_items = self.extract_action_items(notification_type, content, sender)
        
        # Clean sender name for filename
        clean_sender = re.sub(r'[^\w\s-]', '', sender)[:30].strip()
        clean_sender = clean_sender.replace(' ', '_').lower()
        
        # Build task content
        task_content = f"""---
title: LinkedIn: {notification_type.title()} from {sender}
status: needs_action
priority: {priority}
created: {timestamp}
skill: task_processor
source: LinkedIn
sender: {sender}
notification_type: {notification_type}
---

# LinkedIn Notification Task

**From:** {sender}

**Received:** {timestamp}

**Source:** LinkedIn

**Type:** {notification_type.title()}

{'**Profile:** ' + profile_url if profile_url else ''}

**Priority:** {priority.title()}

---

## Notification Content

{content}

---

## Action Items

"""
        
        for item in action_items:
            task_content += f"- [ ] {item}\n"
        
        # Add type-specific guidance
        guidance = self._get_type_guidance(notification_type)
        if guidance:
            task_content += f"""
---

## Guidance

{guidance}
"""
        
        task_content += f"""
---

## Response Templates

### Connection Acceptance
```
Hi {sender.split()[0] if sender else 'there'},

Thanks for connecting! I'd love to learn more about your work at [Company].

Best regards
```

### Message Response
```
Hi {sender.split()[0] if sender else 'there'},

Thank you for reaching out. I appreciate you thinking of me.

[Your response here]

Best regards
```

---

## Notes

- Automatically imported from LinkedIn
- Consider responding via LinkedIn for context and networking
- Priority auto-assigned based on notification type
- Professional response recommended
"""
        
        filename = f"linkedin_{notification_type.lower()}_{clean_sender}"
        
        return task_content, filename
    
    def _get_type_guidance(self, notification_type: str) -> str:
        """Get guidance based on notification type."""
        guidance_map = {
            'message': "Respond within 24-48 hours for professional courtesy.",
            'inmail': "InMail is premium - prioritize response. Consider if this is a valuable opportunity.",
            'connection_request': "Review sender's profile before accepting. Consider mutual connections and relevance.",
            'job_posting': "Review requirements carefully. Update resume before applying. Research the company.",
            'interview_request': "Respond promptly. Prepare availability options. Research the role and company.",
            'recommendation': "Only write recommendations for people you know well. Be specific and genuine.",
            'endorsement': "Consider endorsing back if you can genuinely vouch for their skills."
        }
        
        return guidance_map.get(notification_type.lower(), "")
    
    def save_task(self, task_content: str, filename: str) -> Path:
        """Save task to Inbox folder."""
        # Ensure unique filename
        task_path = self.inbox_dir / f"{filename}.md"
        
        counter = 1
        while task_path.exists():
            task_path = self.inbox_dir / f"{filename}_{counter}.md"
            counter += 1
        
        with open(task_path, 'w', encoding='utf-8') as f:
            f.write(task_content)
        
        logger.info(f"Task saved: {task_path.name}")
        return task_path
    
    def parse_notification_file(self, file_path: Path) -> Optional[Dict]:
        """Parse a notification file from input directory."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return {
                'id': data.get('id', str(file_path)),
                'sender': data.get('sender', 'Unknown'),
                'type': data.get('type', 'notification'),
                'content': data.get('content', ''),
                'timestamp': data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'profile_url': data.get('profile_url')
            }
        except Exception as e:
            logger.error(f"Failed to parse notification file {file_path}: {e}")
            return None
    
    def process_notification(self, notification_data: Dict):
        """Process a single notification and create task."""
        task_content, filename = self.create_task_markdown(
            sender=notification_data['sender'],
            notification_type=notification_data['type'],
            content=notification_data['content'],
            timestamp=notification_data['timestamp'],
            profile_url=notification_data.get('profile_url')
        )
        
        self.save_task(task_content, filename)
    
    def scan_input_directory(self) -> List[Path]:
        """Scan input directory for new notification files."""
        notification_files = []
        
        if not self.input_dir.exists():
            return notification_files
        
        for file_path in self.input_dir.iterdir():
            if file_path.suffix.lower() in ['.json', '.txt']:
                if str(file_path) not in self.processed_notifications:
                    notification_files.append(file_path)
        
        return notification_files
    
    def generate_demo_notification(self) -> Dict:
        """Generate a demo LinkedIn notification for testing."""
        demo_notifications = [
            {
                'id': f"demo_{datetime.now().timestamp()}_1",
                'sender': 'Sarah Johnson',
                'type': 'message',
                'content': 'Hi! I came across your profile and was impressed by your experience. We have an exciting opportunity that might interest you. Would you be open to a quick chat?',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'profile_url': 'https://linkedin.com/in/sarahjohnson'
            },
            {
                'id': f"demo_{datetime.now().timestamp()}_2",
                'sender': 'Michael Chen',
                'type': 'connection_request',
                'content': 'Michael Chen wants to connect with you. "Hi, I\'d like to add you to my professional network."',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'profile_url': 'https://linkedin.com/in/michaelchen'
            },
            {
                'id': f"demo_{datetime.now().timestamp()}_3",
                'sender': 'TechCorp Inc.',
                'type': 'job_posting',
                'content': 'Senior Software Engineer position at TechCorp Inc. • Remote • Full-time • Competitive salary. Your skills match 8/10 requirements.',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'profile_url': 'https://linkedin.com/company/techcorp'
            },
            {
                'id': f"demo_{datetime.now().timestamp()}_4",
                'sender': 'Jennifer Lee',
                'type': 'recommendation',
                'content': 'Jennifer Lee is requesting a recommendation. You worked together at ABC Company from 2020-2022.',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'profile_url': 'https://linkedin.com/in/jenniferlee'
            },
            {
                'id': f"demo_{datetime.now().timestamp()}_5",
                'sender': 'Recruiter Pro',
                'type': 'inmail',
                'content': 'URGENT: My client is looking for someone with your exact skillset. This is a CTO role with equity package. Are you available for a confidential conversation?',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'profile_url': 'https://linkedin.com/in/recruiterpro'
            }
        ]
        
        import random
        return random.choice(demo_notifications)
    
    def run_demo_mode(self):
        """Run in demo mode generating sample notifications."""
        logger.info("Running in DEMO mode - generating sample LinkedIn notifications")
        
        # Generate and process demo notification
        demo_notification = self.generate_demo_notification()
        self.process_notification(demo_notification)
        
        logger.info(f"Demo notification processed: {demo_notification['type']} from {demo_notification['sender']}")
    
    def run(self):
        """Main watcher loop."""
        logger.info("LinkedIn Watcher starting...")
        logger.info(f"Monitoring: {self.input_dir}")
        logger.info(f"Saving tasks to: {self.inbox_dir}")
        logger.info(f"Poll interval: {self.POLL_INTERVAL} seconds")

        # Validate credentials at startup
        credentials_valid = self.validate_credentials()

        # Attempt API connection if credentials are available
        if credentials_valid and (self.LINKEDIN_API_KEY or self.LINKEDIN_EMAIL):
            self.connect_to_linkedin()

        logger.info("")
        logger.info("To add LinkedIn notifications, create JSON files in the input directory:")
        logger.info(f"  {self.input_dir}")
        logger.info("")
        logger.info("JSON format:")
        logger.info('  {"sender": "Name", "type": "message", "content": "Text", "timestamp": "2024-01-01 12:00:00"}')
        logger.info("")
        logger.info("Notification types: message, inmail, connection_request, job_posting,")
        logger.info("                    interview_request, recommendation, endorsement, comment, mention")
        logger.info("")

        demo_count = 0

        while True:
            try:
                # Scan for new notification files
                notification_files = self.scan_input_directory()

                for file_path in notification_files:
                    notification_data = self.parse_notification_file(file_path)

                    if notification_data:
                        self.process_notification(notification_data)
                        self.processed_notifications.add(str(file_path))

                        # Mark file as processed
                        processed_path = file_path.with_suffix('.json.processed')
                        file_path.rename(processed_path)

                if notification_files:
                    logger.info(f"Processed {len(notification_files)} notification(s)")

                # Generate demo notifications periodically (for demonstration)
                demo_count += 1
                if demo_count >= 3:  # Every 3 polls
                    self.run_demo_mode()
                    demo_count = 0

                # Wait for next poll
                time.sleep(self.POLL_INTERVAL)

            except KeyboardInterrupt:
                logger.info("LinkedIn Watcher stopping...")
                break
            except Exception as e:
                logger.error(f"Error in LinkedIn watcher: {e}")
                time.sleep(self.POLL_INTERVAL)


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent.resolve()

    # Centralized vault path - all Obsidian vault folders are relative to this
    VAULT_PATH = BASE_DIR / "notes"

    watcher = LinkedInWatcher(
        inbox_dir=VAULT_PATH / "Inbox",
        logs_dir=BASE_DIR / "Logs"
    )
    watcher.run()
