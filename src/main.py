import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config import Config
from src.agent import TradingAgent


def initialize_portfolio(config: Config):
    """Initialize portfolio with starting capital."""
    data_config = config.data_config
    data_dir = Path(data_config.get("base_dir", "./data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    
    portfolio_file = data_dir / "portfolio_state.json"
    
    if not portfolio_file.exists():
        initial_capital = config.trading_config.get("initial_capital", 5000.0)
        portfolio_state = {
            "cash": float(initial_capital),
            "positions": {},
            "trades": [],
            "initialized_at": datetime.now().isoformat()
        }
        
        with open(portfolio_file, 'w') as f:
            json.dump(portfolio_state, f, indent=2)
        
        print(f"✓ Initialized portfolio with ${initial_capital:.2f}")
    else:
        # Load existing portfolio to check if it needs initialization
        try:
            with open(portfolio_file, 'r') as f:
                portfolio_state = json.load(f)
            if "cash" not in portfolio_state or portfolio_state.get("cash", 0) == 0:
                # Re-initialize if cash is missing or zero
                initial_capital = config.trading_config.get("initial_capital", 5000.0)
                portfolio_state["cash"] = float(initial_capital)
                portfolio_state["initialized_at"] = datetime.now().isoformat()
                with open(portfolio_file, 'w') as f:
                    json.dump(portfolio_state, f, indent=2)
                print(f"✓ Re-initialized portfolio with ${initial_capital:.2f}")
            else:
                print(f"✓ Portfolio already exists (cash: ${portfolio_state.get('cash', 0):.2f})")
        except Exception as e:
            print(f"⚠ Error reading portfolio: {e}, will re-initialize")
            initial_capital = config.trading_config.get("initial_capital", 5000.0)
            portfolio_state = {
                "cash": float(initial_capital),
                "positions": {},
                "trades": [],
                "initialized_at": datetime.now().isoformat()
            }
            with open(portfolio_file, 'w') as f:
                json.dump(portfolio_state, f, indent=2)
            print(f"✓ Re-initialized portfolio with ${initial_capital:.2f}")


def save_daily_result(config: Config, result: Dict[str, Any]):
    """Save daily trading result."""
    data_config = config.data_config
    data_dir = Path(data_config.get("base_dir", "./data"))
    daily_file = data_dir / config.data_config.get("daily_results_file", "daily_results.json")
    
    # Load existing results
    daily_results = []
    if daily_file.exists():
        with open(daily_file, 'r') as f:
            daily_results = json.load(f)
    
    # Add new result
    daily_results.append(result)
    
    # Save
    with open(daily_file, 'w') as f:
        json.dump(daily_results, f, indent=2)
    
    print(f"✓ Saved daily result to {daily_file}")


def save_logs(config: Config, result: Dict[str, Any]):
    """Save detailed logs."""
    data_config = config.data_config
    data_dir = Path(data_config.get("base_dir", "./data"))
    logs_file = data_dir / config.data_config.get("logs_file", "logs.json")
    
    # Load existing logs
    logs = []
    if logs_file.exists():
        with open(logs_file, 'r') as f:
            logs = json.load(f)
    
    # Add new log entry
    logs.append(result)
    
    # Save
    with open(logs_file, 'w') as f:
        json.dump(logs, f, indent=2)
    
    print(f"✓ Saved logs to {logs_file}")


def main():
    """Main entry point for daily trading run."""
    import sys
    
    # Parse command line arguments
    today_date = None
    if len(sys.argv) > 1:
        today_date = sys.argv[1]
    
    # Load configuration
    try:
        config = Config()
    except Exception as e:
        print(f"✗ Error loading config: {e}")
        return
    
    # Initialize portfolio
    initialize_portfolio(config)
    
    # Create trading agent
    try:
        agent = TradingAgent(config)
    except Exception as e:
        print(f"✗ Error creating trading agent: {e}")
        return
    
    # Run daily trading
    try:
        result = agent.run_daily(today_date)
        
        # Save results
        save_logs(config, result)
        
        # Create compact daily result
        daily_result = {
            "date": result["date"],
            "model": result["model"],
            "steps": result["steps"],
            "final_portfolio": result["final_portfolio"]
        }
        save_daily_result(config, daily_result)
        
        print(f"\n{'='*60}")
        print("Daily trading run completed!")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"✗ Error during trading run: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

