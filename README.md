# Trading Bot

A Python-based trading agent that uses LLM (via OpenRouter) to make trading decisions through MCP (Model Context Protocol) services.

## Project Structure

```
tradebot/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── mcp_client.py          # MCP client for communicating with MCP servers
│   ├── agent.py               # Trading agent with LLM integration
│   ├── main.py                # Main entry point
│   └── mcp_servers/           # MCP server implementations
│       ├── __init__.py
│       ├── math_server.py     # Math calculations MCP server
│       ├── search_server.py   # Market news/search MCP server
│       ├── trade_server.py    # Trade execution MCP server
│       └── stock_server.py    # Stock price data MCP server
├── config.yaml                # Configuration file
├── .env.example               # Example environment variables
├── requirements.txt           # Python dependencies
├── start_servers.py          # Script to start all MCP servers
└── README.md                  # This file

```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
- `OPENROUTER_API_KEY` - Required for LLM access
- `ALPHA_VANTAGE_API_KEY` - Optional, for market news (free tier: 25 requests/day)
- `FINNHUB_API_KEY` - Required for stock price data (free tier available)

### 3. Configure Trading Parameters

Edit `config.yaml` to customize:
- LLM model and provider
- Initial capital (default: $5000)
- Max steps per day (default: 10)
- List of symbols to trade
- MCP service URLs (default: localhost ports)

## Usage

### Step 1: Start MCP Servers

In separate terminal windows, start each MCP server:

**Terminal 1 - Math Server:**
```bash
python src/mcp_servers/math_server.py
```

**Terminal 2 - Search Server:**
```bash
python src/mcp_servers/search_server.py
```

**Terminal 3 - Trade Server:**
```bash
python src/mcp_servers/trade_server.py
```

**Terminal 4 - Stock Server:**
```bash
python src/mcp_servers/stock_server.py
```

Or use the convenience script (may need adjustments for your setup):
```bash
python start_servers.py
```

### Step 2: Run Trading Agent

Once all servers are running, execute the trading agent:

```bash
python src/main.py
```

Or specify a date:
```bash
python src/main.py 2024-01-15
```

## How It Works

1. **Configuration Loading**: Loads config from `config.yaml` and environment variables
2. **MCP Client Initialization**: Connects to math, search, trade, and stock_local MCP servers
3. **Tool Discovery**: Discovers available tools from each MCP server
4. **LLM Agent**: Creates an LLM agent (via OpenRouter) with access to all tools
5. **Daily Trading Loop**: Runs up to N steps (configurable) where the LLM:
   - Analyzes current portfolio
   - Gathers market information via search tools
   - Checks stock prices via stock tools
   - Makes trading decisions via trade tools
   - Uses math tools for calculations
6. **Results Storage**: Saves logs and daily results to JSON files in `./data/`

## Data Storage

All data is stored in the `./data/` directory:
- `portfolio_state.json` - Current portfolio state (cash, positions, trades)
- `logs.json` - Detailed logs of each trading run
- `daily_results.json` - Compact daily results summary
- `price_cache.json` - Cached price data (to reduce API calls)

## MCP Servers

### Math Server (Port 8001)
- `calculate` - Perform mathematical calculations
- `calculate_percentage` - Calculate percentage changes

### Search Server (Port 8002)
- `search_market_news` - Search for market news using Alpha Vantage
- `get_market_insights` - Get market insights for a specific symbol

### Trade Server (Port 8003)
- `buy_stock` - Buy shares of a stock
- `sell_stock` - Sell shares of a stock
- `get_portfolio` - Get current portfolio state
- `get_position` - Get position for a specific symbol

### Stock Server (Port 8004)
- `get_current_price` - Get current price for a symbol (uses cache)
- `get_daily_ohlc` - Get daily OHLC data (uses cache)
- `get_prices_batch` - Get prices for multiple symbols at once

## Notes

- The system uses fake money for trading simulation
- Initial capital is set in `config.yaml` (default: $5000)
- Portfolio state persists between runs
- Price data is cached to reduce API calls
- All trading decisions are logged for analysis

## Next Steps

Once working locally:
1. Set up GitHub Actions for automated daily runs
2. Build frontend dashboard (Cloudflare Pages)
3. Add more sophisticated trading strategies
4. Enhance error handling and retry logic

