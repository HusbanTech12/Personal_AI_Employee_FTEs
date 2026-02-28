#!/usr/bin/env python3
"""
WhatsApp Webhook Server - Standalone Production Script

Standalone Flask server for receiving Twilio WhatsApp webhooks.
This script can be deployed independently for production use.

For development, use: python Watchers/whatsapp_watcher.py
For production, use: python webhook_server.py

Requirements:
    pip install flask twilio

Usage:
    python webhook_server.py

Stop:
    Press Ctrl+C to stop the server
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.resolve()

# Centralized vault path - all Obsidian vault folders are relative to this
VAULT_PATH = BASE_DIR / "notes"

INBOX_DIR = VAULT_PATH / "Inbox"
LOGS_DIR = BASE_DIR / "Logs"
CONFIG_FILE = BASE_DIR / "Config" / "twilio_config.json"

# Ensure directories exist
INBOX_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to both file and console."""
    log_file = LOGS_DIR / f"whatsapp_webhook_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("WhatsAppWebhook")


logger = setup_logging()


# =============================================================================
# Load Configuration
# =============================================================================

def load_config() -> dict:
    """Load webhook configuration."""
    default_config = {
        "host": "127.0.0.1",
        "port": 5000,
        "endpoint": "/whatsapp/webhook"
    }

    if not CONFIG_FILE.exists():
        logger.warning(f"Config file not found: {CONFIG_FILE}")
        return default_config

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get("webhook", default_config)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return default_config


# =============================================================================
# Task Creator
# =============================================================================

class WhatsAppTaskCreator:
    """Creates markdown tasks from WhatsApp messages."""

    def __init__(self, inbox_dir: Path):
        self.inbox_dir = inbox_dir

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

    def create_task_markdown(self, sender: str, message: str, timestamp: str,
                             message_sid: str = "") -> tuple:
        """Create markdown task from WhatsApp message."""
        priority = self.determine_priority(message)

        # Clean sender for filename
        import re
        clean_sender = re.sub(r'[^\w\s-]', '', sender)[:30].strip()
        clean_sender = clean_sender.replace(' ', '_').lower()

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

- [ ] Review and respond to this message

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
# Flask Application
# =============================================================================

def create_app() -> Flask:
    """Create and configure Flask application."""
    app = Flask(__name__)
    task_creator = WhatsAppTaskCreator(INBOX_DIR)
    config = load_config()

    @app.route(config.get("endpoint", "/whatsapp/webhook"), methods=['POST'])
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
            task_content, filename = task_creator.create_task_markdown(
                sender=from_number,
                message=body,
                timestamp=timestamp,
                message_sid=message_sid
            )

            task_path = task_creator.save_task(task_content, filename)
            logger.info(f"Task created: {task_path}")

            # Return Twilio response
            resp = MessagingResponse()
            return str(resp)

        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return str(MessagingResponse()), 500

    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'service': 'WhatsApp Webhook Server',
            'timestamp': datetime.now().isoformat()
        })

    @app.route('/status', methods=['GET'])
    def status():
        """Status endpoint."""
        return jsonify({
            'host': config.get("host", "127.0.0.1"),
            'port': config.get("port", 5000),
            'endpoint': config.get("endpoint", "/whatsapp/webhook"),
            'inbox_dir': str(INBOX_DIR)
        })

    return app


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    config = load_config()
    app = create_app()

    host = config.get("host", "127.0.0.1")
    port = config.get("port", 5000)
    endpoint = config.get("endpoint", "/whatsapp/webhook")

    logger.info("=" * 60)
    logger.info("WhatsApp Webhook Server Starting...")
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"Endpoint: {endpoint}")
    logger.info(f"Inbox: {INBOX_DIR}")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Configure Twilio webhook URL:")
    logger.info(f"  http://YOUR_PUBLIC_IP:{port}{endpoint}")
    logger.info("")
    logger.info("For local testing with ngrok:")
    logger.info(f"  ngrok http {port}")
    logger.info("")

    app.run(host=host, port=port, debug=False, threaded=True)
