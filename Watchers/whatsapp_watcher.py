#!/usr/bin/env python3
"""
WhatsApp Watcher - Silver Tier AI Employee

Monitors WhatsApp messages and converts them into markdown tasks.
Saves tasks to /Inbox folder for processing by the AI Employee system.

NOTE: WhatsApp does not have an official public API for personal accounts.
This implementation uses a file-based approach for demo purposes.
For production, consider:
- WhatsApp Business API
- Third-party services like Twilio
- Screen scraping (not recommended)

Requirements:
    None (standard library only)

Usage:
    python whatsapp_watcher.py

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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("WhatsAppWatcher")


class WhatsAppWatcher:
    """
    WhatsApp Watcher for AI Employee Vault.
    
    Monitors for WhatsApp messages and converts them to markdown tasks.
    Uses file-based input for demo (can be extended to use WhatsApp Business API).
    """
    
    # Configuration
    WATCHER_INPUT_DIR = None  # Directory to watch for message files
    POLL_INTERVAL = 15  # seconds
    
    # Processed message IDs
    processed_messages: Set[str] = set()
    
    def __init__(self, inbox_dir: Path, logs_dir: Path, input_dir: Optional[Path] = None):
        self.inbox_dir = inbox_dir
        self.logs_dir = logs_dir
        self.input_dir = input_dir or (logs_dir / "whatsapp_input")
        
        # Ensure directories exist
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.input_dir.mkdir(parents=True, exist_ok=True)
    
    def determine_priority(self, message: str, contact: str) -> str:
        """Determine task priority based on message content."""
        message_lower = message.lower()
        
        # High priority indicators
        high_priority = ['urgent', 'asap', 'emergency', 'critical', 'important',
                         'call me', 'call back', 'immediate', 'deadline']
        
        # Medium priority indicators
        medium_priority = ['meeting', 'tomorrow', 'today', 'reminder', 'please',
                           'can you', 'could you', 'when you get a chance']
        
        for keyword in high_priority:
            if keyword in message_lower:
                return "high"
        
        for keyword in medium_priority:
            if keyword in message_lower:
                return "medium"
        
        return "standard"
    
    def extract_action_items(self, message: str) -> List[str]:
        """Extract potential action items from message."""
        action_items = []
        
        # Look for lines with action indicators
        action_indicators = ['please ', 'need to ', 'have to ', 'must ', 'should ',
                             'can you ', 'could you ', 'will you ', 'action:']
        
        message_lower = message.lower()
        
        # Check for action indicators
        for indicator in action_indicators:
            if indicator in message_lower:
                # Extract the sentence/phrase
                sentences = re.split(r'[.!?]', message)
                for sentence in sentences:
                    if indicator in sentence.lower() and len(sentence.strip()) < 200:
                        action_items.append(sentence.strip())
        
        # Look for question marks (often indicate requests)
        questions = re.findall(r'([^?]+\?)', message)
        for question in questions[:3]:
            if len(question.strip()) > 10 and question not in action_items:
                action_items.append(question.strip())
        
        return list(set(action_items))[:5]  # Limit to 5 unique items
    
    def create_task_markdown(self, contact: str, message: str, timestamp: str,
                             message_type: str = "text", group: Optional[str] = None) -> tuple:
        """Create markdown task from WhatsApp message."""
        priority = self.determine_priority(message, contact)
        action_items = self.extract_action_items(message)
        
        # Clean contact name for filename
        clean_contact = re.sub(r'[^\w\s-]', '', contact)[:30].strip()
        clean_contact = clean_contact.replace(' ', '_').lower()
        
        # Clean message preview for filename
        message_preview = message[:30].replace(' ', '_').lower()
        message_preview = re.sub(r'[^\w-]', '', message_preview)
        
        # Build task content
        task_content = f"""---
title: WhatsApp: {message[:50]}{'...' if len(message) > 50 else ''}
status: needs_action
priority: {priority}
created: {timestamp}
skill: task_processor
source: WhatsApp
contact: {contact}
message_type: {message_type}
---

# WhatsApp Message Task

**From:** {contact}

**Received:** {timestamp}

**Source:** WhatsApp

**Type:** {message_type}

{'**Group:** ' + group if group else ''}

**Priority:** {priority.title()}

---

## Message Content

{message}

---

## Action Items

"""
        
        if action_items:
            for item in action_items:
                task_content += f"- [ ] {item}\n"
        else:
            task_content += "- [ ] Review and respond to this message\n"
        
        task_content += f"""
---

## Response Template

```
Hi {contact.split()[0] if contact else 'there'},

Thanks for your message. I'll get back to you soon.

Best regards
```

---

## Notes

