"""Launcher for trend_scanner package with Google Agents SDK integration"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

LOG_FILE = os.path.join(os.path.dirname(__file__), 'trend_scanner.log.txt')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8'), logging.StreamHandler()]
)

logger = logging.getLogger(__name__)


import os
import sys
from typing import List

# Predefined list of subreddits to scan
TARGET_SUBREDDITS = [
    'NoFilterNews',
    'conspiracy'
]

def main_one_scan() -> dict:
    """Run a single scan using Google Agents orchestration (no CrewAI needed)"""
    from trend_scanner.google_agents import TrendScannerOrchestrator

    REDDIT_CONFIG = {
        'client_id': os.getenv('REDDIT_CLIENT_ID', 'your_reddit_client_id'),
        'client_secret': os.getenv('REDDIT_CLIENT_SECRET', 'your_reddit_client_secret'),
        'user_agent': 'ProjectAegis-EnhancedTrendScanner/2.0-GoogleAgents'
    }

    try:
        print("🚀 Initializing Trend Scanner with Google Agents orchestration...")
        
        # Use the new TrendScannerOrchestrator (replaces CrewAI crew)
        orchestrator = TrendScannerOrchestrator(REDDIT_CONFIG)
        
        # Use predefined target subreddits
        print(f"🎯 Target subreddits: {', '.join([f'r/{s}' for s in TARGET_SUBREDDITS])}")
        orchestrator.set_target_subreddits(TARGET_SUBREDDITS)
        
        print("🔍 Running comprehensive trend analysis with Google Agents...")
        results = orchestrator.scan_trending_content()
        
        print("\n" + "="*80)
        print("📊 GOOGLE AGENTS ORCHESTRATION RESULTS")
        print("="*80)
        print(f"📈 Total trending posts found: {results['total_posts_found']}")
        print(f"🌐 Posts with scraped content: {results['posts_with_scraped_content']}")
        print(f"🔗 Total links scraped: {results['total_links_scraped']}")
        print(f"⚠️  Risk distribution: {results['risk_distribution']}")
        print(f"🕒 Timestamp: {results['timestamp']}")
        print(f"🤖 Orchestration: {results['orchestration_type']}")
        
        # Display high-priority posts with Google analysis
        high_priority = [p for p in results['trending_posts'] if p.get('risk_level') == 'HIGH']
        if high_priority:
            print(f"\n🚨 HIGH PRIORITY POSTS ({len(high_priority)})")
            print("-" * 50)
            for i, post in enumerate(high_priority[:3]):
                print(f"\n{i+1}. {post['title']}")
                print(f"   📍 r/{post['subreddit']} | ⚡ {post['velocity_score']:.1f}/hr | 👍 {post['score']}")
                print(f"   🎯 Risk: {post['risk_level']} | 📊 Source: {post['content_source']}")
                if post.get('scraped_content'):
                    print(f"   🌐 External content analyzed: {len(post['scraped_content'])} chars")
        
        medium_priority = [p for p in results['trending_posts'] if p.get('risk_level') == 'MEDIUM']
        if medium_priority:
            print(f"\n⚠️ MEDIUM PRIORITY POSTS ({len(medium_priority)})")
            print("-" * 50)
            for post in medium_priority[:2]:
                print(f"• {post['title'][:80]}...")
                print(f"  r/{post['subreddit']} | {post['velocity_score']:.1f}/hr | {post['score']} points")
        
        print(f"\n🤖 GOOGLE AGENTS ANALYSIS SUMMARY")
        print("-" * 50)
        print(results['risk_assessment'])
        
        print("\n" + "="*80)
        
    except Exception as e:
        logger.error(f"Error running enhanced scan: {e}")
        print(f"❌ Error: {e}")


def show_installation_requirements():
    """Display installation and setup requirements"""
    print("""
🔧 INSTALLATION REQUIREMENTS FOR GOOGLE AGENTS ORCHESTRATION:

1. Install packages:
   pip install -r requirements.txt

2. Required API Keys:
   - Google API Key (for Google Agents SDK)
   - Gemini API Key (for LLM capabilities)  
   - Reddit API credentials

3. Environment Variables (.env file):
   GOOGLE_API_KEY=your_google_api_key
   GEMINI_API_KEY=your_gemini_api_key
   REDDIT_CLIENT_ID=your_reddit_client_id
   REDDIT_CLIENT_SECRET=your_reddit_client_secret

4. Key Features:
   ✅ Google Agents orchestration (replaces CrewAI)
   ✅ Source credibility analysis with Gemini AI
   ✅ Reddit trend scanning and risk assessment
   ✅ Multi-agent workflow coordination
   ✅ Enhanced misinformation pattern detection

5. Usage:
   python trend_scanner_agent.py

6. Target Subreddits:
   The scanner monitors these subreddits: {', '.join([f'r/{s}' for s in TARGET_SUBREDDITS])}
   To modify the list, edit TARGET_SUBREDDITS in the code.

📚 See trend_scanner/README.md for detailed documentation.
📦 All functionality now in google_agents.py - no CrewAI dependencies!
    """)


if __name__ == '__main__':
    show_installation_requirements()
    
    print(f"📋 Scanning {len(TARGET_SUBREDDITS)} subreddits: {', '.join([f'r/{s}' for s in TARGET_SUBREDDITS])}")
    
    # Check if API keys are configured
    if not os.getenv('GOOGLE_API_KEY') and not os.getenv('GEMINI_API_KEY'):
        print("⚠️  No Google API key found. Please configure GOOGLE_API_KEY or GEMINI_API_KEY")
        print("The system will attempt to run with fallback analysis.")
    
    if not os.getenv('REDDIT_CLIENT_ID'):
        print("⚠️  No Reddit API credentials found. Please configure REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET")
    
    main_one_scan()