from dataclasses import dataclass
from typing import Optional


@dataclass
class TrendingPost:
    post_id: str
    title: str
    content: str
    author: str
    subreddit: str
    url: str
    score: int
    upvote_ratio: float
    num_comments: int
    created_utc: float
    velocity_score: float
    engagement_rate: float
    detected_at: str
    permalink: str
    risk_level: str
    scraped_content: Optional[str] = None
    content_source: str = "reddit"


@dataclass
class VelocityMetric:
    initial_score: int
    current_score: int
    initial_time: float
    current_time: float
    velocity: float
