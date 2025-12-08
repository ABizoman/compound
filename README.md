# Compound: An Autonomous Investing Framework

Compound automates the entire process of investing in the stock market from research to trade execution through the use of LLM models and MCP tools. The agent sees & executes tools for prices, news, math, and trading, allowing it to conduct it's own research, produce a reasoning, and act on it's decisions all without the need for human intervention.


## Project Layout
- `config.yaml` — model/provider settings, trading symbols, capital, and step budget.
- `src/backtest.py` — main backtest runner, agent loop, portfolio tracking, and result writers.
- `src/config.py` — YAML + `.env` loader for runtime configuration and API keys.
- `src/tools/` — tool implementations the agent can call (`pricing`, `trading`, `news`, `math_tools`) plus the `context` abstraction that routes requests to historical data during simulation.
- `data/10ticker12monthDaily.csv` — sample price history used for default runs.
- `data/backtest_results/` — JSON artifacts from previous runs (full summary plus per-day logs).

## Agent Tools
All tools given to the LLM follow the same MCP format, following the recommendation found in the [openrouter docs](https://openrouter.ai/docs/guides/features/tool-calling#function-definition-guidelines):
```json
{
    "type": "function",
    "function": {
        "name": "tool_name",
        "description": "A consicsise explanation for what this tool is and what it should be user for.",
        "parameters": {
            "type": "object",
            "properties": {
                "proerty1": "string",
                "property2": "int"
            },
            "required": ["property1"]
        }
 }
```

### Price
**MCP Tools**
```json
{
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
},
{
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
},
{
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
}
```
**Python Functions**
```python
def get_current_price(symbol: str) -> str:

def get_prices_batch(symbols: List[str]) -> Dict[str, float]:

def get_daily_ohlc(symbol: str, days: int = 1) -> Optional[List[Dict[str, Any]]]:
```

### Maths
**MCP Tools**
```json
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
```
**Python Functions**
```python
# takes are argument python expression, executes it, returns the result
def calculate(expression: str) -> str:

def calculate_percentage(old_value: float, new_value: float) -> str:

def batch_calculate(expressions: List[str]) -> List[Dict[str, Any]]:
```

### News
**MCP Tools**
```json
{
    "type": "function",
    "function": {
        "name": "get_market_insights",
        "description": "Get market news and insights for a specific stock ticker or general market news",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol to get news for"
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of news items to return (default 5)",
                    "default": 5
                }
            }
        }
    }
}
```
**Python Functions**
```python
def get_market_insights(ticker: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
```

### Trading
**MCP Tools**
```json
{
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
},
{
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
},
{
    "type": "function",
    "function": {
        "name": "get_portfolio",
        "description": "Get the current portfolio state including cash and all positions",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    }
},
{
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
}
```
**Python Functions**
```python
def buy_stock(symbol: str, quantity: float, price: float) -> str:

def sell_stock(symbol: str, quantity: float, price: float) -> str:

def get_portfolio() -> str:

def get_position(symbol: str) -> str:
```



## Setup
1) Install dependencies:
```
pip install -U pip
pip install pandas pyyaml python-dotenv openai requests
```
2) Add required environment variables in `.env` (same directory as `config.yaml`):
- `OPENROUTER_API_KEY` — LLM access for decision-making.
- `MASSIVE_API_KEY` — optional, enables `get_market_insights` news tool during runs.

## Running the Backtest
From the project root:
```
python src/backtest.py
```
Default behavior:
- Loads `data/10ticker12monthDaily.csv`.
- Simulates every Monday in the file with `$5,000` starting cash and the symbols listed in `config.yaml`.
- Writes rolling progress to `data/backtest_results/backtest_current.json` and per-day logs under `data/backtest_results/daily_logs/`.
- Saves a timestamped summary (equity curve, trades, metadata) in `data/backtest_results/backtest_YYYYMMDD_HHMMSS.json`.

To change inputs, edit `config.yaml` (symbols, initial capital, step budget) or point `csv_path`/`output_dir` directly in `run_backtest()` inside `src/backtest.py`.

## How the Backtesting Loop Works
1) Load historical OHLCV data into `HistoricalPriceData`, which exposes close prices, OHLC, and trading dates.
2) Derive all Mondays from the dataset and iterate one date at a time.
3) For each day:
   - Configure the global backtest context (current date, price data handle, shared portfolio).
   - Build a system prompt with strict steps: fetch news, fetch prices, inspect portfolio, run calculations, decide buy/sell/hold, execute trades, then emit `<FINISH_SIGNAL>`.
   - Let the LLM call tools. Tool calls are routed to local implementations that read from the historical dataset and mutate the simulated portfolio.
   - Record equity using the day’s close prices and append trades/logs.
4) After all days, emit a summary with total return, trade count, and an equity curve sample.

## Context Abstraction (`src/tools/context.py`)
The `BacktestContext` is a singleton that stores the simulated “today,” the historical price provider, and the shared portfolio. All tools pull these values implicitly, so their signatures match what a live system would use:
- Pricing functions read the close price for `current_date`.
- Trading functions apply buys/sells against the shared `BacktestPortfolio`.
- News fetching can filter by the simulated date.

Because tools depend on the context instead of explicit date/portfolio parameters, the same tool interfaces can be reused in production; swapping data sources only requires reconfiguring the context.

## Notes
- Live trading and live pricing APIs are not wired in; only the backtest path is implemented.
- The Massive news API call will be skipped with a clear error if `MASSIVE_API_KEY` is missing; backtests still run using price data alone.
