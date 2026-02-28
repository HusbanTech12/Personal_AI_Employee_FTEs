#!/usr/bin/env python3
"""
Gmail Watcher - Silver Tier AI Employee

Monitors Gmail for new emails and converts them into markdown tasks.
Saves tasks to /Inbox folder for processing by the AI Employee system.

NOTE: For production use, configure Gmail API credentials.
This implementation uses IMAP for demonstration purposes.

Requirements:
    pip install imaplib2 email python-dotenv

Usage:
    python gmail_watcher.py

Stop:
    Press Ctrl+C to gracefully stop monitoring
"""

import os
import sys
import time
import logging
import re
import email
import imaplib
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Set
from email.header import decode_header
from email.message import Message as EmailMessage
from dotenv import load_dotenv

# =============================================================================
# Secure Credential Loading
# =============================================================================

# Load credentials from Config/credentials.env
BASE_DIR = Path(__file__).parent.parent.resolve()

# Centralized vault path - all Obsidian vault folders are relative to this
VAULT_PATH = BASE_DIR / "notes"

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
logger = logging.getLogger("GmailWatcher")


class GmailWatcher:
    """
    Gmail Watcher for AI Employee Vault.

    Monitors Gmail inbox and converts emails to markdown tasks.
    """

    # Configuration - Loaded securely from credentials.env
    IMAP_SERVER = os.getenv("GMAIL_IMAP_SERVER", "imap.gmail.com")
    IMAP_PORT = int(os.getenv("GMAIL_IMAP_PORT", "993"))
    EMAIL_USER = os.getenv("GMAIL_ADDRESS", "")
    EMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD", "")  # Use App Password

    # Polling interval in seconds
    POLL_INTERVAL = 30

    # Processed email IDs to avoid duplicates
    processed_emails: Set[str] = set()

    # Connection state
    is_connected: bool = False

    def __init__(self, inbox_dir: Path, logs_dir: Path):
        self.inbox_dir = inbox_dir
        self.logs_dir = logs_dir
        self.last_check = datetime.now()

        # Ensure directories exist
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def validate_credentials(self) -> bool:
        """
        Validate that required credentials are configured.
        Returns True if credentials are present, False otherwise.
        """
        if not self.EMAIL_USER:
            logger.warning("[GMAIL] GMAIL_ADDRESS not configured")
            return False

        if not self.EMAIL_PASSWORD:
            logger.warning("[GMAIL] GMAIL_PASSWORD not configured")
            return False

        # Basic validation (not checking password strength for security)
        if len(self.EMAIL_PASSWORD) < 8:
            logger.warning("[GMAIL] Password appears too short - ensure you're using an App Password")

        logger.info("[GMAIL] Credentials validated successfully")
        return True

    def connect_to_gmail(self) -> Optional[imaplib.IMAP4_SSL]:
        """Connect to Gmail IMAP server."""
        try:
            if not self.EMAIL_USER or not self.EMAIL_PASSWORD:
                logger.warning("[GMAIL] Credentials not configured. Running in demo mode.")
                return None

            mail = imaplib.IMAP4_SSL(self.IMAP_SERVER, self.IMAP_PORT)
            mail.login(self.EMAIL_USER, self.EMAIL_PASSWORD)
            mail.select("inbox")

            self.is_connected = True
            logger.info("[GMAIL CONNECTED]")
            return mail

        except imaplib.IMAP4.error as e:
            self.is_connected = False
            logger.error(f"[GMAIL] Authentication failed: {e}")
            return None

        except Exception as e:
            self.is_connected = False
            logger.error(f"[GMAIL] Connection failed: {e}")
            return None
    
    def decode_mime_word(self, mime_word: str) -> str:
        """Decode MIME encoded word."""
        if not mime_word:
            return ""
        
        decoded = decode_header(mime_word)
        result = ""
        
        for text, encoding in decoded:
            if isinstance(text, bytes):
                try:
                    result += text.decode(encoding or 'utf-8')
                except (UnicodeDecodeError, LookupError):
                    result += text.decode('utf-8', errors='replace')
            else:
                result += text
        
        return result
    
    def decode_email_subject(self, subject: str) -> str:
        """Decode email subject line."""
        return self.decode_mime_word(subject)
    
    def get_email_body(self, msg: EmailMessage) -> str:
        """Extract plain text body from email."""
        body = ""
        
        if msg.is_multipart():
            # Prefer plain text part
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition") or "")
                
                # Skip attachments
                if "attachment" in content_disposition:
                    continue
                
                if content_type == "text/plain":
                    try:
                        charset = part.get_content_charset() or 'utf-8'
                        body = part.get_payload(decode=True).decode(charset, errors='replace')
                        break
                    except Exception:
                        continue
            
            # Fallback to HTML if no plain text
            if not body:
                for part in msg.walk():
                    if part.get_content_type() == "text/html":
                        try:
                            html = part.get_payload(decode=True).decode('utf-8', errors='replace')
                            # Simple HTML to text conversion
                            body = re.sub(r'<[^>]+>', '', html)
                        except Exception:
                            continue
        else:
            # Not multipart
            try:
                charset = msg.get_content_charset() or 'utf-8'
                body = msg.get_payload(decode=True).decode(charset, errors='replace')
            except Exception:
                body = str(msg.get_payload())
        
        return body.strip()
    
    def determine_priority(self, subject: str, sender: str) -> str:
        """Determine task priority based on email content."""
        subject_lower = subject.lower()
        sender_lower = sender.lower()
        
        # High priority indicators
        high_priority = ['urgent', 'asap', 'critical', 'important', 'action required',
                         'immediate', 'deadline', 'priority']
        
        # Medium priority indicators
        medium_priority = ['review', 'update', 'meeting', 'schedule', 'reminder']
        
        for keyword in high_priority:
            if keyword in subject_lower:
                return "high"
        
        for keyword in medium_priority:
            if keyword in subject_lower:
                return "medium"
        
        # Check if from important sender (customize as needed)
        important_domains = ['company.com', 'boss.com', 'client.com']
        for domain in important_domains:
            if domain in sender_lower:
                return "medium"
        
        return "standard"
    
    def extract_action_items(self, body: str) -> List[str]:
        """Extract potential action items from email body."""
        action_items = []
        
        # Look for bullet points
        bullets = re.findall(r'^[\s]*[-*•]\s*(.+)$', body, re.MULTILINE)
        action_items.extend([b.strip() for b in bullets[:5]])
        
        # Look for numbered lists
        numbered = re.findall(r'^[\s]*\d+\.\s*(.+)$', body, re.MULTILINE)
        action_items.extend([n.strip() for n in numbered[:5]])
        
        # Look for lines with action verbs
        action_verbs = ['please', 'need to', 'should', 'must', 'have to', 'required']
        for line in body.split('\n'):
            line = line.strip()
            if len(line) < 200:  # Reasonable line length
                for verb in action_verbs:
                    if verb in line.lower() and line not in action_items:
                        action_items.append(line)
                        break
        
        return action_items[:10]  # Limit to 10 items
    
    def create_task_markdown(self, subject: str, sender: str, body: str, 
                             received_date: str, action_items: List[str]) -> str:
        """Create markdown task from email."""
        priority = self.determine_priority(subject, sender)
        
        # Clean subject for filename
        clean_subject = re.sub(r'[^\w\s-]', '', subject)[:50].strip()
        clean_subject = clean_subject.replace(' ', '_').lower()
        
        # Build task content
        task_content = f"""---
title: {subject}
status: needs_action
priority: {priority}
created: {received_date}
skill: task_processor
source: Gmail
sender: {sender}
---

# Email Task: {subject}

**From:** {sender}

**Received:** {received_date}

**Source:** Gmail

**Priority:** {priority.title()}

---

## Email Content

{body[:2000]}{'...' if len(body) > 2000 else ''}

---

## Action Items

"""
        
        if action_items:
            for item in action_items:
                task_content += f"- [ ] {item}\n"
        else:
            task_content += "- [ ] Review and process this email\n"
        
        task_content += f"""
---

## Notes

- Automatically imported from Gmail
- Original email should be reviewed for complete context
- Priority auto-assigned based on content analysis
"""
        
        return task_content, clean_subject
    
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
    
    def fetch_new_emails(self, mail: imaplib.IMAP4_SSL) -> List[Dict]:
        """Fetch new emails since last check."""
        new_emails = []
        
        try:
            # Search for unseen emails
            _, message_ids = mail.search(None, "UNSEEN")
            
            for msg_id in message_ids[0].split():
                msg_id_str = msg_id.decode('utf-8')
                
                # Skip already processed
                if msg_id_str in self.processed_emails:
                    continue
                
                # Fetch email
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Extract email data
                        subject = self.decode_email_subject(msg.get('Subject', 'No Subject'))
                        sender = self.decode_mime_word(msg.get('From', 'Unknown'))
                        date = msg.get('Date', '')
                        
                        # Parse date
                        try:
                            received_date = datetime.strptime(date[:19], '%a, %d %b %Y %H:%M:%S')
                            received_str = received_date.strftime('%Y-%m-%d %H:%M:%S')
                        except (ValueError, IndexError):
                            received_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        
                        # Get body
                        body = self.get_email_body(msg)
                        
                        # Extract action items
                        action_items = self.extract_action_items(body)
                        
                        new_emails.append({
                            'id': msg_id_str,
                            'subject': subject,
                            'sender': sender,
                            'received': received_str,
                            'body': body,
                            'action_items': action_items
                        })
                        
                        # Mark as processed
                        self.processed_emails.add(msg_id_str)
        
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
        
        return new_emails
    
    def generate_demo_email(self) -> Dict:
        """Generate a demo email for testing (when no Gmail connection)."""
        demo_emails = [
            {
                'subject': 'Review Q4 Budget Proposal',
                'sender': 'manager@company.com',
                'received': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'body': '''Hi Team,

Please review the attached Q4 budget proposal and provide feedback by end of week.

Key items to review:
- Marketing budget allocation
- Headcount planning
- Technology investments
- Operational expenses

Let me know if you have any questions.

Thanks,
Manager''',
                'action_items': [
                    'Review Q4 budget proposal',
                    'Provide feedback on marketing budget',
                    'Review headcount planning'
                ]
            },
            {
                'subject': 'Meeting Reminder: Sprint Planning Tomorrow',
                'sender': 'scrum@company.com',
                'received': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'body': '''This is a reminder that Sprint Planning is scheduled for tomorrow at 10 AM.

Agenda:
1. Review sprint goals
2. Estimate story points
3. Assign tasks

Please come prepared with your capacity and availability.

See you there!''',
                'action_items': [
                    'Attend sprint planning meeting',
                    'Prepare capacity and availability'
                ]
            },
            {
                'subject': 'URGENT: Server Maintenance Required',
                'sender': 'alerts@monitoring.com',
                'received': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'body': '''ALERT: Production server requires immediate attention.

Issue: High CPU usage detected on web-server-01
Threshold: 90%
Current: 95%

Action Required:
- Investigate root cause
- Scale resources if needed
- Update incident ticket

This is an automated alert.''',
                'action_items': [
                    'Investigate high CPU usage',
                    'Scale resources if needed',
                    'Update incident ticket'
                ]
            }
        ]
        
        import random
        demo = random.choice(demo_emails).copy()
        demo['id'] = f"demo_{datetime.now().timestamp()}"
        return demo
    
    def process_email(self, email_data: Dict):
        """Process a single email and create task."""
        task_content, filename = self.create_task_markdown(
            subject=email_data['subject'],
            sender=email_data['sender'],
            body=email_data['body'],
            received_date=email_data['received'],
            action_items=email_data['action_items']
        )
        
        self.save_task(task_content, filename)
    
    def run_demo_mode(self):
        """Run in demo mode without Gmail connection."""
        logger.info("Running in DEMO mode - generating sample emails")
        
        # Generate demo email
        demo_email = self.generate_demo_email()
        self.process_email(demo_email)
        
        logger.info(f"Demo email processed: {demo_email['subject']}")
    
    def run(self):
        """Main watcher loop."""
        logger.info("Gmail Watcher starting...")
        logger.info(f"Monitoring inbox, saving to: {self.inbox_dir}")
        logger.info(f"Poll interval: {self.POLL_INTERVAL} seconds")

        # Validate credentials at startup
        credentials_valid = self.validate_credentials()

        if not credentials_valid:
            logger.warning("[GMAIL] Running in DEMO mode - no credentials configured")
            logger.warning("[GMAIL] System will continue but Gmail monitoring is disabled")

        demo_mode = False

        while True:
            try:
                # Try to connect to Gmail
                mail = self.connect_to_gmail()

                if mail:
                    # Fetch and process new emails
                    new_emails = self.fetch_new_emails(mail)

                    for email_data in new_emails:
                        self.process_email(email_data)

                    if new_emails:
                        logger.info(f"Processed {len(new_emails)} new email(s)")

                    # Close connection
                    mail.close()
                    mail.logout()
                else:
                    # No credentials - run demo mode periodically
                    if not demo_mode:
                        logger.debug("[GMAIL] No Gmail credentials - skipping (demo mode available)")

                # Wait for next poll
                time.sleep(self.POLL_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Gmail Watcher stopping...")
                break
            except Exception as e:
                logger.error(f"Error in Gmail watcher: {e}")
                time.sleep(self.POLL_INTERVAL)


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent.resolve()

    # Centralized vault path - all Obsidian vault folders are relative to this
    VAULT_PATH = BASE_DIR / "notes"

    watcher = GmailWatcher(
        inbox_dir=VAULT_PATH / "Inbox",
        logs_dir=BASE_DIR / "Logs"
    )
    watcher.run()