- Automatically imported from WhatsApp
- Consider responding via WhatsApp for context
- Priority auto-assigned based on content analysis
"""
        
        filename = f"whatsapp_{clean_contact}_{message_preview}"
        
        return task_content, filename
    
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
    
    def parse_message_file(self, file_path: Path) -> Optional[Dict]:
        """Parse a message file from input directory."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return {
                'id': data.get('id', str(file_path)),
                'contact': data.get('contact', 'Unknown'),
                'message': data.get('message', ''),
                'timestamp': data.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'type': data.get('type', 'text'),
                'group': data.get('group')
            }
        except Exception as e:
            logger.error(f"Failed to parse message file {file_path}: {e}")
            return None
    
    def process_message(self, message_data: Dict):
        """Process a single message and create task."""
        task_content, filename = self.create_task_markdown(
            contact=message_data['contact'],
            message=message_data['message'],
            timestamp=message_data['timestamp'],
            message_type=message_data.get('type', 'text'),
            group=message_data.get('group')
        )
        
        self.save_task(task_content, filename)
    
    def scan_input_directory(self) -> List[Path]:
        """Scan input directory for new message files."""
        message_files = []
        
        if not self.input_dir.exists():
            return message_files
        
        for file_path in self.input_dir.iterdir():
            if file_path.suffix.lower() in ['.json', '.txt']:
                if str(file_path) not in self.processed_messages:
                    message_files.append(file_path)
        
        return message_files
    
    def generate_demo_message(self) -> Dict:
        """Generate a demo WhatsApp message for testing."""
        demo_messages = [
            {
                'id': f"demo_{datetime.now().timestamp()}_1",
                'contact': 'John Manager',
                'message': 'Hey, can you send me the project status update by EOD? Need it for the steering committee meeting tomorrow.',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'text',
                'group': None
            },
            {
                'id': f"demo_{datetime.now().timestamp()}_2",
                'contact': 'Sarah Team Lead',
                'message': 'URGENT: The client is asking about the deliverable. When can we ship?',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'text',
                'group': None
            },
            {
                'id': f"demo_{datetime.now().timestamp()}_3",
                'contact': 'Project Team',
                'message': 'Reminder: Team lunch at 12:30 today! Please confirm if you\'re coming.',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'text',
                'group': 'Project Team'
            },
            {
                'id': f"demo_{datetime.now().timestamp()}_4",
                'contact': 'Mom',
                'message': 'Call me when you get a chance. Love you!',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'type': 'text',
                'group': None
            }
        ]
        
        import random
        return random.choice(demo_messages)
    
    def run_demo_mode(self):
        """Run in demo mode generating sample messages."""
        logger.info("Running in DEMO mode - generating sample WhatsApp messages")
        
        # Generate and process demo message
        demo_message = self.generate_demo_message()
        self.process_message(demo_message)
        
        logger.info(f"Demo message processed from: {demo_message['contact']}")
    
    def run(self):
        """Main watcher loop."""
        logger.info("WhatsApp Watcher started")
        logger.info(f"Monitoring: {self.input_dir}")
        logger.info(f"Saving tasks to: {self.inbox_dir}")
        logger.info(f"Poll interval: {self.POLL_INTERVAL} seconds")
        logger.info("")
        logger.info("To add WhatsApp messages, create JSON files in the input directory:")
        logger.info(f"  {self.input_dir}")
        logger.info("")
        logger.info("JSON format:")
        logger.info('  {"contact": "Name", "message": "Text", "timestamp": "2024-01-01 12:00:00"}')
        logger.info("")
        
        demo_count = 0
        
        while True:
            try:
                # Scan for new message files
                message_files = self.scan_input_directory()
                
                for file_path in message_files:
                    message_data = self.parse_message_file(file_path)
                    
                    if message_data:
                        self.process_message(message_data)
                        self.processed_messages.add(str(file_path))
                        
                        # Mark file as processed
                        processed_path = file_path.with_suffix('.json.processed')
                        file_path.rename(processed_path)
                
                if message_files:
                    logger.info(f"Processed {len(message_files)} message(s)")
                
                # Generate demo messages periodically (for demonstration)
                demo_count += 1
                if demo_count >= 5:  # Every 5 polls
                    self.run_demo_mode()
                    demo_count = 0
                
                # Wait for next poll
                time.sleep(self.POLL_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("WhatsApp Watcher stopping...")
                break
            except Exception as e:
                logger.error(f"Error in WhatsApp watcher: {e}")
                time.sleep(self.POLL_INTERVAL)


if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    watcher = WhatsAppWatcher(
        inbox_dir=BASE_DIR / "Inbox",
        logs_dir=BASE_DIR / "Logs"
    )
    watcher.run()
