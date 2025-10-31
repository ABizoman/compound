import os
import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path


app = FastAPI(title="Stock Local MCP Server")


class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]


# Cache for price data
_price_cache = {}
_cache_file = Path("./data/price_cache.json")


def load_cache():
    """Load price cache from file."""
    global _price_cache
    if _cache_file.exists():
        try:
            with open(_cache_file, 'r') as f:
                _price_cache = json.load(f)
        except Exception:
            _price_cache = {}


def save_cache():
    """Save price cache to file."""
    _cache_file.parent.mkdir(parents=True, exist_ok=True)
    with open(_cache_file, 'w') as f:
        json.dump(_price_cache, f, indent=2)


def get_finnhub_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """Get current quote from Finnhub."""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return None
    
    try:
        url = "https://finnhub.io/api/v1/quote"
        params = {"symbol": symbol, "token": api_key}
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "c" in data:  # 'c' is current price
            return {
                "symbol": symbol,
                "current": data.get("c"),
                "open": data.get("o"),
                "high": data.get("h"),
                "low": data.get("l"),
                "previous_close": data.get("pc"),
                "timestamp": datetime.now().isoformat()
            }
        return None
    except Exception as e:
        print(f"Error fetching Finnhub quote: {e}")
        return None


def get_finnhub_candle(symbol: str, resolution: str = "D", count: int = 1) -> Optional[List[Dict[str, Any]]]:
    """Get historical candle data from Finnhub."""
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        return None
    
    try:
        url = "https://finnhub.io/api/v1/stock/candle"
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=count * 2)).timestamp())
        
        params = {
            "symbol": symbol,
            "resolution": resolution,
            "from": start_time,
            "to": end_time,
            "token": api_key
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("s") == "ok" and data.get("c"):
            candles = []
            for i in range(len(data["c"])):
                candles.append({
                    "timestamp": data["t"][i],
                    "open": data["o"][i],
                    "high": data["h"][i],
                    "low": data["l"][i],
                    "close": data["c"][i],
                    "volume": data.get("v", [])[i] if "v" in data else None
                })
            return candles[-count:]  # Return last N candles
        return None
    except Exception as e:
        print(f"Error fetching Finnhub candle: {e}")
        return None


# Available stock tools
STOCK_TOOLS = [
    {
        "name": "get_current_price",
        "description": "Get current price for a stock symbol. Uses cached data if available to reduce API calls.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol (e.g., AAPL, MSFT)"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_daily_ohlc",
        "description": "Get daily OHLC (Open, High, Low, Close) data for a stock symbol. Returns cached data if available.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days of data to retrieve (default: 1)"
                }
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_prices_batch",
        "description": "Get current prices for multiple stock symbols at once",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of stock symbols"
                }
            },
            "required": ["symbols"]
        }
    }
]


@app.on_event("startup")
async def startup_event():
    """Load cache on startup."""
    load_cache()


@app.post("/mcp/tools/list")
async def list_tools():
    """List available tools."""
    return {"tools": STOCK_TOOLS}


@app.post("/mcp/tools/call")
async def call_tool(request: ToolCallRequest):
    """Call a stock tool."""
    try:
        if request.name == "get_current_price":
            symbol = request.arguments.get("symbol", "").upper()
            
            # Check cache first
            cache_key = f"{symbol}_current"
            if cache_key in _price_cache:
                cached_data = _price_cache[cache_key]
                cache_time = datetime.fromisoformat(cached_data.get("timestamp", ""))
                # Use cache if less than 5 minutes old
                if (datetime.now() - cache_time).total_seconds() < 300:
                    return {
                        "content": [
                            {"type": "text", "text": f"{symbol}: ${cached_data['price']:.2f} (cached)"}
                        ]
                    }
            
            # Fetch from API
            quote = get_finnhub_quote(symbol)
            
            if quote:
                price = quote["current"]
                # Update cache
                _price_cache[cache_key] = {
                    "price": price,
                    "timestamp": datetime.now().isoformat()
                }
                save_cache()
                
                return {
                    "content": [
                        {"type": "text", "text": f"{symbol}: ${price:.2f}"}
                    ]
                }
            else:
                return {
                    "content": [
                        {"type": "text", "text": f"Error: Could not fetch price for {symbol}. Check FINNHUB_API_KEY."}
                    ]
                }
        
        elif request.name == "get_daily_ohlc":
            symbol = request.arguments.get("symbol", "").upper()
            days = request.arguments.get("days", 1)
            
            # Check cache
            cache_key = f"{symbol}_ohlc_{days}"
            if cache_key in _price_cache:
                cached_data = _price_cache[cache_key]
                cache_time = datetime.fromisoformat(cached_data.get("timestamp", ""))
                # Use cache if less than 1 hour old
                if (datetime.now() - cache_time).total_seconds() < 3600:
                    return {
                        "content": [
                            {"type": "text", "text": json.dumps(cached_data["data"], indent=2)}
                        ]
                    }
            
            # Fetch from API
            candles = get_finnhub_candle(symbol, resolution="D", count=days)
            
            if candles:
                # Update cache
                _price_cache[cache_key] = {
                    "data": candles,
                    "timestamp": datetime.now().isoformat()
                }
                save_cache()
                
                return {
                    "content": [
                        {"type": "text", "text": json.dumps(candles, indent=2)}
                    ]
                }
            else:
                return {
                    "content": [
                        {"type": "text", "text": f"Error: Could not fetch OHLC data for {symbol}"}
                    ]
                }
        
        elif request.name == "get_prices_batch":
            symbols = [s.upper() for s in request.arguments.get("symbols", [])]
            
            results = {}
            for symbol in symbols:
                # Try cache first
                cache_key = f"{symbol}_current"
                if cache_key in _price_cache:
                    cached_data = _price_cache[cache_key]
                    cache_time = datetime.fromisoformat(cached_data.get("timestamp", ""))
                    if (datetime.now() - cache_time).total_seconds() < 300:
                        results[symbol] = cached_data["price"]
                        continue
                
                # Fetch from API
                quote = get_finnhub_quote(symbol)
                if quote:
                    price = quote["current"]
                    results[symbol] = price
                    _price_cache[cache_key] = {
                        "price": price,
                        "timestamp": datetime.now().isoformat()
                    }
            
            save_cache()
            
            return {
                "content": [
                    {"type": "text", "text": json.dumps(results, indent=2)}
                ]
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {request.name}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)

