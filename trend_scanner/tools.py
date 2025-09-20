import time
import json
import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from .scraper import WebContentScraper

logger = logging.getLogger(__name__)


# Long-form prompts moved here for easier editing and reuse by crew code.
RISK_ASSESSMENT_PROMPT = """
Analyze this Reddit post for potential misinformation risk. Consider both the Reddit metadata and the actual content.

REDDIT METADATA:
- Title: {title}
- Subreddit: r/{subreddit}
- Score: {score} upvotes
- Upvote Ratio: {upvote_ratio}
- Comments: {num_comments}
- Age: {age_hours} hours
- Author: {author}
- Has External Content: {has_external_content}

CONTENT TO ANALYZE:
{content}...

RISK ASSESSMENT CRITERIA:
1. HIGH RISK indicators:
    - Claims about health/medical information without sources
    - Political conspiracy theories or election fraud claims
    - Sensational headlines with unverified information
    - Content from known unreliable sources
    - Manipulated statistics or cherry-picked data
    - Urgent/emergency claims designed to cause panic
    - Anti-science or pseudoscience content

2. MEDIUM RISK indicators:
    - Controversial topics with one-sided presentation
    - Emotional language designed to provoke strong reactions
    - Unverified claims about current events
    - Content lacking proper sources or context
    - Potentially misleading headlines

3. LOW RISK indicators:
    - Well-sourced information from reputable outlets
    - Personal opinions clearly marked as such
    - Entertainment or non-factual content
    - Properly contextualized information

ADDITIONAL FACTORS:
- Unusual engagement patterns (comments vs upvotes ratio)
- Rapid viral growth in controversial subreddits
- Content that contradicts established scientific consensus

Based on the content analysis above, respond with ONLY one word: HIGH, MEDIUM, or LOW
"""

SCAN_TASK_PROMPT = """
Perform comprehensive scanning of r/{subreddit} for trending posts that could contain misinformation.

Your enhanced analysis should include:
1. Posts with high velocity (rapid upvote growth)
2. Content analysis of Reddit posts AND linked external content
3. Detection of suspicious claims, unsourced assertions, or misleading information
4. Evaluation of source credibility for linked content
5. Assessment of emotional manipulation techniques
6. Identification of conspiracy theories or pseudoscience

Subreddit: {subreddit}
Scan parameters: limit=20, sort_type=new

Pay special attention to:
- Posts linking to external articles or sources
- Health/medical misinformation
- Political conspiracy theories
- Pseudoscientific claims
- Sensational headlines with unverified content

Return detailed information about trending posts with full content analysis.
"""

ASSESSMENT_TASK_PROMPT = """
Perform comprehensive analysis of all trending posts found across all subreddits, including full content analysis of scraped external sources.

Scan results from all subreddits:
{scan_results}

Your comprehensive analysis should:
1. Rank posts by potential misinformation risk using both metadata and content analysis
2. Identify the most urgent posts needing immediate verification
3. Categorize posts by misinformation type (health, political, scientific, etc.)
4. Highlight posts with the highest viral potential and risk combination
5. Assess the credibility and bias of external sources that were scraped
6. Identify coordinated misinformation campaigns or similar narratives across posts

Priority factors:
- HIGH risk posts with scraped external content containing false claims
- Posts with high velocity in controversial subreddits
- Content contradicting scientific consensus without proper evidence
- Sensational claims designed to provoke emotional responses
- Unsourced medical or health advice
- Political conspiracy theories gaining rapid traction

For each high-priority post, provide:
- Risk level justification based on content analysis
- Key claims that need fact-checking
- Source credibility assessment
- Viral potential score
- Recommended verification priority
"""


class RedditScanInput(BaseModel):
    subreddit_name: str = Field(description="Name of the subreddit to scan")
    limit: int = Field(default=20, description="Number of posts to scan")
    sort_type: str = Field(default="new", description="Sort type: new, rising, hot")


