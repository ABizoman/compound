"""Math tools for calculations and percentage changes."""

import math
from typing import List, Dict, Any


def calculate(expression: str) -> str:
    """Perform basic mathematical calculations.
    
    Args:
        expression: Mathematical expression to evaluate
        
    Returns:
        Result as string or error message
    """
    try:
        result = eval(expression, {"__builtins__": {}}, {"math": math, "sqrt": math.sqrt, "pow": pow})
        return str(result)
    except Exception as e:
        return f"Error calculating: {e}"


def calculate_percentage(old_value: float, new_value: float) -> str:
    """Calculate percentage change between two values.
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        Percentage change as string or error message
    """
    try:
        if old_value == 0:
            return "Error: Cannot calculate percentage change when old_value is 0"
        percentage_change = ((new_value - old_value) / old_value) * 100
        return f"{percentage_change:.2f}%"
    except Exception as e:
        return f"Error calculating percentage: {e}"


def batch_calculate(expressions: List[str]) -> List[Dict[str, Any]]:
    """Calculate multiple mathematical expressions in a single call.
    
    Args:
        expressions: List of mathematical expressions
        
    Returns:
        List of dicts with expression and result
    """
    results = []
    try:
        for expr in expressions:
            result = eval(expr, {"__builtins__": {}}, {"math": math, "sqrt": math.sqrt, "pow": pow})
            results.append({"expression": expr, "result": result})
        return results
    except Exception as e:
        return [{"error": f"Error in batch calculation: {e}"}]
