#!/usr/bin/env python3
"""
LinkedIn Agent - Gold Tier AI Employee

Autonomous agent for LinkedIn posting with direct API integration.
Receives marketing tasks, generates professional posts, publishes on LinkedIn,
and stores engagement summaries.

Flow:
    Marketing Task → Planner → LinkedIn Agent → API Publish → Done Folder

Requirements:
    pip install requests python-dotenv

Usage:
    python Agents/linkedin_agent.py

Stop:
    Press Ctrl+C to gracefully stop the agent
"""

import os
import sys
import re
import json
import time
import logging
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field

# =============================================================================
# Configuration
# =============================================================================

BASE_DIR = Path(__file__).parent.parent.resolve()

# Centralized vault path - all Obsidian vault folders are relative to this
VAULT_PATH = BASE_DIR / "notes"

CONFIG_DIR = BASE_DIR / "Config"
NEEDS_ACTION_DIR = VAULT_PATH / "Needs_Action"
DONE_DIR = VAULT_PATH / "Done"
LOGS_DIR = BASE_DIR / "Logs"
MARKETING_DIR = VAULT_PATH / "Domains" / "Business" / "Marketing"
LINKEDIN_POSTS_DIR = MARKETING_DIR / "linkedin_posts"
CONFIG_FILE = CONFIG_DIR / "linkedin_config.json"

# Logging configuration
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Polling interval in seconds
POLL_INTERVAL = 10

# =============================================================================
# Logging Setup
# =============================================================================

