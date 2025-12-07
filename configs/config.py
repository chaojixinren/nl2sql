"""
Configuration loader for NL2SQL system.
Loads settings from .env and configs/dev.yaml
Supports multiple LLM providers: DeepSeek, Qwen, OpenAI
"""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Any, Optional


# Load .env file
load_dotenv()


class Config:
    """Configuration manager for NL2SQL system."""
    
    def reload(self):
        """重新加载配置"""
        # 重新加载 .env 文件，override=True 确保覆盖已有的环境变量
        load_dotenv(override=True)
        self._load_yaml_config()
        self._load_env_vars()
        print("✓ Configuration reloaded")

    def __init__(self, env: str = "dev"):
        """
        Initialize configuration.

        Args:
            env: Environment name (dev, prod, etc.)
        """
        self.env = env
        self._load_yaml_config()
        self._load_env_vars()

    def _load_yaml_config(self):
        """Load configuration from YAML file."""
        config_path = Path(__file__).parent.parent / "configs" / f"{self.env}.yaml"

        if not config_path.exists():
            print(f"Warning: Config file {config_path} not found. Using defaults.")
            self.yaml_config = {}
            return

        with open(config_path, "r", encoding="utf-8") as f:
            self.yaml_config = yaml.safe_load(f) or {}

    def _load_env_vars(self):
        """Load configuration from environment variables."""
        self.env_config = {
            # LLM Provider
            "llm_provider": os.getenv("LLM_PROVIDER", "deepseek"),

            # DeepSeek
            "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
            "deepseek_base_url": os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            "deepseek_model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),

            # Qwen
            "qwen_api_key": os.getenv("QWEN_API_KEY", ""),
            "qwen_base_url": os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            "qwen_model": os.getenv("QWEN_MODEL", "qwen-plus"),

            # OpenAI
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "openai_base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            "openai_model": os.getenv("OPENAI_MODEL", "gpt-4"),

            # LLM Common
            "llm_temperature": float(os.getenv("LLM_TEMPERATURE", "0.0")),
            "llm_max_tokens": int(os.getenv("LLM_MAX_TOKENS", "2000")),
            "llm_timeout": int(os.getenv("LLM_TIMEOUT", "30")),

            # Embedding
            "embedding_provider": os.getenv("EMBEDDING_PROVIDER", "local"),
            "embedding_model": os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-zh-v1.5"),

            # Database
            "db_type": os.getenv("DB_TYPE", "sqlite"),
            "db_path": os.getenv("DB_PATH", "data/chinook.db"),

            # System
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            "max_retries": int(os.getenv("MAX_RETRIES", "3")),
            "timeout": int(os.getenv("TIMEOUT", "30")),
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key (supports dot notation, e.g., 'llm.model')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        # Try env vars first
        if key in self.env_config:
            return self.env_config[key]

        # Try YAML config with dot notation
        keys = key.split(".")
        value = self.yaml_config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get LLM configuration based on the selected provider.

        Returns:
            Dictionary with api_key, base_url, model, and other LLM settings
        """
        provider = self.get("llm_provider", "deepseek").lower()

        config = {
            "provider": provider,
            "temperature": self.get("llm_temperature", 0.0),
            "max_tokens": self.get("llm_max_tokens", 2000),
            "timeout": self.get("llm_timeout", 30),
        }

        if provider == "deepseek":
            config.update({
                "api_key": self.get("deepseek_api_key"),
                "base_url": self.get("deepseek_base_url"),
                "model": self.get("deepseek_model"),
            })
        elif provider == "qwen":
            config.update({
                "api_key": self.get("qwen_api_key"),
                "base_url": self.get("qwen_base_url"),
                "model": self.get("qwen_model"),
            })
        elif provider == "openai":
            config.update({
                "api_key": self.get("openai_api_key"),
                "base_url": self.get("openai_base_url"),
                "model": self.get("openai_model"),
            })
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

        return config

    def get_all(self) -> Dict[str, Any]:
        """Get all configuration as a dictionary."""
        return {
            "env": self.env,
            "yaml_config": self.yaml_config,
            "env_config": self.env_config
        }


# Global config instance
config = Config()
