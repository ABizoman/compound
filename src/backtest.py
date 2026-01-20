"""
Backtesting module for the trading bot.

This module runs the trading agent on historical data, executing trades
every Monday for the past 12 months using price data from CSV file.
"""

import json
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import subprocess
import time
import signal
import atexit

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

csv_path = "./data/backtest_results/backtest_20251201_184001.json"
output_dir = "./data/backtest_results"

from src.config import Config

from src.tools import pricing, news, trading, math_tools
from src.tools.context import get_context


class HistoricalPriceData:
    """Loads and provides access to historical price data from CSV."""
    
    def __init__(self, csv_path: Path):
        self.csv_path = csv_path
        self.data = self._load_csv()
        self.available_dates = sorted(self.data.keys())
        print(f"✓ Loaded historical data for {len(self.available_dates)} trading days")
        print(f"  Date range: {self.available_dates[0]} to {self.available_dates[-1]}")
    
    def _load_csv(self) -> Dict[str, Dict[str, Dict[str, float]]]:
        """Load and parse the CSV file into a structured format.
        
        Returns:
            Dict mapping date -> ticker -> {open, high, low, close, volume}
        """
        # Read the CSV - it has a multi-level header structure
        # Row 0: Ticker names repeated for each series
        # Row 1: Series names (Open, High, Low, Close, Volume, Dividends)
        # Row 2: Empty (Date label)
        # Row 3+: Data
        
        df = pd.read_csv(self.csv_path, header=[0, 1])
        
        # The first column contains dates, get it from the index
        # Drop the first level which is 'Ticker' and 'Series'
        df_reset = pd.read_csv(self.csv_path, skiprows=2)
        
        # First column is Date
        dates = df_reset.iloc[:, 0].tolist()
        
        # Read header row to get ticker names
        with open(self.csv_path, 'r') as f:
            ticker_line = f.readline().strip().split(',')
            series_line = f.readline().strip().split(',')
        
        # Build ticker-series mapping (skip first column which is date/ticker label)
        tickers = ticker_line[1:]
        series = series_line[1:]
        
        data = {}
        
        for row_idx, date_str in enumerate(dates):
            if pd.isna(date_str) or date_str == '':
                continue
                
            # Parse date
            try:
                date = datetime.strptime(str(date_str).strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
            except ValueError:
                continue
            
            data[date] = {}
            
            # Get values for this row (skip first column which is date)
            values = df_reset.iloc[row_idx, 1:].tolist()
            
            # Map values to tickers and series
            for col_idx, value in enumerate(values):
                if col_idx >= len(tickers):
                    break
                    
                ticker = tickers[col_idx]
                series_name = series[col_idx].lower()
                
                if ticker not in data[date]:
                    data[date][ticker] = {}
                
                try:
                    data[date][ticker][series_name] = float(value) if not pd.isna(value) else None
                except (ValueError, TypeError):
                    data[date][ticker][series_name] = None
        
        return data
    
    def get_price(self, symbol: str, date: str) -> Optional[Dict[str, float]]:
        """Get price data for a symbol on a specific date."""
        if date not in self.data:
            return None, "Date not found"
        if symbol not in self.data[date]:
            return None, "Symbol not found"
        return self.data[date][symbol]
    
    def get_close_price(self, symbol: str, date: str) -> Optional[float]:
        """Get closing price for a symbol on a specific date."""
        price_data = self.get_price(symbol, date)
        if price_data and 'close' in price_data:
            return price_data['close']
        return None
    
    def get_all_prices(self, date: str) -> Dict[str, Dict[str, float]]:
        """Get all prices for a specific date."""
        return self.data.get(date, {})
    
    def get_mondays(self) -> List[str]:
        """Get all Mondays from the available dates."""
        mondays = []
        for date_str in self.available_dates:
            date = datetime.strptime(date_str, "%Y-%m-%d")
            if date.weekday() == 0:  # Monday is 0
                mondays.append(date_str)
        return mondays
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available ticker symbols."""
        if self.available_dates:
            return list(self.data[self.available_dates[0]].keys())
        return []


class BacktestPortfolio:
    """Manages portfolio state during backtesting."""
    
    def __init__(self, initial_capital: float = 5000.0):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Dict[str, float]] = {}  # symbol -> {shares, avg_cost}
        self.trades: List[Dict[str, Any]] = []
        self.equity_history: List[Dict[str, Any]] = []
    
    def reset(self):
        """Reset portfolio to initial state."""
        self.cash = self.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_history = []
    
    def buy(self, symbol: str, quantity: float, price: float, date: str) -> Dict[str, Any]:
        """Execute a buy order."""
        total_cost = quantity * price
        
        if self.cash < total_cost:
            return {"error": f"Insufficient cash. Need ${total_cost:.2f}, have ${self.cash:.2f}"}
        
        self.cash -= total_cost
        
        if symbol in self.positions:
            old_shares = self.positions[symbol]["shares"]
            old_avg = self.positions[symbol]["avg_cost"]
            new_shares = old_shares + quantity
            new_avg = ((old_shares * old_avg) + (quantity * price)) / new_shares
            self.positions[symbol] = {"shares": new_shares, "avg_cost": new_avg}
        else:
            self.positions[symbol] = {"shares": quantity, "avg_cost": price}
        
        trade = {
            "type": "buy",
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "total": total_cost,
            "date": date
        }
        self.trades.append(trade)
        
        return {"success": True, "trade": trade}
    
    def sell(self, symbol: str, quantity: float, price: float, date: str) -> Dict[str, Any]:
        """Execute a sell order."""
        if symbol not in self.positions:
            return {"error": f"No position in {symbol}"}
        
        current_shares = self.positions[symbol]["shares"]
        if current_shares < quantity:
            return {"error": f"Insufficient shares. Have {current_shares}, trying to sell {quantity}"}
        
        total_revenue = quantity * price
        self.cash += total_revenue
        self.positions[symbol]["shares"] -= quantity
        
        if self.positions[symbol]["shares"] <= 0:
            del self.positions[symbol]
        
        trade = {
            "type": "sell",
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "total": total_revenue,
            "date": date
        }
        self.trades.append(trade)
        
        return {"success": True, "trade": trade}
    
    def get_total_equity(self, prices: Dict[str, float]) -> float:
        """Calculate total portfolio equity using current prices."""
        equity = self.cash
        for symbol, position in self.positions.items():
            if symbol in prices:
                equity += position["shares"] * prices[symbol]
        return equity
    
    def record_equity(self, date: str, prices: Dict[str, float]):
        """Record equity snapshot for this date."""
        import copy
        equity = self.get_total_equity(prices)
        self.equity_history.append({
            "date": date,
            "equity": equity,
            "cash": self.cash,
            "positions": copy.deepcopy(self.positions)
        })
    
    def get_state_string(self) -> str:
        """Get portfolio state as a string (for agent prompt)."""
        positions_summary = []
        for symbol, pos in self.positions.items():
            positions_summary.append(f"{symbol}: {pos['shares']:.2f} shares @ avg ${pos['avg_cost']:.2f}")
        
        portfolio_text = f"Cash: ${self.cash:.2f}\n"
        if positions_summary:
            portfolio_text += "Positions:\n" + "\n".join(positions_summary)
        else:
            portfolio_text += "Positions: None"
        
        return portfolio_text



class BacktestAgent:
    """Trading agent modified for backtesting with historical data."""
    
    STOP_SIGNAL = "<FINISH_SIGNAL>"
    
    def __init__(self, config: Config, price_data: HistoricalPriceData, portfolio: BacktestPortfolio):
        self.config = config
        self.llm_config = config.llm_config
        self.trading_config = config.trading_config
        self.price_data = price_data
        self.portfolio = portfolio
        self.output_dir = config.trading_config.get("output_dir", Path("./data/backtest_results"))
        self.strategy_context_path = self.output_dir / "strategy_context.txt"
        self.context = get_context()  # Get global context
        
        # Initialize OpenAI client
        from openai import OpenAI
        api_key = config.openrouter_api_key
        api_base = self.llm_config.get("api_base", "https://openrouter.ai/api/v1")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base,
            default_headers={
                "HTTP-Referer": "https://github.com/compound",
                "X-Title": "Compound Backtest"
            }
        )
        
        # Define available tools (simulating MCP tools)
        self.tools = self._get_tools()
    
    def _get_tools(self) -> List[Dict[str, Any]]:
        """Define available tools for the agent."""
        tools = []
        
        # see tool definition best practices here: https://openrouter.ai/docs/guides/features/tool-calling#function-definition-guidelines
        
        # Math tools
        tools.extend([
            {
                "type": "function",
                "function": {
                    "name": "calculate",
                    "description": "Perform basic mathematical calculations (addition, subtraction, multiplication, division, exponentiation, etc.). Supports expressions like '2+2', '10*5', 'sqrt(16)', 'pow(2,3)'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expression": {
                                "type": "string",
                                "description": "Mathematical expression to evaluate"
                            }
                        },
                        "required": ["expression"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_percentage",
                    "description": "Calculate percentage change between two values",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "old_value": {"type": "number", "description": "Original value"},
                            "new_value": {"type": "number", "description": "New value"}
                        },
                        "required": ["old_value", "new_value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "batch_calculate",
                    "description": "Calculate multiple mathematical expressions in a single call. More efficient than calling calculate multiple times.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "expressions": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of mathematical expressions to evaluate (e.g., ['15 * 88.18', '3 * 234.74', '7 * 196.23'])"
                            }
                        },
                        "required": ["expressions"]
                    }
                }
            }
        ])
        
        # News/Search tools
        tools.append({
            "type": "function",
                "function": {
                    "name": "get_market_insights",
                    "description": "Get market news and insights.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Single stock ticker symbol to get news for (e.g. 'AAPL'). Leave empty for general market news. Do NOT pass a list."
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of news items to return (default 5)",
                                "default": 5
                            }
                        }
                    }
                }
        })
        
        # Add Stock tools
        tools.append({
            "type": "function",
            "function": {
                "name": "get_current_price",
                "description": "Get the current price of a stock symbol",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "The stock ticker symbol (e.g., AAPL, GOOGL)"
                        }
                    },
                    "required": ["symbol"]
                }
            }
        })
        
        tools.append({
            "type": "function",
            "function": {
                "name": "get_prices_batch",
                "description": "Get current prices for multiple stock symbols at once",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbols": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of stock ticker symbols"
                        }
                    },
                    "required": ["symbols"]
                }
            }
        })
        
        tools.append({
            "type": "function",
            "function": {
                "name": "get_daily_ohlc",
                "description": "Get daily OHLC (Open, High, Low, Close) data for a stock",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "The stock ticker symbol"
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days of data to retrieve",
                            "default": 1
                        }
                    },
                    "required": ["symbol"]
                }
            }
        })
        
        # Add Trade tools - price is REQUIRED
        tools.append({
            "type": "function",
            "function": {
                "name": "buy_stock",
                "description": "Buy shares of a stock. You MUST provide the current price - get it first using get_current_price or get_prices_batch.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "The stock ticker symbol to buy"
                        },
                        "quantity": {
                            "type": "number",
                            "description": "Number of shares to buy"
                        },
                        "price": {
                            "type": "number",
                            "description": "The current price per share (REQUIRED - get this from get_current_price first)"
                        }
                    },
                    "required": ["symbol", "quantity", "price"]
                }
            }
        })
        
        tools.append({
            "type": "function",
            "function": {
                "name": "sell_stock",
                "description": "Sell shares of a stock. You MUST provide the current price - get it first using get_current_price or get_prices_batch.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "The stock ticker symbol to sell"
                        },
                        "quantity": {
                            "type": "number",
                            "description": "Number of shares to sell"
                        },
                        "price": {
                            "type": "number",
                            "description": "The current price per share (REQUIRED - get this from get_current_price first)"
                        }
                    },
                    "required": ["symbol", "quantity", "price"]
                }
            }
        })
        
        tools.append({
            "type": "function",
            "function": {
                "name": "get_portfolio",
                "description": "Get the current portfolio state including cash and all positions",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        })
        
        tools.append({
            "type": "function",
            "function": {
                "name": "get_position",
                "description": "Get the current position for a specific stock symbol",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "symbol": {
                            "type": "string",
                            "description": "The stock ticker symbol"
                        }
                    },
                    "required": ["symbol"]
                }
            }
        })
        
        tools.append({
            "type": "function",
            "function": {
                "name": "FINISH_SIGNAL",
                "description": "Call this tool when you have completed all analysis and trading for today. Only call after: 1) Getting market insights, 2) Checking prices, 3) Analyzing portfolio, 4) Making trading decisions (buy/sell/hold), 5) Updating the strategy context if needed.",
                "parameters": {
                    "type": "object",
                    "properties": {}
                }
            }
        })

        tools.append({
            "type": "function",
            "function": {
                "name": "update_strategy_context",
                "description": "Update the persistent long-term strategy note. This note will be read at the start of the next trading day. Use this to record your long-term plan, observations about market regime, or specific setups you are watching. This REPLACES the previous content, so be sure to include all important context you want to keep.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "content": {
                            "type": "string",
                            "description": "The new FULL text of the strategy context/note."
                        }
                    },
                    "required": ["content"]
                }
            }
        })
            
        return tools
    
    def _call_tool(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call - tools use context internally for date/portfolio."""
        try:
            # Pricing tools - no date/context params needed, tools use global context
            if tool_name == "get_current_price":
                result = pricing.get_current_price(args.get("symbol", "").upper())
                return {"content": [{"type": "text", "text": result}]}
            
            elif tool_name == "get_prices_batch":
                symbols = [s.upper() for s in args.get("symbols", [])]
                result = pricing.get_prices_batch(symbols)
                return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
            
            elif tool_name == "get_daily_ohlc":
                result = pricing.get_daily_ohlc(args.get("symbol", "").upper(), args.get("days", 1))
                if result:
                    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
                return {"content": [{"type": "text", "text": f"Error: No OHLC data for {args.get('symbol')}"}]}
            
            # Trading tools - no portfolio/date params needed
            elif tool_name == "buy_stock":
                result = trading.buy_stock(
                    args.get("symbol", "").upper(),
                    float(args.get("quantity", 0)),
                    float(args.get("price")) if args.get("price") else None
                )
                return {"content": [{"type": "text", "text": result}]}
            
            elif tool_name == "sell_stock":
                result = trading.sell_stock(
                    args.get("symbol", "").upper(),
                    float(args.get("quantity", 0)),
                    float(args.get("price")) if args.get("price") else None
                )
                return {"content": [{"type": "text", "text": result}]}
            
            elif tool_name == "get_portfolio":
                result = trading.get_portfolio()
                return {"content": [{"type": "text", "text": result}]}
            
            elif tool_name == "get_position":
                result = trading.get_position(args.get("symbol", "").upper())
                return {"content": [{"type": "text", "text": result}]}
            
            # Math tools 
            elif tool_name == "calculate":
                result = math_tools.calculate(args.get("expression", ""))
                return {"content": [{"type": "text", "text": result}]}
            
            elif tool_name == "calculate_percentage":
                result = math_tools.calculate_percentage(
                    float(args.get("old_value", 0)),
                    float(args.get("new_value", 0))
                )
                return {"content": [{"type": "text", "text": result}]}
            
            elif tool_name == "batch_calculate":
                result = math_tools.batch_calculate(args.get("expressions", []))
                return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
            
            # News tools - no date param needed, uses context
            elif tool_name == "get_market_insights":
                symbol = args.get("symbol", "")
                limit = args.get("limit", 5)
                result = news.get_market_insights(ticker=symbol, limit=limit)
                
                if "error" in result:
                    return {"content": [{"type": "text", "text": f"Error: {result['error']}"}]}
                
                return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
            
            # Handle FINISH_SIGNAL as a tool call (agent sometimes calls it as a tool)
            elif tool_name == "FINISH_SIGNAL" or tool_name == "finish_signal":
                return {"content": [{"type": "text", "text": "<FINISH_SIGNAL>"}], "is_finish": True}
            
            # Strategy Context tool
            elif tool_name == "update_strategy_context":
                content = args.get("content", "")
                try:
                    with open(self.strategy_context_path, 'w') as f:
                        f.write(content)
                    return {"content": [{"type": "text", "text": "Strategy context updated successfully."}]}
                except Exception as e:
                    return {"content": [{"type": "text", "text": f"Error updating strategy context: {str(e)}"}]}

            else:
                return {"content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}]}
        
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error calling {tool_name}: {str(e)}"}]}
    
    def get_system_prompt(self, today_date: str, max_steps: int, strategy_context: str = "") -> str:
        """Generate system prompt with step count awareness."""
        return f"""You are a stock fundamental analysis trading assistant.

Your goals are:
- Think and reason by calling available tools.
- You need to think about the prices of various stocks and their returns.
- Your long-term goal is to maximize returns through this portfolio.
- Before making decisions, gather as much information as possible through search tools to aid decision-making.

LONG-TERM STRATEGY CONTEXT:
The following is your persistent note from previous trading days. Use it to maintain continuity in your strategy.
'''
{strategy_context}
'''

STEP BUDGET: You have a MAXIMUM of {max_steps} steps to complete your analysis and trading today.
You MUST be efficient and prioritize the most important actions.

CRITICAL TRADING RULES:
- When buying or selling stocks, you MUST provide the price parameter as a NUMBER (not a string)
- ALWAYS get prices FIRST using get_prices_batch or get_current_price BEFORE executing trades
- Example workflow:
  1. Call get_prices_batch with symbols ["AAPL", "GOOGL", ...]
  2. Note the prices returned (e.g., AAPL: 150.25)
  3. Call buy_stock with symbol="AAPL", quantity=10, price=150.25 (use the actual number)

CRITICAL: You MUST complete ALL of the following steps before finishing. DO NOT skip any steps:

STEP 1: Gather market insights using get_market_insights. You can specify a SINGLE ticker symbol to get news for that specific stock, or leave it empty for general market news. If you need news for multiple stocks, you must call this tool multiple times (once per ticker) or just get general news.
STEP 2: Analyze the PROVIDED prices for all symbols (prices are already given in the prompt)
STEP 3: Analyze your current portfolio using get_portfolio
STEP 4: Calculate valuations and potential returns using batch_calculate to save steps (e.g., batch_calculate with all position values at once)
STEP 5: Make a trading decision:
   - If you have cash and see opportunities: BUY stocks (include price parameter!)
   - If prices have moved: consider SELLING or REBALANCING (include price parameter!)
   - If no clear opportunity: explicitly state you're HOLDING
STEP 6: Execute any trades using buy_stock or sell_stock WITH THE PRICE PARAMETER
STEP 7: Update your long-term strategy note using update_strategy_context. This is CRITICAL for maintaining your strategy across days.
STEP 8: ONLY after completing steps 1-7, output {self.STOP_SIGNAL}

IMPORTANT RULES:
- Even if market news is empty, you MUST still analyze trading opportunities with the provided prices
- You must make a conscious trading decision (buy/sell/hold) based on price analysis
- You must make a conscious trading decision (buy/sell/hold) based on price analysis
- DO NOT output {self.STOP_SIGNAL} until you have checked prices and made trading decisions
- Simply gathering news is NOT enough - you must analyze prices and execute trades or explicitly decide to hold
- Be EFFICIENT with your steps - you only have {max_steps} total!
- Use batch_calculate for multiple calculations instead of calling calculate multiple times
- Use get_market_insights with specific ticker symbols when you want targeted news (e.g., symbol="AAPL")
- BUY/SELL ORDERS REQUIRE price AS A NUMBER - always include it!

Thinking standards:
- Show your reasoning clearly:
  - "Gathered market insights for all symbols"
  - "Checking current prices for portfolio analysis"
  - "Current portfolio has X positions worth $Y"
  - "Based on prices, I will buy/sell/hold because..."
  - "Executing trade: buying X shares of Y at price Z"

Notes:
- You don't need user permission, execute trades directly
- Always check current prices before buying or selling
- Use the math tools (calculate, calculate_percentage) to analyze returns
- If you have $5000 cash and no positions, you should consider buying undervalued stocks

Current information:

Today's date: {today_date}

Current portfolio state:
{self.portfolio.get_state_string()}

Available symbols to trade: {', '.join(self.trading_config.get('symbols', []))}

Remember: You MUST check prices and make trading decisions. Output {self.STOP_SIGNAL} ONLY after completing all analysis and trades.
REMEMBER: buy_stock and sell_stock REQUIRE the price parameter as a number!
"""
    
    def run_day(self, date: str) -> Dict[str, Any]:
        """Run the agent for one trading day with step count awareness."""
        print(f"\n{'='*60}")
        print(f"Backtest: Running agent for {date}")
        print(f"{'='*60}")
        
        # thos whole section follows the openrouter docs found here: https://openrouter.ai/docs/guides/features/tool-calling#a-simple-agentic-loop
        
        # Configure the global context for this day
        self.context.configure(date, self.price_data, self.portfolio)
        
        # Initialize conversation
        max_steps = self.trading_config.get("max_steps_per_day")
        # need proper error catching for this
        
        # Read strategy context
        strategy_context = "No prior strategy context. This is the first day."
        if self.strategy_context_path.exists():
            with open(self.strategy_context_path, 'r') as f:
                strategy_context = f.read()
        
        # Pre-fetch prices for all symbols
        symbols = self.trading_config.get("symbols", [])
        pricing_results = pricing.get_prices_batch(symbols)
        
        prices_str = "Current Stock Prices:\n"
        for symbol, price in pricing_results.items():
            prices_str += f"- {symbol}: ${price:.2f}\n"
        
        messages = [
            {"role": "system", "content": self.get_system_prompt(date, max_steps, strategy_context)},
            {"role": "user", "content": f"Today is {date}. You have {max_steps} steps maximum.\n\n{prices_str}\n\nAnalyze these prices and make trading decisions efficiently."}
        ]
        step_count = 0
        logs = []
        api_calls = 0
        
        while step_count < max_steps:
            api_calls += 1
            
            try:
                response = self.client.chat.completions.create(
                    model=self.llm_config.get("model"),
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",
                    temperature=0.7
                )
                
                message = response.choices[0].message
                messages.append(message)
                
                has_reasoning = message.content and message.content.strip()
                has_tool_calls = message.tool_calls
                
                if has_reasoning or has_tool_calls:
                    step_count += 1
                    print(f"  Step {step_count}/{max_steps}")
                else:
                    continue
                
                if message.content and self.STOP_SIGNAL in message.content:
                    print(f"  ✓ Agent completed (API calls: {api_calls}, counted steps: {step_count})")
                    logs.append({"step": step_count, "type": "stop", "content": message.content})
                    break
                
                if message.tool_calls:
                    if message.content:
                        print(f"\n  [AGENT REASONING]\n  {message.content}\n")
                        logs.append({
                            "step": step_count, 
                            "type": "reasoning", 
                            "content": message.content
                        })
                    
                    should_finish = False
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        try:
                            tool_args = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
                        except json.JSONDecodeError:
                            tool_args = {}
                        
                        print(f"    [TOOL CALL] {tool_name}({tool_args})")
                        
                        # Call tool - simplified, no context params needed
                        tool_result = self._call_tool(tool_name, tool_args)
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(tool_result.get("content", [])),
                            "name": tool_name
                        })
                        
                        logs.append({
                            "step": step_count,
                            "type": "tool_call",
                            "tool": tool_name,
                            "arguments": tool_args,
                            "result": tool_result
                        })
                        
                        result_text = tool_result.get("content", [{}])[0].get("text", "")
                        print(f"      → {result_text[:80]}...")
                        
                        # Check if this was a finish signal
                        if tool_result.get("is_finish"):
                            should_finish = True
                    
                    if should_finish:
                        print(f"  ✓ Agent completed via FINISH_SIGNAL tool (API calls: {api_calls}, counted steps: {step_count})")
                        logs.append({"step": step_count, "type": "stop", "content": "FINISH_SIGNAL tool called"})
                        break
                else:
                    if message.content:
                        print(f"\n  [AGENT REASONING]\n  {message.content}\n")
                        logs.append({"step": step_count, "type": "message", "content": message.content})
                
            except Exception as e:
                print(f"  ✗ Error: {e}")
                logs.append({"step": step_count, "type": "error", "error": str(e)})
                break
        
        # Record equity at end of day
        prices = {}
        for symbol in self.trading_config.get("symbols", []):
            close = self.price_data.get_close_price(symbol, date)
            if close:
                prices[symbol] = close
        
        self.portfolio.record_equity(date, prices)
        
        day_result = {
            "date": date,
            "steps": step_count,
            "api_calls": api_calls,
            "strategy_context": strategy_context,
            "logs": logs,
            "portfolio": self.portfolio.get_state_string(),
            "equity": self.portfolio.get_total_equity(prices)
        }
        
        return day_result


