"""trend_scanner package init

This file intentionally avoids importing submodules at package import time so
that tooling and lightweight checks won't require heavy external dependencies.
Use explicit imports like `from trend_scanner.scraper import WebContentScraper`.
"""

__all__ = [
    'models', 'scraper', 'tools', 'crew'
]

