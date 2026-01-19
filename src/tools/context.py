"""
Backtest Context Management Module.

This module implements a singleton context manager that maintains the state of the
backtesting simulation. It serves as an abstraction layer, allowing trading tools
to operate seamlessly in both production and backtesting environments without
requiring modification. By injecting historical state (dates, prices, portfolio)
globally, the AI agent interacts with the system as if it were live, unaware
that it is processing historical data.
"""

from typing import Optional, Any


class BacktestContext:
    """
    A Singleton class that encapsulates the current backtesting state.

    This class ensures that only one instance of the simulation context exists
    throughout the application lifecycle. It manages the simulated current date,
    historical price data access, and the portfolio state, enabling tools to
    retrieve context-aware data without explicit parameter passing.
    """
    
    _instance = None
    
    def __new__(cls):
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
        """
        Initializes the backtest context with simulation parameters.

        This method sets up the environment for a specific point in the simulation,
        enabling backtest mode.

        Args:
            current_date (str): The date currently being simulated in 'YYYY-MM-DD' format.
            price_data (Any): The source of historical price data for the simulation.
            portfolio (Any): The portfolio instance tracking positions and value during the backtest.
        """
        self._current_date = current_date
        self._price_data = price_data
        self._portfolio = portfolio
        self._is_backtest_mode = True
    
    def reset(self):
        """
        Clears the backtest context and reverts to production mode.

        This removes all simulation state (date, price data, portfolio) and sets
        the backtest mode flag to False.
        """
        self._current_date = None
        self._price_data = None
        self._portfolio = None
        self._is_backtest_mode = False
    
    @property
    def current_date(self) -> Optional[str]:
        """Returns the current date being simulated in the backtest."""
        return self._current_date
    
    @property
    def price_data(self) -> Optional[Any]:
        """Returns the historical price data provider associated with the current backtest."""
        return self._price_data
    
    @property
    def portfolio(self) -> Optional[Any]:
        """Returns the current state of the portfolio in the backtest."""
        return self._portfolio
    
    @property
    def is_backtest_mode(self) -> bool:
        """Returns True if the system is currently running in a backtest simulation."""
        return self._is_backtest_mode


# Global context instance
_context = BacktestContext()


def get_context() -> BacktestContext:
    """Retrieves the global singleton instance of the BacktestContext."""
    return _context


def set_current_date(date: str):
    """
    Updates the simulated current date in the global context.

    Args:
        date (str): The new date to set as the current simulation date.
    """
    _context._current_date = date


def get_current_date() -> Optional[str]:
    """Retrieves the currently simulated date from the global context."""
    return _context.current_date
