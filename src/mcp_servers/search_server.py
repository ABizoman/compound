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
        "name": "get_market_insights",
        "description": "Get market news and insights for a specific stock from Alpha Vantage. Returns a concise list of recent news items.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol to get insights for"
                },
                "time_from": {
                    "type": "string",
                    "description": "Start of time range in YYYYMMDDTHHMM format (e.g., 20220410T0130)"
                },
                "time_to": {
                    "type": "string",
                    "description": "End of time range in YYYYMMDDTHHMM format (e.g., 20220410T0130)"
                }
            },
            "required": ["symbol"]
        }
    }
]


def get_alpha_vantage_news(symbol: str, time_from: str = None, time_to: str = None) -> Dict[str, Any]:
    """Fetch news from Alpha Vantage API.
    
    Args:
        symbol: Stock ticker symbol
        time_from: Start of time range in YYYYMMDDTHHMM format (e.g., 20220410T0130)
        time_to: End of time range in YYYYMMDDTHHMM format (e.g., 20220410T0130)
    """
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
        
        # Add optional time range parameters
        if time_from:
            params["time_from"] = time_from
        if time_to:
            params["time_to"] = time_to
        
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
        
        # Process and simplify results
        news_items = [
            {
                "title": item.get("title"),
                "summary": item.get("summary"),
                "url": item.get("url"),
                "time_published": item.get("time_published"),
                "sentiment_score": item.get("overall_sentiment_score"),
                "sentiment_label": item.get("overall_sentiment_label")
            }
            for item in data.get("feed", [])[:5]  # Limit to 5 items
        ]
        
        return {"news": news_items}
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
        if request.name == "get_market_insights":
            symbol = request.arguments.get("symbol", "")
            time_from = request.arguments.get("time_from")
            time_to = request.arguments.get("time_to")
            result = get_alpha_vantage_news(symbol, time_from=time_from, time_to=time_to)
            
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

