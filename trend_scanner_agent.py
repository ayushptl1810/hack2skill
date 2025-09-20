"""Launcher for trend_scanner package"""

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


def main_one_scan():
    from trend_scanner.crew import TrendScannerCrew

    REDDIT_CONFIG = {
        'client_id': os.getenv('REDDIT_CLIENT_ID', 'your_reddit_client_id'),
        'client_secret': os.getenv('REDDIT_CLIENT_SECRET', 'your_reddit_client_secret'),
        'user_agent': 'ProjectAegis-EnhancedTrendScanner/2.0'
    }

    try:
        crew = TrendScannerCrew(REDDIT_CONFIG)
        results = crew.scan_trending_content()
        print(results)
    except Exception as e:
        logger.error(f"Error running scan: {e}")


if __name__ == '__main__':
    main_one_scan()