def run_backtest(csv_path: Path = None, output_dir: Path = None):
    """Run the full backtest simulation."""
    print("\n" + "="*70)
    print("TRADING BOT BACKTEST")
    print("="*70)
    
    # Load config
    config = Config()
    
    # Set paths
    if csv_path is None:
        csv_path = project_root / "data" / "10ticker14monthsDaily.csv"
    if output_dir is None:
        output_dir = project_root / "data" / "backtest_results"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load historical data
    print(f"\nLoading historical data from {csv_path}...")
    price_data = HistoricalPriceData(csv_path)
    
    # Initialize strategy context file
    strategy_context_path = output_dir / "strategy_context.txt"
    with open(strategy_context_path, 'w') as f:
        f.write("No prior strategy context. This is the first day.")
    print(f"✓ Initialized strategy context at {strategy_context_path}")
    
    # Get all Mondays
    mondays = price_data.get_mondays()
    print(f"\n✓ Found {len(mondays)} Mondays to backtest")
    print(f"  First: {mondays[0]}")
    print(f"  Last: {mondays[-1]}")
    
    # Initialize portfolio
    initial_capital = config.trading_config.get("initial_capital")
    portfolio = BacktestPortfolio(initial_capital)
    
    # Create backtest agent
    # Update config with output_dir for agent to use
    config.trading_config["output_dir"] = output_dir
    agent = BacktestAgent(config, price_data, portfolio)
    
    # Run backtest for each Monday
    results = []
    
    # Create daily logs directory
    daily_logs_dir = output_dir / "daily_logs"
    daily_logs_dir.mkdir(parents=True, exist_ok=True)
    
    for i, monday in enumerate(mondays):
        print(f"\n[{i+1}/{len(mondays)}] Processing {monday}...")
        
        try:
            result = agent.run_day(monday)
            results.append(result)
            
            print(f"  Equity: ${result['equity']:.2f}")
            
            # Save individual day log immediately
            day_log_file = daily_logs_dir / f"day_{monday}.json"
            with open(day_log_file, 'w') as f:
                json.dump(result, f, indent=2)
            
            # Save cumulative results incrementally after each day
            results_file = output_dir / f"backtest_current.json"
            with open(results_file, 'w') as f:
                json.dump({
                    "start_date": mondays[0] if mondays else None,
                    "end_date": monday,  # Current progress
                    "days_completed": i + 1,
                    "days_total": len(mondays),
                    "initial_capital": initial_capital,
                    "final_equity": portfolio.equity_history[-1]["equity"] if portfolio.equity_history else initial_capital,
                    "total_trades": len(portfolio.trades),
                    "equity_history": portfolio.equity_history,
                    "trades": portfolio.trades,
                    "daily_results": results
                }, f, indent=2)
                
        except Exception as e:
            print(f"  ✗ Error on {monday}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Save results
    results_file = output_dir / f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump({
            "start_date": mondays[0] if mondays else None,
            "end_date": mondays[-1] if mondays else None,
            "initial_capital": initial_capital,
            "final_equity": portfolio.equity_history[-1]["equity"] if portfolio.equity_history else initial_capital,
            "total_trades": len(portfolio.trades),
            "equity_history": portfolio.equity_history,
            "trades": portfolio.trades,
            "daily_results": results
        }, f, indent=2)
    
    print(f"\n✓ Results saved to {results_file}")
    
    # Print summary
    print("\n" + "="*70)
    print("BACKTEST SUMMARY")
    print("="*70)
    
    if portfolio.equity_history:
        final_equity = portfolio.equity_history[-1]["equity"]
        total_return = ((final_equity - initial_capital) / initial_capital) * 100
        
        print(f"Initial Capital:  ${initial_capital:,.2f}")
        print(f"Final Equity:     ${final_equity:,.2f}")
        print(f"Total Return:     {total_return:+.2f}%")
        print(f"Total Trades:     {len(portfolio.trades)}")
        print(f"Trading Days:     {len(mondays)}")
    
    # Print equity curve
    print("\nEquity Curve (sampled):")
    sample_size = min(10, len(portfolio.equity_history))
    step = max(1, len(portfolio.equity_history) // sample_size)
    
    for i in range(0, len(portfolio.equity_history), step):
        entry = portfolio.equity_history[i]
        print(f"  {entry['date']}: ${entry['equity']:,.2f}")
    
    if portfolio.equity_history:
        print(f"  {portfolio.equity_history[-1]['date']}: ${portfolio.equity_history[-1]['equity']:,.2f} (final)")
    
    return results


if __name__ == "__main__":
    run_backtest()

