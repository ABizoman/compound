"""
Backtest context module - provides date abstraction layer.

This module holds the current simulation state so that tool functions
can be called without explicitly passing backtest-specific parameters.
The AI agent remains completely unaware that it's operating on historical data.
"""

from typing import Optional, Any
from threading import Lock


class BacktestContext:
    """Singleton context holding current backtest state.
    
    This abstraction layer allows tools to be called with the same
    signatures they would have in production, while internally
    using historical data for the simulated current date.
    """
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._current_date: Optional[str] = None
        self._price_data: Optional[Any] = None
        self._portfolio: Optional[Any] = None
        self._is_backtest_mode: bool = False
        self._initialized = True
    
    def configure(self, current_date: str, price_data: Any, portfolio: Any):
        """Configure the context for a specific backtest day.
        
        Args:
            current_date: The simulated current date (YYYY-MM-DD)
            price_data: HistoricalPriceData instance
            portfolio: BacktestPortfolio instance
        """
        self._current_date = current_date
        self._price_data = price_data
        self._portfolio = portfolio
        self._is_backtest_mode = True
    
    def reset(self):
        """Reset context to production mode (no backtest)."""
        self._current_date = None
        self._price_data = None
        self._portfolio = None
        self._is_backtest_mode = False
    
    @property
    def current_date(self) -> Optional[str]:
        """Get the current simulated date."""
        return self._current_date
    
    @property
    def price_data(self) -> Optional[Any]:
        """Get the historical price data source."""
        return self._price_data
    
    @property
    def portfolio(self) -> Optional[Any]:
        """Get the portfolio instance."""
        return self._portfolio
    
    @property
    def is_backtest_mode(self) -> bool:
        """Check if running in backtest mode."""
        return self._is_backtest_mode


# Global context instance
_context = BacktestContext()


def get_context() -> BacktestContext:
    """Get the global backtest context."""
    return _context


def set_current_date(date: str):
    """Convenience function to update just the current date."""
    _context._current_date = date


def get_current_date() -> Optional[str]:
    """Get the current simulated date."""
    return _context.current_date
