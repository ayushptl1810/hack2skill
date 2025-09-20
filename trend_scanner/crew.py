import os
import logging
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from crewai import Agent, Task, Crew, Process, LLM
from .tools import RedditScanTool, SCAN_TASK_PROMPT, ASSESSMENT_TASK_PROMPT

logger = logging.getLogger(__name__)


class TrendScannerCrew:
    def __init__(self, reddit_config: Dict[str, str], gemini_api_key: Optional[str] = None):
        gemini_key = gemini_api_key or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be provided")
        os.environ['GEMINI_API_KEY'] = gemini_key

        class SimpleLLMWrapper:
            def __init__(self):
                import litellm
                self.completion = litellm.completion

            def invoke(self, prompt):
                response = self.completion(
                    model="gemini/gemini-1.5-flash",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1
                )
                class ResponseWrapper:
                    def __init__(self, content):
                        self.content = content
                return ResponseWrapper(response.choices[0].message.content)

        self.llm = SimpleLLMWrapper()

        self.crewai_llm = LLM(
            model="gemini/gemini-1.5-flash",
            api_key=gemini_key,
            temperature=0.4
        )

        self.reddit = __import__('praw').Reddit(
            client_id=reddit_config['client_id'],
            client_secret=reddit_config['client_secret'],
            user_agent=reddit_config['user_agent'],
            ratelimit_seconds=10,
            timeout=30
        )

        self.reddit_tool = RedditScanTool(self.reddit, self.llm, velocity_threshold=25.0, min_score_threshold=50)

        self.target_subreddits = ['worldnews']

        self.trend_scout_agent = Agent(
            role='Enhanced Reddit Trend Scout',
            goal='Identify rapidly trending posts across Reddit that could contain misinformation, including analysis of linked external content',
            backstory='You are an expert at spotting viral content on Reddit with advanced content analysis capabilities.',
            tools=[self.reddit_tool],
            verbose=True,
            allow_delegation=False,
            llm=self.crewai_llm
        )

        self.risk_assessor_agent = Agent(
            role='Advanced Content Risk Assessor',
            goal='Evaluate the risk level of trending posts based on comprehensive content analysis including external sources',
            backstory='You are a specialist in identifying potentially harmful content with access to the full text of external articles and sources.',
            verbose=True,
            allow_delegation=False,
            llm=self.crewai_llm
        )

    def create_scan_tasks(self) -> List[Task]:
        tasks = []
        for subreddit in self.target_subreddits:
            task = Task(
                description=SCAN_TASK_PROMPT.format(subreddit=subreddit),
                agent=self.trend_scout_agent,
                expected_output="JSON formatted list of trending posts with comprehensive content analysis, scraped external content, and detailed risk assessments"
            )
            tasks.append(task)
        return tasks

    def create_assessment_task(self, scan_results) -> Task:
        return Task(
            description=ASSESSMENT_TASK_PROMPT.format(scan_results=scan_results),
            agent=self.risk_assessor_agent,
            expected_output="Comprehensive prioritized analysis of trending posts with detailed risk assessment, content analysis summary, and specific recommendations for fact-checking priorities"
        )

    def scan_trending_content(self) -> Dict[str, Any]:
        scan_tasks = self.create_scan_tasks()
        scan_crew = Crew(agents=[self.trend_scout_agent], tasks=scan_tasks, process=Process.sequential, verbose=True)
        scan_results = scan_crew.kickoff()

        all_trending_posts = []
        scan_summaries = []
        total_scraped = 0

        if isinstance(scan_results, list):
            for i, result in enumerate(scan_results):
                parsed = None
                if isinstance(result, dict):
                    parsed = result
                else:
                    text = str(result)
                    try:
                        parsed = json.loads(text)
                    except Exception:
                        parsed = None
                    if parsed is None:
                        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
                        if m:
                            try:
                                parsed = json.loads(m.group(1))
                            except Exception:
                                parsed = None
                    if parsed and 'trending_posts' in parsed:
                        all_trending_posts.extend(parsed.get('trending_posts', []))
                        scan_summaries.append(parsed.get('scan_summary', ''))
                        total_scraped += int(parsed.get('scraped_count', 0) or 0)
        print(type(scan_results))

        assessment_task = self.create_assessment_task(scan_results)
        assessment_crew = Crew(agents=[self.risk_assessor_agent], tasks=[assessment_task], process=Process.sequential, verbose=True)
        assessment_result = assessment_crew.kickoff()

        risk_distribution = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1}
        posts_with_scraped_content = 0
        for post in all_trending_posts:
            risk_distribution[post.get('risk_level', 'LOW')] += 1
            if post.get('scraped_content'):
                posts_with_scraped_content += 1

        return {
            'trending_posts': all_trending_posts,
            'scan_summaries': scan_summaries,
            'risk_assessment': str(assessment_result),
            'total_posts_found': len(all_trending_posts),
            'posts_with_scraped_content': posts_with_scraped_content,
            'total_links_scraped': total_scraped,
            'risk_distribution': risk_distribution,
            'timestamp': datetime.now().isoformat()
        }
