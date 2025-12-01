import os
import json
import requests
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv
# Import new News client
from src.mcp_servers.news_client import get_market_news

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
        "description": "Get market news and insights for a specific stock. Returns a list of recent news items with sentiment analysis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol to filter news (optional)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of news items to return (default 5)",
                    "default": 5
                }
            },
            "required": []
        }
    }
]



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
            limit = request.arguments.get("limit", 5)
            
            # Note: For the live server, we don't filter by date (get latest).
            # Backtest will use the client directly with date parameters.
            result = get_market_news(ticker=symbol, limit=limit)
            
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

