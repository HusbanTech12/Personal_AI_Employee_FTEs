#!/usr/bin/env python3
"""
WhatsApp Watcher - Gold Tier AI Employee

Monitors WhatsApp messages via Twilio webhook server and converts them
into markdown tasks for the AI Employee system.

Features:
- Flask-based webhook server for Twilio POST requests
- Parses incoming WhatsApp messages
- Creates task files in Inbox folder
- Supports demo mode for testing without Twilio

Flow:
    User WhatsApp Message → Twilio Webhook → WhatsApp Watcher → Inbox Task

Requirements:
    pip install flask twilio python-dotenv

Usage:
    python Watchers/whatsapp_watcher.py

Stop:
    Press Ctrl+C to gracefully stop the watcher
"""

import os
import sys
import re
import json
import time
import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Set
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.parent.resolve()

# Centralized vault path - all Obsidian vault folders are relative to this
VAULT_PATH = BASE_DIR / "notes"

CONFIG_DIR = BASE_DIR / "Config"
INBOX_DIR = VAULT_PATH / "Inbox"
LOGS_DIR = BASE_DIR / "Logs"
CONFIG_FILE = CONFIG_DIR / "twilio_config.json"

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to both file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"whatsapp_watcher_{datetime.now().strftime('%Y-%m-%d')}.log"

    # Clear existing handlers to avoid duplicates
    root_logger = logging.getLogger()
    root_logger.handlers = []

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("WhatsAppWatcher")


logger = setup_logging()


# =============================================================================
# Twilio Config Loader
# =============================================================================

class TwilioConfig:
    """Twilio configuration holder."""

    def __init__(self):
        self.account_sid = ""
        self.auth_token = ""
        self.whatsapp_number = ""
        self.webhook_host = "127.0.0.1"
        self.webhook_port = 5000
        self.webhook_endpoint = "/whatsapp/webhook"
        self.load_config()

    def load_config(self):
        """Load configuration from file and environment."""
        if not CONFIG_FILE.exists():
            logger.warning(f"Config file not found: {CONFIG_FILE}")
            return

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                raw_config = json.load(f)

            # Load from environment (secure) or fallback to config file
            self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", raw_config.get("account_sid", ""))
            self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", raw_config.get("auth_token", ""))
            self.whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER", raw_config.get("whatsapp_number", ""))

            # Webhook settings
            webhook = raw_config.get("webhook", {})
            self.webhook_host = webhook.get("host", "127.0.0.1")
            self.webhook_port = webhook.get("port", 5000)
            self.webhook_endpoint = webhook.get("endpoint", "/whatsapp/webhook")

            logger.info("Twilio configuration loaded")

        except Exception as e:
            logger.error(f"Failed to load config: {e}")


# =============================================================================
# WhatsApp Task Creator
# =============================================================================

