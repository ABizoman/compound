
import os
from typing import Union, Optional

# Try to import Alpaca SDK
try:
    from alpaca.trading.client import TradingClient
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

def get_trading_client() -> Union[TradingClient, str]:
    """Get Alpaca trading client instance."""
    if not ALPACA_AVAILABLE:
        return "Error: alpaca-py library not installed. Please pip install alpaca-py"
        
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    paper_mode = os.getenv("ALPACA_PAPER", "True").lower() == "true"
    
    if not api_key or not secret_key:
        return "Error: ALPACA_API_KEY and ALPACA_SECRET_KEY environment variables must be set"
        
    try:
        return TradingClient(api_key, secret_key, paper=paper_mode)
    except Exception as e:
        return f"Error initializing Alpaca client: {str(e)}"