def setup_logging() -> logging.Logger:
    """Configure logging to both file and console."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    LINKEDIN_POSTS_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOGS_DIR / f"linkedin_agent_{datetime.now().strftime('%Y-%m-%d')}.log"

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
    return logging.getLogger("LinkedInAgent")


logger = setup_logging()


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class LinkedInConfig:
    """LinkedIn API configuration holder."""
    access_token: str = ""
    org_id: str = ""
    author_urn: str = ""
    base_url: str = "https://api.linkedin.com/v2"
    demo_mode: bool = True
    max_retries: int = 3
    retry_delay_seconds: int = 30

    def is_configured(self) -> bool:
        """Check if API credentials are configured."""
        return bool(self.access_token and self.org_id)


@dataclass
class LinkedInPost:
    """Represents a LinkedIn post to be published."""
    task_file: Path
    topic: str = ""
    audience: str = ""
    goal: str = ""
    content: str = ""
    hashtags: List[str] = field(default_factory=list)
    tone: str = "professional"
    post_type: str = "business"
    visibility: str = "PUBLIC"


@dataclass
class PostResult:
    """Result from LinkedIn post publication."""
    success: bool
    post_id: str = ""
    post_url: str = ""
    published_at: str = ""
    error_message: str = ""
    engagement_summary: Dict = field(default_factory=dict)


# =============================================================================
# LinkedIn API Client
# =============================================================================

class LinkedInAPIClient:
    """
    Direct LinkedIn API client for posting.
    
    Uses LinkedIn UGC Posts API:
    https://api.linkedin.com/v2/ugcPosts
    """

    def __init__(self, config: LinkedInConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {self.config.access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        })

    def publish_post(self, post: LinkedInPost) -> PostResult:
        """
        Publish a post to LinkedIn via API.
        
        API Endpoint: POST https://api.linkedin.com/v2/ugcPosts
        """
        if self.config.demo_mode or not self.config.is_configured():
            return self._demo_publish(post)

        try:
            # Build LinkedIn UGC Post payload
            payload = self._build_ugc_post_payload(post)

            response = self.session.post(
                f"{self.config.base_url}/ugcPosts",
                json=payload,
                timeout=30
            )

            if response.status_code == 201:
                result_data = response.json()
                post_id = result_data.get('id', '')
                
                # Build post URL
                post_url = self._build_post_url(post_id)

                return PostResult(
                    success=True,
                    post_id=post_id,
                    post_url=post_url,
                    published_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    engagement_summary={
                        'impressions': 0,
                        'likes': 0,
                        'comments': 0,
                        'shares': 0
                    }
                )
            else:
                error_msg = f"API Error {response.status_code}: {response.text}"
                logger.error(error_msg)
                return PostResult(
                    success=False,
                    error_message=error_msg
                )

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return PostResult(
                success=False,
                error_message=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return PostResult(
                success=False,
                error_message=str(e)
            )

    def _build_ugc_post_payload(self, post: LinkedInPost) -> Dict:
        """Build LinkedIn UGC Post API payload."""
        # Format content with hashtags
        full_content = post.content
        if post.hashtags:
            hashtag_str = ' '.join(post.hashtags)
            full_content = f"{post.content}\n\n{hashtag_str}"

        # Determine author URN
        author_urn = self.config.author_urn or f"urn:li:organization:{self.config.org_id}"

        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": full_content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": post.visibility
            }
        }

        return payload

    def _build_post_url(self, post_id: str) -> str:
        """Build LinkedIn post URL from post ID."""
        # Extract numeric ID from URN
        numeric_id = post_id.split(':')[-1] if ':' in post_id else post_id
        return f"https://www.linkedin.com/feed/update/urn:li:share:{numeric_id}"

    def _demo_publish(self, post: LinkedInPost) -> PostResult:
        """Simulate post publication in demo mode."""
        demo_post_id = f"urn:li:share:{int(time.time())}"
        demo_url = f"https://www.linkedin.com/feed/update/{demo_post_id}"

        logger.info(f"[DEMO MODE] Would publish post: {post.topic}")
        logger.info(f"[DEMO MODE] Content preview: {post.content[:100]}...")

        return PostResult(
            success=True,
            post_id=demo_post_id,
            post_url=demo_url,
            published_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            engagement_summary={
                'impressions': 0,
                'likes': 0,
                'comments': 0,
                'shares': 0,
                'demo_mode': True
            }
        )

    def get_analytics(self, post_id: str) -> Dict:
        """Get analytics for a published post."""
        if not self.config.is_configured() or self.config.demo_mode:
            return {'demo_mode': True, 'impressions': 0, 'likes': 0, 'comments': 0, 'shares': 0}

        try:
            # LinkedIn analytics endpoint
            response = self.session.get(
                f"{self.config.base_url}/posts/{post_id}",
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'impressions': data.get('specificContent', {}).get('analytics', {}).get('impressions', 0),
                    'likes': data.get('engagement', {}).get('likes', 0),
                    'comments': data.get('engagement', {}).get('comments', 0),
                    'shares': data.get('engagement', {}).get('shares', 0)
                }
        except Exception as e:
            logger.error(f"Failed to get analytics: {e}")

        return {}


# =============================================================================
# Content Generator
# =============================================================================

class LinkedInContentGenerator:
    """Generates professional LinkedIn post content."""

    # Tone templates
    TONE_TEMPLATES = {
        'professional': {
            'opening': [
                "We're pleased to announce",
                "We're excited to share",
                "Today we're introducing"
            ],
            'closing': [
                "Learn more about our solution.",
                "Discover how we can help.",
                "Join us in shaping the future."
            ]
        },
        'conversational': {
            'opening': [
                "Hey everyone! Great news to share",
                "Exciting updates from our team",
                "Want to share something cool with you"
            ],
            'closing': [
                "What do you think? Drop a comment!",
                "Let's chat about this in the comments",
                "Would love to hear your thoughts"
            ]
        },
        'enthusiastic': {
            'opening': [
                "🚀 Big news!",
                "✨ Amazing announcement!",
                "🎉 We did it!"
            ],
            'closing': [
                "This is just the beginning!",
                "Stay tuned for more!",
                "Let's go!"
            ]
        },
        'educational': {
            'opening': [
                "Here's something valuable to know",
                "Key insights on",
                "Important lessons about"
            ],
            'closing': [
                "Save this for later reference.",
                "Share if you found this helpful.",
                "What would you add?"
            ]
        }
    }

    # Hashtag suggestions by topic
    HASHTAG_SUGGESTIONS = {
        'product': ['#ProductLaunch', '#Innovation', '#Technology', '#NewProduct', '#Tech'],
        'business': ['#Business', '#Leadership', '#Strategy', '#Growth', '#Entrepreneurship'],
        'ai': ['#AI', '#ArtificialIntelligence', '#MachineLearning', '#Automation', '#FutureOfWork'],
        'marketing': ['#Marketing', '#DigitalMarketing', '#ContentMarketing', '#SocialMedia', '#Brand'],
        'technology': ['#Technology', '#Tech', '#Innovation', '#Digital', '#Software'],
        'career': ['#Career', '#ProfessionalDevelopment', '#Leadership', '#CareerAdvice', '#Growth'],
        'company': ['#Company', '#TeamWork', '#Culture', '#WorkLife', '#CompanyNews']
    }

    def generate_post(self, task: LinkedInPost) -> LinkedInPost:
        """Generate LinkedIn post content from task."""
        # Get tone template
        tone_data = self.TONE_TEMPLATES.get(task.tone, self.TONE_TEMPLATES['professional'])
        opening = (task.content or '').split('\n')[0] if task.content else ''
        
        if not opening:
            import random
            opening = random.choice(tone_data['opening'])

        # Build main content
        content_parts = []
        
        # Add hook/opening
        content_parts.append(opening)
        
        # Add value proposition or details
        if task.goal:
            content_parts.append(f"\n{task.goal}")
        
        if task.audience:
            content_parts.append(f"\nDesigned for: {task.audience}")
        
        # Add call-to-action
        closing = random.choice(tone_data['closing'])
        content_parts.append(f"\n\n{closing}")

        # Generate hashtags
        hashtags = self._suggest_hashtags(task.topic)

        task.content = '\n'.join(content_parts)
        task.hashtags = hashtags

        return task

    def _suggest_hashtags(self, topic: str) -> List[str]:
        """Suggest relevant hashtags based on topic."""
        topic_lower = topic.lower()
        selected_hashtags = []

        # Match topic to hashtag categories
        for keyword, hashtags in self.HASHTAG_SUGGESTIONS.items():
            if keyword in topic_lower:
                selected_hashtags.extend(hashtags[:3])  # Take top 3 from category

        # Default hashtags if no match
        if not selected_hashtags:
            selected_hashtags = ['#Business', '#Professional', '#LinkedIn']

        # Limit to 5 hashtags
        return list(dict.fromkeys(selected_hashtags))[:5]


# =============================================================================
# LinkedIn Agent
# =============================================================================

class LinkedInAgent:
    """
    LinkedIn Agent for Gold Tier AI Employee.

    Responsibilities:
    - Monitor Needs_Action for LinkedIn marketing tasks
    - Generate professional post content
    - Publish posts via LinkedIn API
    - Store engagement summaries
    - Handle failures with retry logic
    """

    def __init__(self):
        self.config = self._load_config()
        self.api_client = LinkedInAPIClient(self.config)
        self.content_generator = LinkedInContentGenerator()
        self.processed_tasks: set = set()
        self.retry_queue: Dict[str, Tuple[LinkedInPost, int]] = {}

    def _load_config(self) -> LinkedInConfig:
        """Load LinkedIn configuration from file and environment."""
        config = LinkedInConfig()

        # Load from environment variables (secure)
        config.access_token = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
        config.org_id = os.getenv("LINKEDIN_ORG_ID", "")
        config.author_urn = os.getenv("LINKEDIN_AUTHOR_URN", "")

        # Load from config file if exists
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    raw_config = json.load(f)
                
                # Override with file config if env vars not set
                if not config.access_token:
                    config.access_token = raw_config.get("access_token", "")
                if not config.org_id:
                    config.org_id = raw_config.get("org_id", "")
                if not config.author_urn:
                    config.author_urn = raw_config.get("author_urn", "")
                
                config.demo_mode = raw_config.get("demo_mode", not config.is_configured())
                config.max_retries = raw_config.get("max_retries", 3)
                config.retry_delay_seconds = raw_config.get("retry_delay_seconds", 30)

            except Exception as e:
                logger.error(f"Failed to load config: {e}")

        # Auto-enable demo mode if not configured
        if not config.is_configured():
            config.demo_mode = True
            logger.info("LinkedIn API not configured - running in DEMO MODE")

        return config

    def scan_for_tasks(self) -> List[Path]:
        """Scan Needs_Action for LinkedIn marketing tasks."""
        tasks = []

        if not NEEDS_ACTION_DIR.exists():
            return tasks

        for file_path in NEEDS_ACTION_DIR.iterdir():
            if (file_path.is_file() and 
                file_path.suffix.lower() == '.md' and
                file_path.stem not in self.processed_tasks):
                
                # Check if it's a LinkedIn task
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    skill_match = re.search(r'skill:\s*(\w+)', content, re.IGNORECASE)
                    if skill_match:
                        skill = skill_match.group(1).lower()
                        if 'linkedin' in skill:
                            tasks.append(file_path)
                except Exception:
                    pass

        return tasks

    def parse_task(self, file_path: Path) -> Optional[LinkedInPost]:
        """Parse task file and extract LinkedIn post details."""
        try:
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

            # Check if it's a LinkedIn task
            skill = frontmatter.get('skill', '').lower()
            if 'linkedin' not in skill:
                return None

            return LinkedInPost(
                task_file=file_path,
                topic=frontmatter.get('topic', frontmatter.get('title', '')),
                audience=frontmatter.get('audience', ''),
                goal=frontmatter.get('goal', ''),
                content=body.strip()[:1000],  # Limit content length
                tone=frontmatter.get('tone', 'professional'),
                post_type=frontmatter.get('post_type', 'business'),
                visibility=frontmatter.get('visibility', 'PUBLIC')
            )

        except Exception as e:
            logger.error(f"Failed to parse task {file_path.name}: {e}")
            return None

    def publish_post(self, post: LinkedInPost) -> PostResult:
        """Generate content and publish post."""
        # Generate content if not provided
        if not post.content:
            post = self.content_generator.generate_post(post)
            logger.info(f"Generated content for post: {post.topic}")

        # Publish via API
        result = self.api_client.publish_post(post)

        if result.success:
            logger.info(f"Post published: {result.post_id}")
        else:
            logger.error(f"Post failed: {result.error_message}")

        return result

    def save_engagement_summary(self, post: LinkedInPost, result: PostResult):
        """Save engagement summary to marketing directory."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        summary_file = LINKEDIN_POSTS_DIR / f"linkedin_post_{timestamp}.md"

        # Build summary content
        summary_content = f"""---
title: LinkedIn Post - {post.topic}
status: Published
post_id: {result.post_id}
post_url: {result.post_url}
published_at: {result.published_at}
topic: {post.topic}
audience: {post.audience}
tone: {post.tone}
---

# LinkedIn Post Summary

## Publication Details

| Field | Value |
|-------|-------|
| **Post ID** | {result.post_id} |
| **URL** | [{result.post_url}]({result.post_url}) |
| **Published** | {result.published_at} |
| **Topic** | {post.topic} |
| **Audience** | {post.audience} |
| **Tone** | {post.tone} |

---

## Post Content

```
{post.content}
```

---

## Hashtags

{' '.join(post.hashtags)}

---

## Engagement Summary

| Metric | Value |
|--------|-------|
| Impressions | {result.engagement_summary.get('impressions', 'N/A')} |
| Likes | {result.engagement_summary.get('likes', 'N/A')} |
| Comments | {result.engagement_summary.get('comments', 'N/A')} |
| Shares | {result.engagement_summary.get('shares', 'N/A')} |

---

## Notes

- Automatically published by AI Employee LinkedIn Agent
- {'Demo mode - post was not actually published' if result.engagement_summary.get('demo_mode') else 'Published via LinkedIn API'}
- Engagement metrics will be updated periodically

---

*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

        try:
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary_content)
            logger.info(f"Engagement summary saved: {summary_file.name}")
        except Exception as e:
            logger.error(f"Failed to save summary: {e}")

    def update_task_status(self, task_file: Path, result: PostResult):
        """Update task file with execution result."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if execution result already exists
            if '## Execution Result' in content:
                return

            # Add execution result section
            result_section = f"""
---

## Execution Result

**Status:** {'✅ Success' if result.success else '❌ Failed'}

**Summary:**
- Post ID: {result.post_id}
- URL: {result.post_url}
- Published: {result.published_at}

"""
            if result.success:
                result_section += "**Result:** Post published successfully on LinkedIn.\n"
            else:
                result_section += f"**Error:** {result.error_message}\n"

            # Append to content
            new_content = content + result_section

            with open(task_file, 'w', encoding='utf-8') as f:
                f.write(new_content)

            logger.info(f"Task status updated: {task_file.name}")

        except Exception as e:
            logger.error(f"Failed to update task status: {e}")

    def process_task(self, file_path: Path):
        """Process a single LinkedIn task."""
        logger.info(f"Processing LinkedIn task: {file_path.name}")

        # Parse task
        post = self.parse_task(file_path)
        if not post:
            logger.warning(f"Not a LinkedIn task: {file_path.name}")
            return

        # Publish post
        result = self.publish_post(post)

        # Save engagement summary
        if result.success:
            self.save_engagement_summary(post, result)

        # Update task status
        self.update_task_status(file_path, result)

        # Mark as processed
        self.processed_tasks.add(file_path.stem)

        if result.success:
            logger.info(f"Task completed: {file_path.name}")
        else:
            # Add to retry queue
            if file_path.stem not in self.retry_queue:
                self.retry_queue[file_path.stem] = (post, 0)
            logger.warning(f"Task failed, added to retry queue: {file_path.name}")

    def process_retry_queue(self):
        """Process retry queue for failed posts."""
        to_remove = []

        for task_id, (post, retry_count) in self.retry_queue.items():
            if retry_count >= self.config.max_retries:
                logger.error(f"Max retries reached for task: {task_id}")
                to_remove.append(task_id)
                continue

            retry_count += 1
            self.retry_queue[task_id] = (post, retry_count)

            logger.info(f"Retrying task: {task_id} (attempt {retry_count})")

            # Retry publishing
            result = self.api_client.publish_post(post)

            if result.success:
                self.save_engagement_summary(post, result)
                self.update_task_status(post.task_file, result)
                self.processed_tasks.add(task_id)
                to_remove.append(task_id)
                logger.info(f"Retry successful for task: {task_id}")

        for task_id in to_remove:
            del self.retry_queue[task_id]

    def run(self):
        """Main agent loop."""
        logger.info("=" * 60)
        logger.info("LinkedIn Agent Starting...")
        logger.info(f"Needs_Action: {NEEDS_ACTION_DIR}")
        logger.info(f"Marketing Dir: {MARKETING_DIR}")
        logger.info(f"Poll Interval: {POLL_INTERVAL}s")
        logger.info(f"Demo Mode: {self.config.demo_mode}")
        logger.info(f"API Configured: {self.config.is_configured()}")
        logger.info("=" * 60)

        if self.config.demo_mode:
            logger.warning("Running in DEMO MODE - posts will not be published")
            logger.warning("Set LINKEDIN_ACCESS_TOKEN and LINKEDIN_ORG_ID to enable")

        while True:
            try:
                # Scan for new tasks
                tasks = self.scan_for_tasks()

                for task_file in tasks:
                    self.process_task(task_file)

                # Process retry queue
                self.process_retry_queue()

                # Wait for next poll
                time.sleep(POLL_INTERVAL)

            except KeyboardInterrupt:
                logger.info("LinkedIn Agent stopping...")
                break
            except Exception as e:
                logger.error(f"Error in LinkedIn agent loop: {e}")
                time.sleep(POLL_INTERVAL)


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    agent = LinkedInAgent()
    agent.run()
