"""News tools for getting market news and insights.

Uses backtest context for date filtering when in backtest mode.
"""

import os
import requests
from typing import Dict, Any, Optional
from .context import get_context


def get_market_insights(ticker: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    """Fetch market news from Massive API.
    
    Args:
        ticker: Optional single ticker symbol to filter news (e.g. 'AAPL'). Do NOT pass a list.
        limit: Number of results to return (default 5)
        
    Returns:
        Dict with news items or error
    """
    ctx = get_context()
    
    base_url = "https://api.massive.com/v2/reference/news"
    api_key = os.getenv("MASSIVE_API_KEY")
    
    if not api_key:
        return {"error": "MASSIVE_API_KEY not found"}
    
    params = {
        "limit": limit,
        "sort": "published_utc",
        "order": "desc",
        "apiKey": api_key
    }
    
    if ticker:
        params["ticker"] = ticker.upper()
    
    # In backtest mode, filter news to current simulated date
    if ctx.is_backtest_mode and ctx.current_date:
        params["published_utc.lte"] = ctx.current_date

    try:
        response = requests.get(base_url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = data.get("results", [])
        
        # Format results for the agent
        news_items = []
        for item in results:
            news_items.append({
                "title": item.get("title"),
                "author": item.get("author"),
                "published_utc": item.get("published_utc"),
                "article_url": item.get("article_url"),
                "description": item.get("description"),
                "tickers": item.get("tickers"),
                "insights": item.get("insights", [])
            })
            
        return {"news": news_items}
        
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error fetching news: {e}")
        return {"error": f"HTTP error: {str(e)}"}
    except Exception as e:
        print(f"Error fetching news: {e}")
        return {"error": str(e)}
