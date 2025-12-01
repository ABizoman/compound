import os
import requests
from typing import Dict, Any, Optional

def get_market_news(ticker: str = None, limit: int = 5, published_utc_lte: str = None) -> Dict[str, Any]:
    """Fetch market news from the new API.

    Args:
        ticker: Optional ticker symbol to filter news.
        limit: Number of results to return (default 5).
        published_utc_lte: Filter news published on or before this timestamp (ISO 8601).
    """
    # Use a default base URL if not specified in env, based on user sample
    base_url = "https://api.massive.com/v2/reference/news"
    api_key = os.getenv("MASSIVE_API_KEY")
    
    # Error if no api key is set
    if not api_key:
        raise ValueError("MASSIVE_API_KEY not found.")
    
    params = {
        "limit": limit,
        "sort": "published_utc",
        "order": "desc"
    }
    
    if ticker:
        params["ticker"] = ticker.upper()
        
    if published_utc_lte:
        params["published_utc.lte"] = published_utc_lte

    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}" # Assuming Bearer auth, or maybe query param?
        # Many APIs use query param 'apiKey' or 'token'. Finnhub used 'token'.
        # The user didn't specify auth method. I'll try adding it as a query param 'apiKey' as well if header fails?
        # Or maybe just query param. Polygon uses ?apiKey=...
        # Let's assume query param for safety if it's like Polygon/Finnhub.
        params["apiKey"] = api_key

    try:
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
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