class RedditScanOutput(BaseModel):
    trending_posts: List[Dict[str, Any]] = Field(description="List of trending posts found")
    scan_summary: str = Field(description="Summary of the scan results")


class RedditScanTool(BaseTool):
    name: str = "reddit_scanner"
    description: str = "Scans Reddit subreddits for rapidly trending posts that could contain misinformation"

    def __init__(self, reddit_client, llm_wrapper, velocity_threshold=25, min_score_threshold=50):
        super().__init__()
        object.__setattr__(self, '_reddit', reddit_client)
        object.__setattr__(self, '_llm_wrapper', llm_wrapper)
        object.__setattr__(self, '_velocity_threshold', velocity_threshold)
        object.__setattr__(self, '_min_score_threshold', min_score_threshold)
        object.__setattr__(self, '_tracked_posts', {})
        object.__setattr__(self, '_scraper', WebContentScraper())
        object.__setattr__(self, '_scraped_cache', {})

    def calculate_velocity(self, post_id: str, current_score: int, created_utc: float) -> float:
        current_time = time.time()
        if post_id in self._tracked_posts:
            metric = self._tracked_posts[post_id]
            time_diff = current_time - metric.current_time
            score_diff = current_score - metric.current_score
            metric.current_score = current_score
            metric.current_time = current_time
            if time_diff > 0:
                velocity = (score_diff / time_diff) * 3600
                metric.velocity = velocity
                return velocity
            return metric.velocity
        else:
            age_seconds = max(current_time - created_utc, 1.0)
            hours = age_seconds / 3600.0
            proxy_velocity = current_score / hours if hours > 0 else float(current_score) * 3600.0
            self._tracked_posts[post_id] = type('VM', (), {
                'initial_score': current_score,
                'current_score': current_score,
                'initial_time': current_time,
                'current_time': current_time,
                'velocity': proxy_velocity
            })()
            return proxy_velocity

    def extract_post_content(self, submission) -> Tuple[str, Optional[str], str]:
        reddit_content = ""
        scraped_content = None
        content_source = "reddit"

        if submission.selftext:
            reddit_content = submission.selftext
            content_source = "selftext"
        elif submission.url:
            if self._scraper.is_scrapeable_url(submission.url):
                url_hash = hashlib.md5(submission.url.encode()).hexdigest()
                if url_hash in self._scraped_cache:
                    scraped_content = self._scraped_cache[url_hash]
                    content_source = "cached_scraped"
                else:
                    scraped_content, scrape_method = self._scraper.scrape_content(submission.url)
                    if scraped_content:
                        self._scraped_cache[url_hash] = scraped_content
                        content_source = f"scraped_{scrape_method}"
                    else:
                        content_source = "link_failed"
            else:
                reddit_content = f"Link post: {submission.url}"
                content_source = "link_not_scrapeable"

        if scraped_content:
            combined_content = f"Reddit Title: {submission.title}\n"
            if reddit_content:
                combined_content += f"Reddit Content: {reddit_content}\n\n"
            combined_content += f"Linked Content: {scraped_content}"
            return combined_content, scraped_content, content_source
        else:
            return reddit_content or f"Link: {submission.url}", None, content_source

    def assess_risk_level(self, submission, content: str, scraped_content: Optional[str], llm_wrapper) -> str:
        try:
            # Prepare metadata and formatted fields for the long prompt
            metadata = {
                'title': submission.title,
                'subreddit': submission.subreddit.display_name,
                'score': submission.score,
                'upvote_ratio': f"{submission.upvote_ratio:.2f}",
                'num_comments': submission.num_comments,
                'age_hours': f"{(time.time() - submission.created_utc) / 3600:.1f}",
                'author': str(submission.author) if submission.author else "[deleted]",
                'has_external_content': str(scraped_content is not None),
                'content': (content or '')[:2000]
            }

            prompt = RISK_ASSESSMENT_PROMPT.format(**metadata)

            response = llm_wrapper.invoke(prompt)
            risk_level = getattr(response, 'content', str(response)).strip().upper()

            if risk_level in ['HIGH', 'MEDIUM', 'LOW']:
                logger.debug(f"assess_risk_level: LLM returned {risk_level} for post {getattr(submission,'id',None)}")
                return risk_level
            else:
                logger.warning(f"assess_risk_level: unexpected LLM response '{risk_level}' - defaulting to LOW")
                return 'LOW'
        except Exception as e:
            logger.warning(f"LLM risk assessment failed: {e} - defaulting to LOW")
            return 'LOW'

    def _run(self, subreddit_name: str, limit: int = 20, sort_type: str = "new") -> str:
        try:
            subreddit = self._reddit.subreddit(subreddit_name)
            trending_posts = []
            processed_count = 0
            scraped_count = 0

            if sort_type == "new":
                submissions = subreddit.new(limit=limit)
            elif sort_type == "rising":
                submissions = subreddit.rising(limit=limit)
            elif sort_type == "hot":
                submissions = subreddit.hot(limit=limit)
            else:
                submissions = subreddit.new(limit=limit)

            for submission in submissions:
                processed_count += 1
                content, scraped_content, content_source = self.extract_post_content(submission)
                if scraped_content:
                    scraped_count += 1
                velocity = self.calculate_velocity(submission.id, submission.score, submission.created_utc)
                engagement_rate = submission.num_comments / max(submission.score, 1)
                is_recent = (time.time() - submission.created_utc) < 86400
                meets_basic_score = submission.score >= (self._min_score_threshold * 0.3)
                if is_recent and meets_basic_score:
                    risk_level = self.assess_risk_level(submission, content, scraped_content, self._llm_wrapper)
                else:
                    risk_level = 'LOW'

                threshold_multiplier = {"HIGH": 0.3, "MEDIUM": 0.5, "LOW": 1.0}
                if scraped_content:
                    threshold_multiplier = {"HIGH": 0.2, "MEDIUM": 0.4, "LOW": 0.8}

                adjusted_threshold = self._velocity_threshold * threshold_multiplier[risk_level]
                meets_velocity = velocity >= adjusted_threshold
                meets_score = submission.score >= self._min_score_threshold
                if risk_level == 'HIGH' and scraped_content:
                    meets_score = submission.score >= (self._min_score_threshold * 0.5)

                if (meets_velocity and meets_score and is_recent) or (risk_level == 'HIGH' and scraped_content and is_recent):
                    post_data = {
                        'post_id': submission.id,
                        'title': submission.title,
                        'content': content[:1000] if content else "",
                        'scraped_content': scraped_content[:1000] if scraped_content else None,
                        'content_source': content_source,
                        'author': str(submission.author) if submission.author else "[deleted]",
                        'subreddit': submission.subreddit.display_name,
                        'url': submission.url,
                        'score': submission.score,
                        'upvote_ratio': submission.upvote_ratio,
                        'num_comments': submission.num_comments,
                        'created_utc': submission.created_utc,
                        'velocity_score': velocity,
                        'engagement_rate': engagement_rate,
                        'risk_level': risk_level,
                        'detected_at': __import__('datetime').datetime.now().isoformat(),
                        'permalink': f"https://reddit.com{submission.permalink}"
                    }
                    trending_posts.append(post_data)

            def combined_score(post):
                risk_multiplier = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
                return post['velocity_score'] * risk_multiplier[post['risk_level']]

            trending_posts.sort(key=combined_score, reverse=True)

            result = {
                'trending_posts': trending_posts,
                'scan_summary': f"Scanned r/{subreddit_name} ({processed_count} posts), scraped {scraped_count} links, found {len(trending_posts)} trending posts",
                'processed_count': processed_count,
                'scraped_count': scraped_count,
                'subreddit': subreddit_name
            }

            return json.dumps(result, indent=2)
        except Exception as e:
            return json.dumps({'trending_posts': [], 'scan_summary': str(e), 'processed_count': 0, 'scraped_count': 0, 'subreddit': subreddit_name}, indent=2)
