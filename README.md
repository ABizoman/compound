# Compound: An Autonomous Investing Framework

Compound is a backtesting harness that lets an LLM-driven trading agent practice making decisions over historical equity data. The agent sees realistic tools for prices, news, math, and trading, but the framework swaps in historical data so the model behaves as if it were live.

## Project Layout
- `config.yaml` — model/provider settings, trading symbols, capital, and step budget.
- `src/backtest.py` — main backtest runner, agent loop, portfolio tracking, and result writers.
- `src/config.py` — YAML + `.env` loader for runtime configuration and API keys.
- `src/tools/` — tool implementations the agent can call (`pricing`, `trading`, `news`, `math_tools`) plus the `context` abstraction that routes requests to historical data during simulation.
- `data/10ticker12monthDaily.csv` — sample price history used for default runs.
- `data/backtest_results/` — JSON artifacts from previous runs (full summary plus per-day logs).

## Setup
1) Use Python 3.10+ and create a virtual environment:
```
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
```
2) Install dependencies:
```
pip install -U pip
pip install pandas pyyaml python-dotenv openai requests
```
3) Add required environment variables in `.env` (same directory as `config.yaml`):
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
