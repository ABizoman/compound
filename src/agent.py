import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from openai import OpenAI

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import Config
from src.mcp_client import MCPClient


STOP_SIGNAL = "<FINISH_SIGNAL>"


class TradingAgent:
    """Trading agent that uses LLM to make trading decisions via MCP tools."""
    
    def __init__(self, config: Config):
        self.config = config
        self.llm_config = config.llm_config
        self.trading_config = config.trading_config
        
        # Initialize OpenAI client (OpenRouter uses OpenAI-compatible API)
        api_key = config.openrouter_api_key
        api_base = self.llm_config.get("api_base", "https://openrouter.ai/api/v1")
        
        # OpenRouter requires HTTP-Referer header (optional but recommended)
        self.client = OpenAI(
            api_key=api_key,
            base_url=api_base,
            default_headers={
                "HTTP-Referer": "https://github.com/tradebot",  # Optional: for tracking
                "X-Title": "Trading Bot"  # Optional: for tracking
            }
        )
        
        # Initialize MCP clients
        self.mcp_clients = {}
        mcp_urls = config.mcp_services
        
        for service_name, url in mcp_urls.items():
            client = MCPClient(url)
            try:
                client.initialize()
                self.mcp_clients[service_name] = client
                print(f"✓ Initialized {service_name} MCP client at {url}")
            except Exception as e:
                print(f"✗ Failed to initialize {service_name} MCP client: {e}")
        
        # Get all available tools from MCP clients
        self.tools = []
        for client in self.mcp_clients.values():
            self.tools.extend(client.get_tools_for_llm())
        
        print(f"✓ Loaded {len(self.tools)} tools from MCP services")
    
    def get_system_prompt(self, today_date: str) -> str:
        """Generate system prompt for the trading agent."""
        # Get initial portfolio state
        portfolio_state = self._get_portfolio_state()
        
        prompt = f"""You are a stock fundamental analysis trading assistant.

Your goals are:
- Think and reason by calling available tools.
- You need to think about the prices of various stocks and their returns.
- Your long-term goal is to maximize returns through this portfolio.
- Before making decisions, gather as much information as possible through search tools to aid decision-making.

Thinking standards:
- Clearly show key intermediate steps:
  - Read input of current positions and today's prices
  - Update valuation and adjust weights for each target (if strategy requires)
  - Use search tools to gather market news and insights
  - Make informed trading decisions based on analysis

Notes:
- You don't need to request user permission during operations, you can execute directly
- You must execute operations by calling tools, directly output operations will not be accepted
- Always check current prices before buying or selling
- When you think your task is complete, output {STOP_SIGNAL}

Here is the information you need:

Today's date: {today_date}

Current portfolio state:
{portfolio_state}

Available symbols to trade: {', '.join(self.trading_config.get('symbols', []))}

When you think your task is complete, output:
{STOP_SIGNAL}
"""
        return prompt
    
    def _get_portfolio_state(self) -> str:
        """Get current portfolio state from trade service."""
        if "trade" not in self.mcp_clients:
            return "Portfolio service not available"
        
        try:
            result = self.mcp_clients["trade"].call_tool("get_portfolio", {})
            if result.get("content"):
                return result["content"][0].get("text", "Unable to fetch portfolio")
        except Exception as e:
            return f"Error fetching portfolio: {e}"
        
        return "Unable to fetch portfolio"
    
    def run_daily(self, today_date: Optional[str] = None) -> Dict[str, Any]:
        """Run the trading agent for one day."""
        if today_date is None:
            today_date = datetime.now().strftime("%Y-%m-%d")
        
        print(f"\n{'='*60}")
        print(f"Running trading agent for {today_date}")
        print(f"{'='*60}\n")
        
        # Initialize conversation
        system_prompt = self.get_system_prompt(today_date)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Today is {today_date}. Please analyze the market and make trading decisions to maximize portfolio returns."}
        ]
        
        max_steps = self.trading_config.get("max_steps_per_day", 10)
        step_count = 0
        logs = []
        
        while step_count < max_steps:
            step_count += 1
            print(f"\n--- Step {step_count}/{max_steps} ---")
            
            try:
                # Call LLM
                response = self.client.chat.completions.create(
                    model=self.llm_config.get("model"),
                    messages=messages,
                    tools=self.tools if self.tools else None,
                    tool_choice="auto" if self.tools else None,
                    temperature=0.7
                )
                
                message = response.choices[0].message
                messages.append(message)
                
                # Check for stop signal
                if message.content and STOP_SIGNAL in message.content:
                    print(f"\n✓ Agent completed (stop signal received)")
                    logs.append({
                        "step": step_count,
                        "type": "stop",
                        "content": message.content
                    })
                    break
                
                # Handle tool calls
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        tool_name = tool_call.function.name
                        
                        # Handle arguments - might be None, string, or dict
                        arguments_raw = tool_call.function.arguments
                        if arguments_raw is None:
                            tool_args = {}
                        elif isinstance(arguments_raw, str):
                            try:
                                tool_args = json.loads(arguments_raw)
                            except json.JSONDecodeError as e:
                                print(f"⚠ Warning: Failed to parse tool arguments: {e}")
                                tool_args = {}
                        elif isinstance(arguments_raw, dict):
                            tool_args = arguments_raw
                        else:
                            tool_args = {}
                        
                        print(f"Calling tool: {tool_name}({tool_args})")
                        
                        # Find which MCP client has this tool
                        tool_result = None
                        for service_name, client in self.mcp_clients.items():
                            if any(t.name == tool_name for t in client.tools):
                                tool_result = client.call_tool(tool_name, tool_args)
                                break
                        
                        if not tool_result:
                            tool_result = {
                                "error": f"Tool {tool_name} not found",
                                "content": [{"type": "text", "text": f"Tool {tool_name} not found"}]
                            }
                        
                        # Add tool result to conversation
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
                        
                        # Print result
                        if tool_result.get("content"):
                            result_text = tool_result["content"][0].get("text", "")
                            print(f"   Result: {result_text[:200]}...")
                else:
                    # No tool calls, just assistant message
                    if message.content:
                        print(f"💬 {message.content[:200]}...")
                        logs.append({
                            "step": step_count,
                            "type": "message",
                            "content": message.content
                        })
            
            except Exception as e:
                print(f"✗ Error in step {step_count}: {e}")
                logs.append({
                    "step": step_count,
                    "type": "error",
                    "error": str(e)
                })
                break
        
        # Get final portfolio state
        final_portfolio = self._get_portfolio_state()
        
        return {
            "date": today_date,
            "steps": step_count,
            "logs": logs,
            "final_portfolio": final_portfolio,
            "model": self.llm_config.get("model")
        }

