import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
_project_root = Path(__file__).parent.parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)
else:
    # Fallback to default behavior (searches current directory and parents)
    load_dotenv()


class Config:
    """Configuration manager for the trading bot."""
    
    def __init__(self, config_path: str = "config.yaml"):
        # Resolve config path relative to project root (parent of src/)
        if Path(config_path).is_absolute():
            self.config_path = Path(config_path)
        else:
            # Try to find config.yaml relative to project root
            # If running from src/, go up one level; if from root, use as-is
            project_root = Path(__file__).parent.parent
            self.config_path = project_root / config_path
            # If not found there, try current working directory as fallback
            if not self.config_path.exists():
                cwd_path = Path(config_path)
                if cwd_path.exists():
                    self.config_path = cwd_path
        
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value using dot notation (e.g., 'llm.model')."""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get an environment variable."""
        return os.getenv(key, default)
    
    @property
    def openrouter_api_key(self) -> str:
        """Get OpenRouter API key from environment."""
        key = self.get_env("OPENROUTER_API_KEY")
        if not key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        return key
    
    @property
    def llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration."""
        return self.config.get('llm', {})
    
    @property
    def trading_config(self) -> Dict[str, Any]:
        """Get trading configuration."""
        return self.config.get('trading', {})
    
    @property
    def mcp_services(self) -> Dict[str, str]:
        """Get MCP service URLs."""
        return self.config.get('mcp_services', {})
    
    @property
    def data_config(self) -> Dict[str, str]:
        """Get data storage configuration."""
        return self.config.get('data', {})