class WhatsAppTaskCreator:
    """Creates markdown tasks from WhatsApp messages."""

    def __init__(self, inbox_dir: Path):
        self.inbox_dir = inbox_dir
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        self.processed_messages: Set[str] = set()

    def determine_priority(self, message: str) -> str:
        """Determine task priority based on message content."""
        message_lower = message.lower()

        high_priority = ['urgent', 'asap', 'emergency', 'critical', 'important',
                         'call me', 'call back', 'immediate', 'deadline', 'help']
        medium_priority = ['meeting', 'tomorrow', 'today', 'reminder', 'please',
                           'can you', 'could you', 'when you get a chance', 'question']

        for keyword in high_priority:
            if keyword in message_lower:
                return "high"

        for keyword in medium_priority:
            if keyword in message_lower:
                return "medium"

        return "standard"

    def extract_action_items(self, message: str) -> list:
        """Extract potential action items from message."""
        action_items = []
        action_indicators = ['please ', 'need to ', 'have to ', 'must ', 'should ',
                             'can you ', 'could you ', 'will you ', 'action:', 'task:']

        message_lower = message.lower()

        for indicator in action_indicators:
            if indicator in message_lower:
                sentences = re.split(r'[.!?]', message)
                for sentence in sentences:
                    if indicator in sentence.lower() and len(sentence.strip()) < 200:
                        action_items.append(sentence.strip())

        # Look for questions
        questions = re.findall(r'([^?]+\?)', message)
        for question in questions[:3]:
            if len(question.strip()) > 10 and question not in action_items:
                action_items.append(question.strip())

        return list(set(action_items))[:5]

    def create_task_markdown(self, sender: str, message: str, timestamp: str,
                             message_sid: str = "") -> tuple:
        """Create markdown task from WhatsApp message."""
        priority = self.determine_priority(message)
        action_items = self.extract_action_items(message)

        # Clean sender for filename
        clean_sender = re.sub(r'[^\w\s-]', '', sender)[:30].strip()
        clean_sender = clean_sender.replace(' ', '_').lower()

        # Clean message preview for filename
        message_preview = message[:30].replace(' ', '_').lower()
        message_preview = re.sub(r'[^\w-]', '', message_preview)

        # Build task content
        task_content = f"""---
title: WhatsApp: {message[:50]}{'...' if len(message) > 50 else ''}
status: New
priority: {priority}
created: {timestamp}
skill: task_processor
source: WhatsApp
sender: {sender}
message_sid: {message_sid}
approval: Not Required
---

# WhatsApp Message Task

**From:** {sender}

**Received:** {timestamp}

**Source:** WhatsApp

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

## Execution Result

*To be filled by AI Employee after processing*

---

## Response

*Auto-reply will be sent via WhatsApp after task completion*

---

## Notes

- Automatically imported from WhatsApp
- AI Employee will process this task
- Reply will be sent automatically upon completion
"""

        filename = f"whatsapp_task_{timestamp.replace(' ', '_').replace(':', '')}_{clean_sender}.md"

        return task_content, filename

    def save_task(self, task_content: str, filename: str) -> Path:
        """Save task to Inbox folder."""
        task_path = self.inbox_dir / filename

        # Ensure unique filename
        counter = 1
        while task_path.exists():
            name = filename.rsplit('.', 1)[0]
            task_path = self.inbox_dir / f"{name}_{counter}.md"
            counter += 1

        with open(task_path, 'w', encoding='utf-8') as f:
            f.write(task_content)

        logger.info(f"Task saved: {task_path.name}")
        return task_path


# =============================================================================
# WhatsApp Webhook Server
# =============================================================================

class WhatsAppWebhookServer:
    """
    Flask-based webhook server for Twilio WhatsApp integration.

    Receives POST requests from Twilio when WhatsApp messages arrive.
    """

    def __init__(self, config: TwilioConfig, task_creator: WhatsAppTaskCreator):
        self.config = config
        self.task_creator = task_creator
        self.app = Flask(__name__)
        self.server_thread: Optional[threading.Thread] = None
        self.is_running = False

        self._setup_routes()

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route(self.config.webhook_endpoint, methods=['POST'])
        def whatsapp_webhook():
            """Handle incoming WhatsApp messages from Twilio."""
            logger.info("Received WhatsApp webhook")

            try:
                # Extract Twilio parameters
                from_number = request.form.get('From', '')
                to_number = request.form.get('To', '')
                body = request.form.get('Body', '')
                message_sid = request.form.get('MessageSid', '')
                timestamp = request.form.get('Timestamp', datetime.now().isoformat())

                # Log incoming message
                logger.info(f"Message from: {from_number}")
                logger.info(f"Message body: {body[:100]}...")

                # Create task
                task_content, filename = self.task_creator.create_task_markdown(
                    sender=from_number,
                    message=body,
                    timestamp=timestamp,
                    message_sid=message_sid
                )

                task_path = self.task_creator.save_task(task_content, filename)

                logger.info(f"Task created: {task_path}")

                # Return Twilio response (empty - we just acknowledge)
                resp = MessagingResponse()
                return str(resp)

            except Exception as e:
                logger.error(f"Webhook error: {e}")
                return str(MessagingResponse()), 500

        @self.app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'service': 'WhatsApp Watcher',
                'timestamp': datetime.now().isoformat()
            })

        @self.app.route('/status', methods=['GET'])
        def status():
            """Status endpoint."""
            return jsonify({
                'running': self.is_running,
                'host': self.config.webhook_host,
                'port': self.config.webhook_port,
                'endpoint': self.config.webhook_endpoint,
                'processed_messages': len(self.task_creator.processed_messages)
            })

    def start(self):
        """Start the webhook server in a background thread."""
        if self.is_running:
            logger.warning("Webhook server already running")
            return

        def run_server():
            logger.info(f"Starting WhatsApp webhook server on {self.config.webhook_host}:{self.config.webhook_port}")
            logger.info(f"Webhook endpoint: {self.config.webhook_endpoint}")
            self.is_running = True
            self.app.run(
                host=self.config.webhook_host,
                port=self.config.webhook_port,
                debug=False,
                threaded=True
            )

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        # Wait for server to start
        time.sleep(2)

    def stop(self):
        """Stop the webhook server."""
        self.is_running = False
        if self.server_thread:
            self.server_thread.join(timeout=5)
        logger.info("WhatsApp webhook server stopped")


