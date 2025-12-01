import os
import requests
from typing import Dict, Any, List


def get_finnhub_news(symbol: str = None, category: str = "general", min_id: int = 0) -> Dict[str, Any]:
    """Fetch latest market news from Finnhub.

    Args:
        symbol: Optional ticker symbol to filter news (Finnhub generic endpoint does not filter by symbol,
                but we can post‑filter the results).
        category: One of "general", "forex", "crypto", "merger".
        min_id: Return only news items with ID > min_id.
    """
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        print("Warning: FINNHUB_API_KEY not found in environment")
        return {"error": "FINNHUB_API_KEY not set. Add it to your .env file."}

    try:
        url = "https://finnhub.io/api/v1/news"
        # Build request parameters. If a symbol is provided we request company‑specific news
        # (Finnhub uses the 'symbol' query param for that). Otherwise we request general news by category.
        params = {"token": api_key}
        if symbol:
            params["symbol"] = symbol.upper()
            # Optionally include category to further filter, but Finnhub ignores it when 'symbol' is present
            if category:
                params["category"] = category
        else:
            # No symbol – use category (default "general")
            params["category"] = category
        if min_id:
            params["minId"] = min_id
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        # Finnhub returns a list of news items; filter by symbol if possible
        # Each item may contain "related" or "ticker" fields. If a symbol is provided but no items match,
        # we fall back to returning the first few general news items.
        if symbol:
            filtered = [item for item in data if symbol.upper() in item.get("related", []) or symbol.upper() in item.get("ticker", "")]
            if not filtered:
                # No symbol‑specific items – fall back to generic news
                filtered = data
        else:
            filtered = data
        # Map to our expected schema (limit to 5 items)
        news_items = []
        for item in filtered[:5]:
            news_items.append({
                "category": item.get("category"),
                "datetime": item.get("datetime"),
                "headline": item.get("headline"),
                "id": item.get("id"),
                "image": item.get("image"),
                "related": item.get("related"),
                "source": item.get("source"),
                "summary": item.get("summary"),
                "url": item.get("url"),
            })
        return {"news": news_items}
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error fetching Finnhub news for {symbol}: {e}")
        return {"error": f"HTTP error: {str(e)}"}
    except Exception as e:
        print(f"Error fetching Finnhub news for {symbol}: {e}")
        return {"error": str(e)}
