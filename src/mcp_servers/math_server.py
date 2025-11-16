import json
import math
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
_project_root = Path(__file__).parent.parent.parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    # Fallback to default behavior (searches current directory and parents)
    load_dotenv()


app = FastAPI(title="Math MCP Server")


class ToolCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any]


class ToolCallResponse(BaseModel):
    content: List[Dict[str, Any]]


# Available math tools
MATH_TOOLS = [
    {
        "name": "calculate",
        "description": "Perform basic mathematical calculations (addition, subtraction, multiplication, division, exponentiation, etc.). Supports expressions like '2+2', '10*5', 'sqrt(16)', 'pow(2,3)'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate"
                }
            },
            "required": ["expression"]
        }
    },
    {
        "name": "calculate_percentage",
        "description": "Calculate percentage change between two values",
        "inputSchema": {
            "type": "object",
            "properties": {
                "old_value": {"type": "number", "description": "Original value"},
                "new_value": {"type": "number", "description": "New value"}
            },
            "required": ["old_value", "new_value"]
        }
    }
]


@app.post("/mcp/tools/list")
async def list_tools():
    """List available tools."""
    return {"tools": MATH_TOOLS}


@app.post("/mcp/tools/call")
async def call_tool(request: ToolCallRequest):
    """Call a math tool."""
    try:
        if request.name == "calculate":
            expression = request.arguments.get("expression", "")
            # Safe evaluation of mathematical expressions
            result = eval(expression, {"__builtins__": {}}, {"math": math, "sqrt": math.sqrt, "pow": pow})
            return {
                "content": [
                    {"type": "text", "text": str(result)}
                ]
            }
        
        elif request.name == "calculate_percentage":
            old_value = request.arguments.get("old_value")
            new_value = request.arguments.get("new_value")
            if old_value == 0:
                raise ValueError("Cannot calculate percentage change when old_value is 0")
            percentage_change = ((new_value - old_value) / old_value) * 100
            return {
                "content": [
                    {"type": "text", "text": f"{percentage_change:.2f}%"}
                ]
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {request.name}")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

