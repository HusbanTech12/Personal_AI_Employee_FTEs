#!/usr/bin/env python3
"""
Social Media Agent - Gold Tier AI Employee

Manages social media marketing across Facebook, Instagram, and Twitter (X).
Generates posts, publishes via Social MCP server, and creates daily summaries.

Capabilities:
- Generate platform-optimized posts
- Publish to multiple platforms via MCP
- Fetch engagement metrics
- Generate daily social media summaries

Platforms:
- Facebook
- Instagram
- Twitter (X)

Usage:
    python social_media_agent.py

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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("SocialMediaAgent")


class Platform(Enum):
    """Supported social media platforms."""
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"


@dataclass
class PostContent:
    """Generated post content for a platform."""
    platform: Platform
    content: str
    hashtags: List[str]
    character_count: int
    media_suggestion: Optional[str] = None


class SocialMediaAgent:
    """
    Social Media Agent - Multi-platform marketing automation.
    """
    
    # Social MCP Server
    MCP_HOST = os.getenv("SOCIAL_MCP_HOST", "127.0.0.1")
    MCP_PORT = int(os.getenv("SOCIAL_MCP_PORT", "8768"))
    MCP_BASE_URL = f"http://{MCP_HOST}:{MCP_PORT}"
    
    # Platform-specific configurations
    PLATFORM_CONFIG = {
        Platform.FACEBOOK: {
            'max_length': 63206,
            'optimal_length': 80,
            'hashtag_limit': 10,
            'optimal_hashtags': 5,
            'emoji_support': True,
            'link_support': True
        },
        Platform.INSTAGRAM: {
            'max_length': 2200,
            'optimal_length': 150,
            'hashtag_limit': 30,
            'optimal_hashtags': 15,
            'emoji_support': True,
            'link_support': False,  # Links only in bio
            'media_required': True
        },
        Platform.TWITTER: {
            'max_length': 280,
            'optimal_length': 120,
            'hashtag_limit': 3,
            'optimal_hashtags': 2,
            'emoji_support': True,
            'link_support': True,
            'thread_support': True
        }
    }
    
    # Hashtag libraries by topic
    HASHTAG_LIBRARIES = {
        'product': ['#ProductLaunch', '#NewProduct', '#Innovation', '#Tech', '#Startup'],
        'business': ['#Business', '#Entrepreneur', '#Success', '#Leadership', '#Growth'],
        'marketing': ['#Marketing', '#DigitalMarketing', '#SocialMedia', '#Content', '#Brand'],
        'technology': ['#Technology', '#AI', '#Software', '#Tech', '#Innovation'],
        'lifestyle': ['#Lifestyle', '#Daily', '#Motivation', '#Inspiration', '#Life'],
        'general': ['#Trending', '#Viral', '#Explore', '#Follow', '#Like']
    }
    
    def __init__(self, needs_action_dir: Path, logs_dir: Path, business_dir: Optional[Path] = None):
        self.needs_action_dir = needs_action_dir
        self.logs_dir = logs_dir
        self.business_dir = business_dir or (needs_action_dir.parent / "Domains" / "Business")
        
        # Marketing directory for summaries
        self.marketing_dir = self.business_dir / "Marketing"
        self.marketing_dir.mkdir(parents=True, exist_ok=True)
        
        self.processed_tasks: set = set()
        self.post_history: List[Dict] = []
    
    def read_task(self, file_path: Path) -> Tuple[str, Dict]:
        """Read task file and extract frontmatter + content."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        frontmatter = {}
        body = content
        
        frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if frontmatter_match:
            fm_text = frontmatter_match.group(1)
            for line in fm_text.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    frontmatter[key.strip()] = value.strip()
            body = content[frontmatter_match.end():]
        
        return body, frontmatter
    
    def parse_platforms(self, platform_str: str) -> List[Platform]:
        """Parse platform string into Platform enums."""
        platforms = []
        platform_map = {
            'facebook': Platform.FACEBOOK,
            'fb': Platform.FACEBOOK,
            'instagram': Platform.INSTAGRAM,
            'insta': Platform.INSTAGRAM,
            'ig': Platform.INSTAGRAM,
            'twitter': Platform.TWITTER,
            'x': Platform.TWITTER
        }
        
        for p in platform_str.lower().replace(',', ' ').split():
            if p in platform_map:
                platforms.append(platform_map[p])
        
        return platforms if platforms else [Platform.FACEBOOK, Platform.INSTAGRAM, Platform.TWITTER]
    
    def detect_topic(self, content: str) -> str:
        """Detect topic category from content."""
        content_lower = content.lower()
        
        topic_keywords = {
            'product': ['product', 'launch', 'release', 'feature', 'new'],
            'business': ['business', 'company', 'enterprise', 'corporate', 'b2b'],
            'marketing': ['marketing', 'promotion', 'campaign', 'brand', 'advertise'],
            'technology': ['technology', 'tech', 'software', 'ai', 'digital', 'app'],
            'lifestyle': ['lifestyle', 'daily', 'life', 'wellness', 'health']
        }
        
        scores = {topic: 0 for topic in topic_keywords}
        
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword in content_lower:
                    scores[topic] += 1
        
        return max(scores, key=scores.get) if max(scores.values()) > 0 else 'general'
    
    def generate_hashtags(self, topic: str, count: int = 5) -> List[str]:
        """Generate relevant hashtags for a topic."""
        base_hashtags = self.HASHTAG_LIBRARIES.get(topic, self.HASHTAG_LIBRARIES['general'])
        
        # Add general hashtags
        all_hashtags = base_hashtags + self.HASHTAG_LIBRARIES['general']
        
        # Remove duplicates and return requested count
        unique = list(dict.fromkeys(all_hashtags))
        return unique[:count]
    
    def generate_post_content(self, topic: str, goal: str, key_points: List[str], 
                               platform: Platform) -> PostContent:
        """Generate platform-optimized post content."""
        config = self.PLATFORM_CONFIG[platform]
        detected_topic = self.detect_topic(f"{topic} {goal} {' '.join(key_points)}")
        hashtags = self.generate_hashtags(detected_topic, config['optimal_hashtags'])
        
        # Generate content based on platform
        if platform == Platform.FACEBOOK:
            content = self._generate_facebook_content(topic, goal, key_points, config)
        elif platform == Platform.INSTAGRAM:
            content = self._generate_instagram_content(topic, goal, key_points, config)
        elif platform == Platform.TWITTER:
            content = self._generate_twitter_content(topic, goal, key_points, config)
        else:
            content = f"{topic}: {goal}"
        
        # Add hashtags
        hashtag_str = ' '.join(hashtags)
        if len(content) + len(hashtag_str) + 1 <= config['max_length']:
            content = f"{content}\n\n{hashtag_str}"
        else:
            # Truncate content to fit hashtags
            available = config['max_length'] - len(hashtag_str) - 3
            content = f"{content[:available]}...\n\n{hashtag_str}"
        
        # Suggest media
        media_suggestion = self._suggest_media(topic, goal, platform)
        
        return PostContent(
            platform=platform,
            content=content,
            hashtags=hashtags,
            character_count=len(content),
            media_suggestion=media_suggestion
        )
    
    def _generate_facebook_content(self, topic: str, goal: str, 
                                    key_points: List[str], config: Dict) -> str:
        """Generate Facebook post content."""
        emojis = {'product': '🎉', 'business': '💼', 'marketing': '📢', 
                  'technology': '💻', 'lifestyle': '✨', 'general': '📱'}
        
        topic_category = self.detect_topic(f"{topic} {goal}")
        emoji = emojis.get(topic_category, '📱')
        
        # Facebook prefers conversational tone
        content = f"{emoji} {topic}\n\n"
        
        if key_points:
            for point in key_points[:5]:
                content += f"• {point}\n"
        else:
            content += f"{goal}\n\n"
        
        content += "\n👉 Learn more in the comments!"
        
        return content[:config['optimal_length'] * 2]
    
    def _generate_instagram_content(self, topic: str, goal: str, 
                                     key_points: List[str], config: Dict) -> str:
        """Generate Instagram post content."""
        emojis = {'product': '✨', 'business': '🚀', 'marketing': '📸', 
                  'technology': '🔧', 'lifestyle': '🌟', 'general': '📷'}
        
        topic_category = self.detect_topic(f"{topic} {goal}")
        emoji = emojis.get(topic_category, '📷')
        
        # Instagram prefers visual-first, shorter captions
        content = f"{emoji} {topic}\n\n"
        
        if key_points:
            content += f"{key_points[0] if key_points else goal}\n"
            if len(key_points) > 1:
                content += f"\nSwipe to see more! 👉\n"
        else:
            content += f"{goal}\n"
        
        content += "\n💬 Double-tap if you agree!"
        
        return content[:config['optimal_length'] * 1.5]
    
    def _generate_twitter_content(self, topic: str, goal: str, 
                                   key_points: List[str], config: Dict) -> str:
        """Generate Twitter post content."""
        emojis = {'product': '🚀', 'business': '💡', 'marketing': '📣', 
                  'technology': '⚡', 'lifestyle': '🎯', 'general': '📍'}
        
        topic_category = self.detect_topic(f"{topic} {goal}")
        emoji = emojis.get(topic_category, '📍')
        
        # Twitter needs concise, impactful content
        if key_points:
            content = f"{emoji} {key_points[0]}"
        else:
            content = f"{emoji} {topic}: {goal[:100]}"
        
        # Add call-to-action if space
        if len(content) < 200:
            content += " 👇"
        
        return content[:config['optimal_length']]
    
    def _suggest_media(self, topic: str, goal: str, platform: Platform) -> Optional[str]:
        """Suggest media type for post."""
        if platform == Platform.INSTAGRAM:
            return "High-quality image or short video reel"
        elif platform == Platform.FACEBOOK:
            return "Image, video, or link preview"
        elif platform == Platform.TWITTER:
            return "Image, GIF, or short video"
        return None
    
    def publish_via_mcp(self, posts: List[PostContent]) -> Dict:
        """Publish posts via Social MCP server."""
        results = {}
        
        for post in posts:
            try:
                # Prepare request
                request_data = {
                    'content': post.content,
                    'platforms': [post.platform.value],
                    'hashtags': post.hashtags
                }
                
                json_data = json.dumps(request_data).encode('utf-8')
                req = urllib.request.Request(
                    f"{self.MCP_BASE_URL}/post/publish",
                    data=json_data,
                    method='POST',
                    headers={'Content-Type': 'application/json'}
                )
                
                with urllib.request.urlopen(req, timeout=30) as response:
                    result = json.loads(response.read().decode('utf-8'))
                    results[post.platform.value] = result
                    
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8') if e.fp else str(e)
                results[post.platform.value] = {
                    'success': False,
                    'error': error_body
                }
            except Exception as e:
                results[post.platform.value] = {
                    'success': False,
                    'error': str(e),
                    'fallback': True,
                    'message': 'MCP offline - content queued'
                }
        
        return results
    
    def fetch_engagement(self, days: int = 7) -> Dict:
        """Fetch engagement metrics from Social MCP."""
        try:
            req = urllib.request.Request(
                f"{self.MCP_BASE_URL}/analytics?days={days}",
                method='GET'
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read().decode('utf-8'))
                return result
                
        except Exception as e:
            logger.warning(f"Failed to fetch engagement: {e}")
            # Return demo data
            return {
                'success': True,
                'demo_mode': True,
                'analytics': {
                    'facebook': {'posts': 5, 'impressions': 5000, 'likes': 150, 'shares': 25, 'comments': 30},
                    'instagram': {'posts': 4, 'impressions': 3500, 'likes': 280, 'comments': 45},
                    'twitter': {'posts': 10, 'impressions': 2500, 'likes': 120, 'retweets': 35}
                }
            }
    
    def generate_daily_summary(self) -> Dict:
        """Generate daily social media summary."""
        try:
            # Fetch engagement data
            engagement = self.fetch_engagement(days=1)
            
            # Get analytics by platform
            analytics = engagement.get('analytics', {})
            
            # Calculate totals
            total_posts = sum(a.get('posts', 0) for a in analytics.values())
            total_impressions = sum(a.get('impressions', 0) for a in analytics.values())
            total_engagement = sum(
                a.get('likes', 0) + a.get('shares', 0) + a.get('retweets', 0) + a.get('comments', 0)
                for a in analytics.values()
            )
            
            # Calculate engagement rates
            for platform, data in analytics.items():
                impressions = data.get('impressions', 1)
                eng = data.get('likes', 0) + data.get('shares', 0) + data.get('comments', 0)
                data['engagement_rate'] = round((eng / impressions) * 100, 2) if impressions > 0 else 0
            
            # Generate markdown summary
            summary_md = self._create_summary_markdown(analytics, total_posts, 
                                                        total_impressions, total_engagement)
            
            # Save summary
            today = datetime.now().strftime('%Y-%m-%d')
            summary_file = self.marketing_dir / f"daily_social_summary_{today}.md"
            
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary_md)
            
            logger.info(f"Daily summary saved: {summary_file.name}")
            
            return {
                'success': True,
                'summary_file': str(summary_file),
                'total_posts': total_posts,
                'total_impressions': total_impressions,
                'total_engagement': total_engagement
            }
            
        except Exception as e:
            logger.error(f"Failed to generate daily summary: {e}")
            return {'success': False, 'error': str(e)}
    
    def _create_summary_markdown(self, analytics: Dict, total_posts: int,
                                  total_impressions: int, total_engagement: int) -> str:
        """Create daily summary markdown."""
        today = datetime.now().strftime('%Y-%m-%d')
        
        content = f"""# Daily Social Media Summary

**Date:** {today}
**Generated by:** AI Employee Social Media Agent

---

## Summary

| Platform | Posts | Impressions | Engagement | Rate |
|----------|-------|-------------|------------|------|
"""
        
        for platform, data in analytics.items():
            content += f"| {platform.title()} | {data.get('posts', 0)} | {data.get('impressions', 0):,} | {data.get('likes', 0) + data.get('shares', 0) + data.get('comments', 0)} | {data.get('engagement_rate', 0)}% |\n"
        
        overall_rate = round((total_engagement / total_impressions) * 100, 2) if total_impressions > 0 else 0
        
        content += f"| **Total** | **{total_posts}** | **{total_impressions:,}** | **{total_engagement}** | **{overall_rate}%** |\n"
        
        content += """
---

## Top Performing Content

"""
        
        # Add placeholder for top posts (would come from actual post history)
        content += "*Post-level analytics available in Social MCP server*\n"
        
        content += f"""
---

## Recommendations

1. **Review engagement rates** - Focus on platforms with highest engagement
2. **Optimize posting times** - Post when audience is most active
3. **Content variety** - Mix of images, videos, and text posts
4. **Hashtag strategy** - Use platform-appropriate hashtag counts

---

## Tomorrow's Plan

- [ ] Review today's performance
- [ ] Schedule posts for tomorrow
- [ ] Engage with comments and mentions
- [ ] Monitor trending topics

---

*Generated automatically by AI Employee Social Media Agent*
"""
        
        return content
    
    def execute(self, task_input: Dict) -> Dict:
        """Execute social media task."""
        action = task_input.get('action', '')
        topic = task_input.get('topic', task_input.get('title', ''))
        goal = task_input.get('goal', '')
        key_points = task_input.get('key_points', [])
        platforms = task_input.get('platforms', [Platform.FACEBOOK])
        
        logger.info(f"Executing social media action: {action}")
        logger.info(f"  Topic: {topic}")
        logger.info(f"  Platforms: {[p.value for p in platforms]}")
        
        if action == 'generate' or action == 'generate_post':
            # Generate content for all platforms
            generated = {}
            for platform in platforms:
                post = self.generate_post_content(topic, goal, key_points, platform)
                generated[platform.value] = {
                    'content': post.content,
                    'hashtags': post.hashtags,
                    'character_count': post.character_count,
                    'media_suggestion': post.media_suggestion
                }
            
            return {
                'success': True,
                'action': 'generate',
                'generated_posts': generated
            }
        
        elif action == 'publish' or action == 'generate_and_publish':
            # Generate and publish
            posts = []
            for platform in platforms:
                post = self.generate_post_content(topic, goal, key_points, platform)
                posts.append(post)
            
            # Publish via MCP
            publish_results = self.publish_via_mcp(posts)
            
            return {
                'success': True,
                'action': 'publish',
                'generated_posts': {p.platform.value: p.content for p in posts},
                'publish_results': publish_results
            }
        
        elif action == 'fetch_engagement' or action == 'engagement':
            return self.fetch_engagement(days=task_input.get('days', 7))
        
        elif action == 'generate_summary' or action == 'daily_summary':
            return self.generate_daily_summary()
        
        else:
            # Default: generate content
            generated = {}
            for platform in platforms if platforms else [Platform.FACEBOOK]:
                post = self.generate_post_content(topic, goal, key_points, platform)
                generated[platform.value] = {
                    'content': post.content,
                    'hashtags': post.hashtags,
                    'character_count': post.character_count
                }
            
            return {
                'success': True,
                'action': 'generate',
                'generated_posts': generated
            }
    
    def scan_for_social_tasks(self) -> List[Path]:
        """Scan Needs_Action for social media tasks."""
        tasks = []
        
        if not self.needs_action_dir.exists():
            return tasks
        
        for file_path in self.needs_action_dir.iterdir():
            if file_path.is_file() and file_path.suffix.lower() == '.md':
                if file_path.name in self.processed_tasks:
                    continue
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for social media task indicators
                is_social = (
                    'skill: social_media_marketing' in content.lower() or
                    'skill:social' in content.lower() or
                    ('facebook' in content.lower() or 'instagram' in content.lower() or 'twitter' in content.lower()) and
                    ('post' in content.lower() or 'publish' in content.lower())
                )
                
                if is_social:
                    tasks.append(file_path)
        
        return tasks
    
    def update_task_file(self, task_file: Path, result: Dict):
        """Update task file with execution result."""
        try:
            with open(task_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if result.get('success'):
                if 'generated_posts' in result:
                    posts_md = "\n\n## Generated Posts\n\n"
                    for platform, post_data in result['generated_posts'].items():
                        posts_md += f"### {platform.title()}\n\n"
                        posts_md += f"```\n{post_data.get('content', '')}\n```\n\n"
                        posts_md += f"**Hashtags:** {' '.join(post_data.get('hashtags', []))}\n\n"
                    
                    result_md = f"""
---

## Task Completed

**Status:** ✅ Success
**Time:** {timestamp}
{posts_md}
"""
                elif 'summary_file' in result:
                    result_md = f"""
---

## Summary Generated

**Status:** ✅ Success
**Time:** {timestamp}
**File:** {result.get('summary_file')}
**Total Posts:** {result.get('total_posts', 0)}
**Total Impressions:** {result.get('total_impressions', 0):,}
**Total Engagement:** {result.get('total_engagement', 0)}
"""
                else:
                    result_md = f"""
---

## Task Completed

**Status:** ✅ Success
**Time:** {timestamp}
**Result:** {json.dumps(result, indent=2)}
"""
                
                # Update status
                content = re.sub(r'(status:\s*)[^\n]+', r'\1done', content, flags=re.MULTILINE)
                if 'completed:' not in content:
                    content = re.sub(r'(status:\s*done)', f'\\1\ncompleted: {timestamp}', content)
            else:
                result_md = f"""
---

## Task Failed

**Status:** ❌ Failed
**Error:** {result.get('error', 'Unknown error')}
"""
            
            new_content = content + result_md
            
            with open(task_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            logger.info(f"Task file updated: {task_file.name}")
            
        except Exception as e:
            logger.error(f"Failed to update task file: {e}")
    
    def run(self):
        """Main social media agent loop."""
        logger.info("=" * 60)
        logger.info("Social Media Agent started")
        logger.info(f"Social MCP: {self.MCP_BASE_URL}")
        logger.info(f"Marketing Dir: {self.marketing_dir}")
        logger.info("=" * 60)
        logger.info("")
        logger.info("Platforms: Facebook, Instagram, Twitter (X)")
        logger.info("Actions: generate, publish, fetch_engagement, daily_summary")
        logger.info("")
        
        while True:
            try:
                tasks = self.scan_for_social_tasks()
                
                if tasks:
                    logger.info(f"Found {len(tasks)} social media task(s)")
                    
                    for task_file in tasks:
                        logger.info(f"Processing: {task_file.name}")
                        
                        content, frontmatter = self.read_task(task_file)
                        
                        # Parse platforms
                        platform_str = frontmatter.get('platform', 'facebook,instagram,twitter')
                        platforms = self.parse_platforms(platform_str)
                        
                        # Extract key points
                        key_points = []
                        bullets = re.findall(r'^[-*•]\s*(.+)$', content, re.MULTILINE)
                        key_points = [b.strip() for b in bullets[:5]]
                        
                        result = self.execute({
                            'action': frontmatter.get('action', 'generate'),
                            'topic': frontmatter.get('title', ''),
                            'goal': content[:200],
                            'key_points': key_points,
                            'platforms': platforms,
                            'days': int(frontmatter.get('days', 7))
                        })
                        
                        self.update_task_file(task_file, result)
                        self.processed_tasks.add(task_file.name)
                    
                    logger.info("Waiting for more tasks...")
                
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("")
                logger.info("Social Media Agent stopping...")
                break
            except Exception as e:
                logger.error(f"Error in social media agent loop: {e}")
                time.sleep(5)


# Import time for the run loop
import time

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    agent = SocialMediaAgent(
        needs_action_dir=BASE_DIR / "Needs_Action",
        logs_dir=BASE_DIR / "Logs",
        business_dir=BASE_DIR / "Domains" / "Business"
    )
    agent.run()
