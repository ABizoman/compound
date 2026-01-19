"""
Verification script for Alpaca Trading Integration.

Usage:
    python3 verify_alpaca_connection.py

Prerequisites:
    1. pip install alpaca-py
    2. Set environment variables:
       export ALPACA_API_KEY="your_key"
       export ALPACA_SECRET_KEY="your_secret"
       export ALPACA_PAPER="True" (optional, defaults to True)
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from src.tools import trading
    from src.tools.context import get_context
    from src.lib.alpaca_client import get_trading_client
except ImportError:
    print("Error: Could not import project modules. Make sure you run this from the project root.")
    sys.exit(1)

def main():
    print("=== Alpaca Connection Verification ===")
    
    # Check Environment Variables
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    
    print(f"Checking Environment Variables:")
    print(f"  ALPACA_API_KEY: {'✓ Set' if api_key else '✗ Missing'}")
    print(f"  ALPACA_SECRET_KEY: {'✓ Set' if secret_key else '✗ Missing'}")
    
    if not api_key or not secret_key:
        print("\nPlease export your Alpaca keys before running this script.")
        return

    # Check Context State
    ctx = get_context()
    print(f"\nContext State:")
    print(f"  Is Backtest Mode: {ctx.is_backtest_mode}")
    
    if ctx.is_backtest_mode:
        print("Warning: Context is in backtest mode. Verification will run against mock portfolio.")
    else:
        print("  Target: Live/Paper Alpaca Account")

    # Test Portfolio Connection
    print("\nTesting get_portfolio()...")
    portfolio_result = trading.get_portfolio()
    print(f"Result:\n{portfolio_result}")
    
    if "Error" in portfolio_result:
        print("\n✗ Connection Failed")
    else:
        print("\n✓ Connection Successful")

if __name__ == "__main__":
    main()
