"""Trading tools for executing buy/sell orders and managing portfolio.

These tools use the backtest context internally, so the agent
calls them without knowing about the date abstraction.
"""

import os
from typing import Optional, Dict, Any, Union
from .context import get_context

try:
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
except ImportError:
    pass # Handled by client check

# Import from new lib
from src.lib.alpaca_client import get_trading_client

def buy_stock(symbol: str, quantity: float, price: float) -> str:
    """Buy stock.
    
    Args:
        symbol: Stock ticker symbol
        quantity: Number of shares to buy
        price: Price per share (used for logging/estimation in live mode)
        
    Returns:
        Success or error message
    """
    ctx = get_context()
    
    if not ctx.is_backtest_mode:
        client = get_trading_client()
        if isinstance(client, str):  # Error message
            return client
            
        try:
            # Prepare market order
            # Note: For simplicity we use Market orders. 
            # In a real system you might want Limit orders using 'price'
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=OrderSide.BUY,
                time_in_force=TimeInForce.DAY
            )
            
            # Submit order
            trade = client.submit_order(order_data)
            
            # Return confirmation
            # Note: The trade object from submit_order is an Order, actual fill price might vary
            status = "filled" if trade.filled_at else "submitted"
            return f"Order {status}: Buy {quantity} {symbol} (Order ID: {trade.id})"
            
        except Exception as e:
            return f"Error executing buy order: {str(e)}"
    
    # Backtest mode implementation
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
        price: Price per share (used for logging/estimation in live mode)
        
    Returns:
        Success or error message
    """
    ctx = get_context()
    
    if not ctx.is_backtest_mode:
        client = get_trading_client()
        if isinstance(client, str):  # Error message
            return client
            
        try:
            # Prepare market order
            order_data = MarketOrderRequest(
                symbol=symbol,
                qty=quantity,
                side=OrderSide.SELL,
                time_in_force=TimeInForce.DAY
            )
            
            # Submit order
            trade = client.submit_order(order_data)
            
            status = "filled" if trade.filled_at else "submitted"
            return f"Order {status}: Sell {quantity} {symbol} (Order ID: {trade.id})"
            
        except Exception as e:
            return f"Error executing sell order: {str(e)}"
    
    # Backtest mode implementation
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
        client = get_trading_client()
        if isinstance(client, str):  # Error message
            return client
            
        try:
            account = client.get_account()
            positions = client.get_all_positions()
            
            portfolio_text = f"Cash: ${float(account.cash):.2f} (Buying Power: ${float(account.buying_power):.2f})\n"
            
            if positions:
                pos_list = []
                for p in positions:
                    # p is a Position object
                    pos_list.append(f"{p.symbol}: {float(p.qty):.2f} shares @ avg ${float(p.avg_entry_price):.2f} (Current: ${float(p.current_price):.2f})")
                portfolio_text += "Positions:\n" + "\n".join(pos_list)
            else:
                portfolio_text += "Positions: None"
                
            return portfolio_text
            
        except Exception as e:
            return f"Error fetching portfolio: {str(e)}"
    
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
        client = get_trading_client()
        if isinstance(client, str):  # Error message
            return client
            
        try:
            # get_all_positions returns list, we want one. 
            # Client has get_open_position(symbol_or_asset_id)
            try:
                pos = client.get_open_position(symbol)
                return f"{symbol}: {float(pos.qty):.2f} shares @ avg ${float(pos.avg_entry_price):.2f} (Current: ${float(pos.current_price):.2f})"
            except Exception:
                # Alpaca raises error if position doesn't exist
                return f"No position in {symbol}"
                
        except Exception as e:
            return f"Error fetching position: {str(e)}"
    
    if symbol in ctx.portfolio.positions:
        pos = ctx.portfolio.positions[symbol]
        return f"{symbol}: {pos['shares']:.2f} shares @ avg ${pos['avg_cost']:.2f}"
    return f"No position in {symbol}"
