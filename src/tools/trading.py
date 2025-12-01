"""Trading tools for executing buy/sell orders and managing portfolio.

These tools use the backtest context internally, so the agent
calls them without knowing about the date abstraction.
"""

from typing import Optional
from .context import get_context


def buy_stock(symbol: str, quantity: float, price: float) -> str:
    """Buy stock.
    
    Args:
        symbol: Stock ticker symbol
        quantity: Number of shares to buy
        price: Price per share
        
    Returns:
        Success or error message
    """
    ctx = get_context()
    
    if not ctx.is_backtest_mode:
        return "Error: Live trading not implemented"
    
    result = ctx.portfolio.buy(symbol, quantity, price, ctx.current_date)
    if "error" in result:
        return f"Error: {result['error']}"
    
    trade = result["trade"]
    return f"Bought {quantity} shares of {symbol} at ${price:.2f}. Total: ${trade['total']:.2f}. Cash: ${ctx.portfolio.cash:.2f}"


def sell_stock(symbol: str, quantity: float, price: float) -> str:
    """Sell stock.
    
    Args:
        symbol: Stock ticker symbol
        quantity: Number of shares to sell
        price: Price per share
        
    Returns:
        Success or error message
    """
    ctx = get_context()
    
    if not ctx.is_backtest_mode:
        return "Error: Live trading not implemented"
    
    result = ctx.portfolio.sell(symbol, quantity, price, ctx.current_date)
    if "error" in result:
        return f"Error: {result['error']}"
    
    trade = result["trade"]
    return f"Sold {quantity} shares of {symbol} at ${price:.2f}. Total: ${trade['total']:.2f}. Cash: ${ctx.portfolio.cash:.2f}"


def get_portfolio() -> str:
    """Get portfolio state.
    
    Returns:
        Portfolio state string
    """
    ctx = get_context()
    
    if not ctx.is_backtest_mode:
        return "Error: Portfolio not available"
    
    return ctx.portfolio.get_state_string()


def get_position(symbol: str) -> str:
    """Get position for a symbol.
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        Position info string
    """
    ctx = get_context()
    
    if not ctx.is_backtest_mode:
        return "Error: Portfolio not available"
    
    if symbol in ctx.portfolio.positions:
        pos = ctx.portfolio.positions[symbol]
        return f"{symbol}: {pos['shares']:.2f} shares @ avg ${pos['avg_cost']:.2f}"
    return f"No position in {symbol}"
