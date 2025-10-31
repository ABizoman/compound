import json
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from datetime import datetime


app = FastAPI(title="Trade MCP Server")


class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]


# Available trade tools
TRADE_TOOLS = [
    {
        "name": "buy_stock",
        "description": "Buy shares of a stock. Returns the trade execution details.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol to buy"
                },
                "quantity": {
                    "type": "number",
                    "description": "Number of shares to buy"
                },
                "price": {
                    "type": "number",
                    "description": "Price per share (optional, will use current market price if not provided)"
                }
            },
            "required": ["symbol", "quantity"]
        }
    },
    {
        "name": "sell_stock",
        "description": "Sell shares of a stock. Returns the trade execution details.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol to sell"
                },
                "quantity": {
                    "type": "number",
                    "description": "Number of shares to sell"
                },
                "price": {
                    "type": "number",
                    "description": "Price per share (optional, will use current market price if not provided)"
                }
            },
            "required": ["symbol", "quantity"]
        }
    },
    {
        "name": "get_portfolio",
        "description": "Get current portfolio positions and cash balance",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_position",
        "description": "Get current position for a specific stock symbol",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock symbol to get position for"
                }
            },
            "required": ["symbol"]
        }
    }
]


# Global state for portfolio (in production, this would be in a database)
_portfolio_state = {
    "cash": 0.0,
    "positions": {},  # {symbol: {"shares": float, "avg_cost": float}}
    "trades": []  # List of trade history
}


def load_portfolio_state(data_dir: str = "./data", initial_capital: float = 5000.0):
    """Load portfolio state from file."""
    global _portfolio_state
    state_file = Path(data_dir) / "portfolio_state.json"
    if state_file.exists():
        try:
            with open(state_file, 'r') as f:
                _portfolio_state = json.load(f)
        except Exception as e:
            print(f"Error loading portfolio state: {e}")
            # Initialize with default if load fails
            _portfolio_state = {
                "cash": initial_capital,
                "positions": {},
                "trades": []
            }
    else:
        # Initialize with default if file doesn't exist
        _portfolio_state = {
            "cash": initial_capital,
            "positions": {},
            "trades": []
        }


def save_portfolio_state(data_dir: str = "./data"):
    """Save portfolio state to file."""
    state_file = Path(data_dir) / "portfolio_state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with open(state_file, 'w') as f:
        json.dump(_portfolio_state, f, indent=2)


@app.on_event("startup")
async def startup_event():
    """Initialize portfolio state on startup."""
    # Try to get initial capital from environment or use default
    import os
    initial_capital = float(os.getenv("INITIAL_CAPITAL", "5000.0"))
    # Load portfolio state (will initialize if file doesn't exist)
    load_portfolio_state(initial_capital=initial_capital)
    # Save immediately to ensure file exists
    save_portfolio_state()


@app.post("/mcp/tools/list")
async def list_tools():
    """List available tools."""
    return {"tools": TRADE_TOOLS}


