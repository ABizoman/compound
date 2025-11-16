import json
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class MCPTool:
    """Represents an MCP tool."""
    name: str
    description: str
    parameters: Dict[str, Any]


class MCPClient:
    """Client for communicating with MCP servers over HTTP."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.tools: List[MCPTool] = []
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize the client by fetching available tools."""
        if self._initialized:
            return
        
        try:
            response = requests.post(
                f"{self.base_url}/mcp/tools/list",
                json={},
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            # Parse tools from MCP response
            if 'tools' in data:
                self.tools = [
                    MCPTool(
                        name=tool['name'],
                        description=tool.get('description', ''),
                        parameters=tool.get('inputSchema', {})
                    )
                    for tool in data['tools']
                ]
            
            self._initialized = True
        except Exception as e:
            print(f"Warning: Could not initialize MCP client at {self.base_url}: {e}")
            self._initialized = False
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call an MCP tool with given arguments."""
        try:
            response = requests.post(
                f"{self.base_url}/mcp/tools/call",
                json={
                    "name": tool_name,
                    "arguments": arguments
                },
                timeout=30
            )
            response.raise_for_status()
            
            # Handle empty or None response
            try:
                result = response.json()
                if result is None:
                    return {
                        "error": "Empty response from server",
                        "content": [{"type": "text", "text": f"Empty response from {tool_name}"}]
                    }
                return result
            except (json.JSONDecodeError, ValueError) as e:
                # Response is not valid JSON
                return {
                    "error": f"Invalid JSON response: {str(e)}",
                    "content": [{"type": "text", "text": f"Error: Invalid response from {tool_name}: {response.text[:200]}"}]
                }
        except requests.exceptions.RequestException as e:
            return {
                "error": str(e),
                "content": [{"type": "text", "text": f"Error calling tool {tool_name}: {e}"}]
            }
        except Exception as e:
            return {
                "error": str(e),
                "content": [{"type": "text", "text": f"Unexpected error calling tool {tool_name}: {e}"}]
            }
    
    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """Get tools in format suitable for LLM function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters
                }
            }
            for tool in self.tools
        ]

