"""Trading bot tools package.

Provides tools for pricing, trading, news, and math calculations.
The context module provides date abstraction for backtesting.
"""

from . import pricing, news, trading, math_tools
from .context import get_context, set_current_date, get_current_date, BacktestContext

__all__ = [
    'pricing',
    'news', 
    'trading',
    'math_tools',
    'get_context',
    'set_current_date',
    'get_current_date',
    'BacktestContext'
]
