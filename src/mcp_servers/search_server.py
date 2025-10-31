import os
import json
import requests
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(title="Search MCP Server")


class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]


# Available search tools
SEARCH_TOOLS = [
    {
        "name": "search_market_news",
        "description": "Search for market news and information about stocks. Uses Alpha Vantage and Jina AI to fetch relevant market information.",
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
        return {"error": "ALPHA_VANTAGE_API_KEY not set"}
    
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
        return response.json()
    except Exception as e:
        return {"error": str(e)}


def get_jina_search(query: str) -> Dict[str, Any]:
    """Search using Jina AI.
    
    Note: Jina AI primarily offers embedding and reranking APIs. For market search,
    you may want to use Jina's embedding API with a vector database, or use a
    Jina AI MCP server if available. This is a placeholder implementation.
    """
    api_key = os.getenv("JINA_API_KEY")
    if not api_key:
        return {"error": "JINA_API_KEY not set"}
    
    try:
        # Jina AI Embedding API - can be used for semantic search
        # This is a basic implementation - you may want to enhance it with
        # actual vector search or use a Jina AI MCP server for market info
        url = "https://api.jina.ai/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "input": query,
            "model": "jina-embeddings-v2-base-en"
        }
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        # Return a simplified result indicating embedding was generated
        # For actual search, you'd need to compare with stored embeddings
        return {
            "query": query,
            "embedding_generated": True,
            "note": "Jina AI embedding API used. For full search functionality, consider using Jina AI MCP server or vector database."
        }
    except requests.exceptions.HTTPError as e:
        # If API endpoint doesn't work, return helpful error
        return {"error": f"Jina AI API error: {e.response.status_code}. Check API endpoint or use Jina AI MCP server instead."}
    except Exception as e:
        return {"error": f"Jina AI search error: {str(e)}"}


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
            
            # Try Jina AI search
            jina_result = get_jina_search(query)
            if "error" not in jina_result:
                results.append(f"Jina AI Results: {json.dumps(jina_result, indent=2)}")
            
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

