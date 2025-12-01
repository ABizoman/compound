"""Pricing tools for getting stock price data.

These tools use the backtest context internally, so the agent
calls them without knowing about the date abstraction.
"""

from typing import Dict, Any, List, Optional
from .context import get_context


def get_current_price(symbol: str) -> str:
    """Get current price for a symbol.
    
    Args:
        symbol: Stock ticker symbol
        
    Returns:
        Formatted price string
    """
    ctx = get_context()
    
    if not ctx.is_backtest_mode:
        # Production mode - would call live API
        return f"Error: Live pricing not implemented"
    
    close = ctx.price_data.get_close_price(symbol, ctx.current_date)
    if close:
        return f"{symbol}: ${close:.2f}"
    return f"Error: No price data for {symbol} on {ctx.current_date}"


def get_prices_batch(symbols: List[str]) -> Dict[str, float]:
    """Get prices for multiple symbols.
    
    Args:
        symbols: List of stock ticker symbols
        
    Returns:
        Dict mapping symbol to price
    """
    ctx = get_context()
    
    if not ctx.is_backtest_mode:
        return {"error": "Live pricing not implemented"}
    
    results = {}
    for symbol in symbols:
        close = ctx.price_data.get_close_price(symbol, ctx.current_date)
        if close:
            results[symbol] = close
    return results


def get_daily_ohlc(symbol: str, days: int = 1) -> Optional[List[Dict[str, Any]]]:
    """Get OHLC data for a symbol.
    
    Args:
        symbol: Stock ticker symbol
        days: Number of days (currently only supports 1)
        
    Returns:
        List of OHLC data dicts or None if not found
    """
    ctx = get_context()
    
    if not ctx.is_backtest_mode:
        return None
    
    price_info = ctx.price_data.get_price(symbol, ctx.current_date)
    if price_info:
        return [{
            "date": ctx.current_date,
            "open": price_info.get("open"),
            "high": price_info.get("high"),
            "low": price_info.get("low"),
            "close": price_info.get("close"),
            "volume": price_info.get("volume")
        }]
    return None