@app.post("/mcp/tools/call")
async def call_tool(request: ToolCallRequest):
    """Call a trade tool."""
    try:
        if request.name == "buy_stock":
            symbol = request.arguments.get("symbol", "").upper()
            quantity = float(request.arguments.get("quantity", 0))
            price = request.arguments.get("price")
            
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            
            # If price not provided, we'll need to get it from stock_local service
            # For now, we'll return an error if price is not provided
            if price is None:
                return {
                    "content": [
                        {"type": "text", "text": f"Error: Price required for buy order. Please provide current price."}
                    ]
                }
            
            price = float(price)
            total_cost = quantity * price
            
            if _portfolio_state["cash"] < total_cost:
                return {
                    "content": [
                        {"type": "text", "text": f"Error: Insufficient cash. Need ${total_cost:.2f}, have ${_portfolio_state['cash']:.2f}"}
                    ]
                }
            
            # Execute trade
            _portfolio_state["cash"] -= total_cost
            
            if symbol in _portfolio_state["positions"]:
                old_shares = _portfolio_state["positions"][symbol]["shares"]
                old_avg = _portfolio_state["positions"][symbol]["avg_cost"]
                new_shares = old_shares + quantity
                new_avg = ((old_shares * old_avg) + (quantity * price)) / new_shares
                _portfolio_state["positions"][symbol] = {
                    "shares": new_shares,
                    "avg_cost": new_avg
                }
            else:
                _portfolio_state["positions"][symbol] = {
                    "shares": quantity,
                    "avg_cost": price
                }
            
            trade_record = {
                "type": "buy",
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "total": total_cost,
                "timestamp": str(datetime.now())
            }
            _portfolio_state["trades"].append(trade_record)
            
            save_portfolio_state()
            
            return {
                "content": [
                    {"type": "text", "text": f"Bought {quantity} shares of {symbol} at ${price:.2f} each. Total cost: ${total_cost:.2f}. Remaining cash: ${_portfolio_state['cash']:.2f}"}
                ]
            }
        
        elif request.name == "sell_stock":
            symbol = request.arguments.get("symbol", "").upper()
            quantity = float(request.arguments.get("quantity", 0))
            price = request.arguments.get("price")
            
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
            
            if symbol not in _portfolio_state["positions"]:
                return {
                    "content": [
                        {"type": "text", "text": f"Error: No position in {symbol}"}
                    ]
                }
            
            current_shares = _portfolio_state["positions"][symbol]["shares"]
            
            if current_shares < quantity:
                return {
                    "content": [
                        {"type": "text", "text": f"Error: Insufficient shares. Have {current_shares}, trying to sell {quantity}"}
                    ]
                }
            
            # If price not provided, we'll need to get it from stock_local service
            if price is None:
                return {
                    "content": [
                        {"type": "text", "text": f"Error: Price required for sell order. Please provide current price."}
                    ]
                }
            
            price = float(price)
            total_revenue = quantity * price
            
            # Execute trade
            _portfolio_state["cash"] += total_revenue
            _portfolio_state["positions"][symbol]["shares"] -= quantity
            
            if _portfolio_state["positions"][symbol]["shares"] == 0:
                del _portfolio_state["positions"][symbol]
            
            trade_record = {
                "type": "sell",
                "symbol": symbol,
                "quantity": quantity,
                "price": price,
                "total": total_revenue,
                "timestamp": str(datetime.now())
            }
            _portfolio_state["trades"].append(trade_record)
            
            save_portfolio_state()
            
            return {
                "content": [
                    {"type": "text", "text": f"Sold {quantity} shares of {symbol} at ${price:.2f} each. Total revenue: ${total_revenue:.2f}. Cash: ${_portfolio_state['cash']:.2f}"}
                ]
            }
        
        elif request.name == "get_portfolio":
            positions_summary = []
            for symbol, pos in _portfolio_state["positions"].items():
                positions_summary.append(f"{symbol}: {pos['shares']} shares @ avg ${pos['avg_cost']:.2f}")
            
            portfolio_text = f"Cash: ${_portfolio_state['cash']:.2f}\n"
            portfolio_text += f"Positions:\n" + "\n".join(positions_summary) if positions_summary else "No positions"
            
            return {
                "content": [
                    {"type": "text", "text": portfolio_text}
                ]
            }
        
        elif request.name == "get_position":
            symbol = request.arguments.get("symbol", "").upper()
            
            if symbol in _portfolio_state["positions"]:
                pos = _portfolio_state["positions"][symbol]
                return {
                    "content": [
                        {"type": "text", "text": f"{symbol}: {pos['shares']} shares @ avg ${pos['avg_cost']:.2f}"}
                    ]
                }
            else:
                return {
                    "content": [
                        {"type": "text", "text": f"No position in {symbol}"}
                    ]
                }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {request.name}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

