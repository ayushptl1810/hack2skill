# Trend Scanner with Google Agents SDK

Enhanced Reddit trend scanning and misinformation detection powered by Google Agents SDK orchestration.

## Features

- **Google Agents Integration**: Advanced misinformation detection using Google's fact-checking and search capabilities
- **Real-time Reddit Scanning**: Monitor trending posts across multiple subreddits
- **Content Analysis**: Comprehensive analysis of both Reddit posts and linked external content
- **Risk Assessment**: Multi-factor risk scoring using Google's knowledge base
- **Google Orchestration**: Pure Google Agents SDK workflow management

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
# .env file
GOOGLE_API_KEY=your_google_api_key
GEMINI_API_KEY=your_gemini_api_key  # Alternative to GOOGLE_API_KEY
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
```

## Usage

### Basic Usage

```python
from trend_scanner.google_agents import TrendScannerOrchestrator

# Configure Reddit API
reddit_config = {
    'client_id': 'your_reddit_client_id',
    'client_secret': 'your_reddit_client_secret',
    'user_agent': 'TrendScanner/2.0'
}

# Initialize with Google Agents orchestration  
orchestrator = TrendScannerOrchestrator(reddit_config)

# Subreddits are predefined in the code - no need to configure manually
# Default list: ['worldnews', 'technology', 'politics', 'news', 'conspiracy', 'science', 'economics', 'climate']

# Run analysis
results = orchestrator.scan_trending_content()
print(results)
```

### Command Line Usage

```bash
# Simply run the scanner - subreddits are predefined
python trend_scanner_agent.py
```

### Using Google Misinformation Tool Directly

```python
from trend_scanner.google_misinformation_tool import GoogleMisinformationTool

tool = GoogleMisinformationTool(google_api_key='your_api_key')

result = tool._run(
    content="Breaking: New study shows that...",
    url="https://example.com/article",
    claims_to_check=["Study shows X", "Experts claim Y"]
)
print(result)
```

### Running the Launcher

```bash
python trend_scanner_agent.py
```

## Google Agents SDK Features

The integration provides:

1. **Enhanced Fact-Checking**: Real-time verification against Google's fact-check database
2. **Source Credibility Analysis**: Automated assessment of content source reliability
3. **Advanced Content Analysis**: Pattern recognition for misinformation indicators
4. **Multi-factor Risk Scoring**: Comprehensive risk assessment using multiple signals
5. **Recommendation Engine**: Specific next steps for content verification

## Module Structure

- `models.py`: Data structures for trending posts and metrics
- `scraper.py`: Web content extraction and scraping
- `tools.py`: Reddit scanning tool with Google Agents integration
- `google_agents.py`: Google Agents SDK orchestration and workflow management

## Risk Levels

- **HIGH**: Immediate verification required, high misinformation indicators
- **MEDIUM**: Additional verification recommended, some risk factors present  
- **LOW**: Content appears credible, standard monitoring sufficient

## API Requirements

- Google API Key (for Google Agents SDK)
- Reddit API credentials (client ID and secret)
- Gemini API access (for LLM capabilities)

## Troubleshooting

If Google Agents SDK fails to initialize:
- Verify your Google API key is valid
- Check that you have the necessary API quotas
- The system will fall back to standard LLM-based analysis

For Reddit API issues:
- Ensure your Reddit app is properly configured
- Check rate limiting settings
- Verify user agent string format

## Version

Current version: 2.0.0 with Google Agents SDK integration