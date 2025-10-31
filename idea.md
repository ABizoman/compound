Project Description

A Python-based trading agent that runs once per market day (Monday to Friday). The agent connects to the same MCP services used in the AI-Trader repo to get data and act: a math MCP service, a search MCP service, a stock/price MCP service, and a trade MCP service. The agent then calls a configurable LLM (for example via OpenRouter) to decide what to do with the portfolio. The LLM and model name must be set in a config file so it is easy to switch providers without changing code.

MCP services to use
	•	math: general calculations, exposed as MCP over HTTP 
	•	search: fetches extra information/news for the agent 
        - Aplha Advantage (for market insights) MCP server is free for up to 25 requests per day. https://mcp.alphavantage.co
        - Jina AI for news and market info, I think they have an MCP as well

	•	trade: applies the decision or records the trade/simulation 
	•	stock_local (price): returns market/price data for the traded symbols 

Daily run flow
	1.	Load config (model, API base, API key, max steps, symbols, MCP URLs).
	2.	Initialize MCP clients for math, search, trade, and stock_local.
	3.	Create the LLM agent for today’s date.
	4.	Run a bounded loop of LLM/tool calls (for example, up to 10 steps) for that date.
	5.	Update and save positions and logs to disk as JSON.
	6.	Optionally export a compact daily result (date, equity/cash, positions, model used) for a dashboard.

Hosting
	•	The trading engine (Python + MCP services) runs on github actions once we can see that it's working locally.
	•	A separate frontend (Cloudflare Pages + a small Worker) can read the exported JSON and display performance over time.


