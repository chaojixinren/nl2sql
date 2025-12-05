"""
LLM Client wrapper for NL2SQL system.
Supports DeepSeek, Qwen, and OpenAI with unified interface.
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from configs.config import config


class LLMClient:
    """
    Unified LLM client supporting multiple providers.

    Supports:
    - DeepSeek (deepseek-chat)
    - Qwen (qwen-plus, qwen-max, qwen-turbo)
    - OpenAI (gpt-4, gpt-3.5-turbo)

    All providers use OpenAI-compatible API format.
    """

    def __init__(self, provider: Optional[str] = None):
        """
        Initialize LLM client.

        Args:
            provider: LLM provider (deepseek, qwen, openai)
                     If None, uses config.get_llm_config()
        """
        if provider:
            # Temporarily override provider
            import os
            os.environ["LLM_PROVIDER"] = provider
            from configs.config import Config
            llm_config = Config().get_llm_config()
        else:
            llm_config = config.get_llm_config()

        self.provider = llm_config["provider"]
        self.model = llm_config["model"]

        # Initialize ChatOpenAI with provider-specific config
        self.client = ChatOpenAI(
            model=llm_config["model"],
            api_key=llm_config["api_key"],
            base_url=llm_config["base_url"],
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"],
            timeout=llm_config["timeout"]
        )

        print(f"✓ LLM Client initialized: {self.provider} ({self.model})")

    def chat(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Send a chat message and get response.

        Args:
            prompt: User prompt
            system_message: Optional system message
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            LLM response text
        """
        messages = []

        if system_message:
            messages.append(SystemMessage(content=system_message))

        messages.append(HumanMessage(content=prompt))

        # Override client parameters if provided
        if kwargs:
            client = ChatOpenAI(
                model=self.model,
                api_key=self.client.openai_api_key,
                base_url=self.client.openai_api_base,
                temperature=kwargs.get("temperature", self.client.temperature),
                max_tokens=kwargs.get("max_tokens", self.client.max_tokens),
                timeout=self.client.timeout
            )
        else:
            client = self.client

        response = client.invoke(messages)

        return response.content

    def chat_with_messages(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Send a list of messages and get response.

        Args:
            messages: List of {role: str, content: str}
            **kwargs: Additional parameters

        Returns:
            LLM response text
        """
        formatted_messages = []

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                formatted_messages.append(SystemMessage(content=content))
            else:  # user or assistant
                formatted_messages.append(HumanMessage(content=content))

        response = self.client.invoke(formatted_messages)

        return response.content

    def __repr__(self):
        return f"LLMClient(provider={self.provider}, model={self.model})"


# Global LLM client instance
llm_client = LLMClient()


if __name__ == "__main__":
    """Test LLM client with different providers"""
    import sys

    print("=== LLM Client Test ===\n")

    # Test current provider
    print(f"Current Provider: {llm_client.provider}")
    print(f"Current Model: {llm_client.model}\n")

    # Test simple chat
    try:
        print("Testing simple chat...")
        response = llm_client.chat(
            prompt="将这句话翻译成SQL: 查询所有用户",
            system_message="你是一个SQL专家"
        )
        print(f"Response: {response}\n")
        print("✓ Chat test passed")

    except Exception as e:
        print(f"✗ Chat test failed: {e}")
        print("\n提示: 请确保已配置 API Key")
        print("  1. 复制 .env.example 到 .env")
        print("  2. 填入你的 API Key (DeepSeek/Qwen/OpenAI)")
        print("  3. 重新运行测试")
        sys.exit(1)

    print("\n=== Test Complete ===")