# =============================================================================
# Demo Mode Handler
# =============================================================================

class DemoModeHandler:
    """Generates demo WhatsApp messages for testing."""

    def __init__(self, task_creator: WhatsAppTaskCreator):
        self.task_creator = task_creator

    def generate_demo_message(self) -> Dict:
        """Generate a demo WhatsApp message."""
        demo_messages = [
            {
                'from': 'whatsapp:+1234567890',
                'body': 'Hey, can you send me the project status update by EOD? Need it for the steering committee meeting tomorrow.',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'from': 'whatsapp:+1987654321',
                'body': 'URGENT: The client is asking about the deliverable. When can we ship?',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'from': 'whatsapp:+1122334455',
                'body': 'Reminder: Team lunch at 12:30 today! Please confirm if you\'re coming.',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            {
                'from': 'whatsapp:+1555666777',
                'body': 'Can you help me review the document I sent earlier? Would appreciate your feedback.',
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        ]

        import random
        return random.choice(demo_messages)

    def process_demo_message(self):
        """Process a demo message."""
        demo = self.generate_demo_message()

        task_content, filename = self.task_creator.create_task_markdown(
            sender=demo['from'],
            message=demo['body'],
            timestamp=demo['timestamp'],
            message_sid=f"demo_{datetime.now().timestamp()}"
        )

        self.task_creator.save_task(task_content, filename)
        logger.info(f"Demo message processed from: {demo['from']}")


# =============================================================================
# Main WhatsApp Watcher
# =============================================================================

class WhatsAppWatcher:
    """
    Main WhatsApp Watcher for AI Employee Vault.

    Combines webhook server with demo mode for testing.
    """

    def __init__(self):
        self.config = TwilioConfig()
        self.task_creator = WhatsAppTaskCreator(INBOX_DIR)
        self.webhook_server = WhatsAppWebhookServer(self.config, self.task_creator)
        self.demo_handler = DemoModeHandler(self.task_creator)

        # Demo mode settings
        self.demo_mode = True
        self.demo_interval = 60  # seconds between demo messages
        self.demo_count = 0

    def run(self):
        """Main watcher loop."""
        logger.info("=" * 60)
        logger.info("WhatsApp Watcher Starting...")
        logger.info(f"Inbox: {INBOX_DIR}")
        logger.info(f"Webhook: {self.config.webhook_host}:{self.config.webhook_port}")
        logger.info(f"Endpoint: {self.config.webhook_endpoint}")
        logger.info(f"Demo Mode: {self.demo_mode}")
        logger.info("=" * 60)

        # Start webhook server
        self.webhook_server.start()

        logger.info("")
        logger.info("WhatsApp Watcher is ready!")
        logger.info("")
        logger.info("To test with Twilio:")
        logger.info(f"  1. Set your webhook URL to: http://YOUR_PUBLIC_IP:{self.config.webhook_port}{self.config.webhook_endpoint}")
        logger.info("  2. Use ngrok for local testing: ngrok http 5000")
        logger.info("")
        logger.info("Demo messages will be generated every 60 seconds")
        logger.info("")

        try:
            while True:
                # Generate demo messages periodically
                if self.demo_mode:
                    self.demo_count += 1
                    if self.demo_count >= self.demo_interval:
                        self.demo_handler.process_demo_message()
                        self.demo_count = 0

                time.sleep(1)

        except KeyboardInterrupt:
            logger.info("")
            logger.info("WhatsApp Watcher stopping...")
            self.webhook_server.stop()
            logger.info("WhatsApp Watcher stopped")


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    watcher = WhatsAppWatcher()
    watcher.run()
