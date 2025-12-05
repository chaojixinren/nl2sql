#!/usr/bin/env python
"""
测试 LLM 配置切换
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from configs.config import Config

def test_llm_provider(provider: str):
    """测试特定 LLM 提供商配置"""
    # 临时设置环境变量
    os.environ["LLM_PROVIDER"] = provider

    # 重新加载配置
    config = Config()
    llm_config = config.get_llm_config()

    print(f"\n=== {provider.upper()} 配置 ===")
    print(f"Provider: {llm_config['provider']}")
    print(f"Model: {llm_config.get('model', 'N/A')}")
    print(f"Base URL: {llm_config.get('base_url', 'N/A')}")
    print(f"API Key Set: {'Yes' if llm_config.get('api_key') else 'No'}")

if __name__ == "__main__":
    providers = ["deepseek", "qwen", "openai"]

    print("=== LLM 配置切换测试 ===")

    for provider in providers:
        try:
            test_llm_provider(provider)
        except Exception as e:
            print(f"Error with {provider}: {e}")

    print("\n✓ 测试完成")