import os
import json
import requests
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv
# Import Finnhub client
from src.mcp_servers.finnhub_client import get_finnhub_news

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
        "description": "Get market news and insights for a specific stock from Finnhub. Returns a concise list of recent news items.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol to filter news (optional)"
                },
                "category": {
                    "type": "string",
                    "enum": ["general", "forex", "crypto", "merger"],
                    "description": "News category"
                },
                "min_id": {
                    "type": "integer",
                    "description": "Return only news items with ID greater than this value"
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
            category = request.arguments.get("category", "general")
            min_id = request.arguments.get("min_id", 0)
            result = get_finnhub_news(symbol=symbol, category=category, min_id=min_id)
            
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

