import os
import json
import requests
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
_project_root = Path(__file__).parent.parent.parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    # Fallback to default behavior (searches current directory and parents)
    load_dotenv()


app = FastAPI(title="Search MCP Server")


class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]


# Available search tools
SEARCH_TOOLS = [
    {
        "name": "search_market_news",
        "description": "Search for market news and information about stocks. Uses Alpha Vantage to fetch relevant market information.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for market news and information"
                },
                "symbols": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of stock symbols to filter news for"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_market_insights",
        "description": "Get market insights from Alpha Vantage API",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol to get insights for"
                }
            },
            "required": ["symbol"]
        }
    }
]


def get_alpha_vantage_news(symbol: str) -> Dict[str, Any]:
    """Fetch news from Alpha Vantage API."""
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY")
    if not api_key:
        print("Warning: ALPHA_VANTAGE_API_KEY not found in environment")
        return {"error": "ALPHA_VANTAGE_API_KEY not set. Add it to your .env file."}
    
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": symbol,
            "apikey": api_key,
            "limit": 5
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Check for API errors in response
        if "Error Message" in data:
            print(f"Alpha Vantage API error: {data.get('Error Message')}")
            return {"error": data.get("Error Message")}
        if "Note" in data:
            print(f"Alpha Vantage API note: {data.get('Note')}")
            return {"error": data.get("Note")}
        
        return data
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error fetching Alpha Vantage news for {symbol}: {e}")
        if e.response is not None:
            try:
                error_data = e.response.json()
                print(f"Error response: {error_data}")
            except:
                print(f"Error response text: {e.response.text}")
        return {"error": f"HTTP error: {str(e)}"}
    except Exception as e:
        print(f"Error fetching Alpha Vantage news for {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


@app.post("/mcp/tools/list")
async def list_tools():
    """List available tools."""
    return {"tools": SEARCH_TOOLS}


@app.post("/mcp/tools/call")
async def call_tool(request: ToolCallRequest):
    """Call a search tool."""
    try:
        if request.name == "search_market_news":
            query = request.arguments.get("query", "")
            symbols = request.arguments.get("symbols", [])
            
            results = []
            
            # Try Alpha Vantage for each symbol
            for symbol in symbols[:3]:  # Limit to 3 symbols to avoid rate limits
                av_result = get_alpha_vantage_news(symbol)
                if "error" not in av_result:
                    results.append(f"Alpha Vantage News for {symbol}: {json.dumps(av_result, indent=2)}")
            
            if not results:
                results.append("No search results available. Check API keys.")
            
            return {
                "content": [
                    {"type": "text", "text": "\n\n".join(results)}
                ]
            }
        
        elif request.name == "get_market_insights":
            symbol = request.arguments.get("symbol", "")
            result = get_alpha_vantage_news(symbol)
            
            if "error" in result:
                return {
                    "content": [
                        {"type": "text", "text": f"Error: {result['error']}"}
                    ]
                }
            
            return {
                "content": [
                    {"type": "text", "text": json.dumps(result, indent=2)}
                ]
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {request.name}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

