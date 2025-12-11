"""
测试 base_graph.py 整个流程
用于验证 NL2SQL 系统是否能正常运行
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
# 安全修复：test文件在test子目录中，需要使用parent.parent获取项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from graphs.base_graph import run_query


def test_connection():
    """测试数据库连接"""
    print("=" * 60)
    print("Step 1: 测试数据库连接")
    print("=" * 60)
    
    try:
        from tools.db import db_client
        
        # 测试连接
        if db_client.test_connection():
            print("✓ 数据库连接成功")
            
            # 获取表名
            tables = db_client.get_table_names()
            print(f"✓ 找到 {len(tables)} 个表: {', '.join(tables[:5])}{'...' if len(tables) > 5 else ''}")
            return True
        else:
            print("✗ 数据库连接失败")
            return False
    except Exception as e:
        print(f"✗ 数据库连接错误: {e}")
        print("\n请检查:")
        print("  1. MySQL 服务是否运行")
        print("  2. .env 文件中的 MySQL 配置是否正确")
        print("  3. 数据库 'chinook' 是否存在")
        return False


def test_schema_manager():
    """测试 Schema Manager"""
    print("\n" + "=" * 60)
    print("Step 2: 测试 Schema Manager")
    print("=" * 60)
    
    try:
        from tools.schema_manager import schema_manager
        
        # 检查 schema.json 是否存在
        schema_path = project_root / "data" / "schema.json"
        if not schema_path.exists():
            print("⚠️  schema.json 不存在，正在生成...")
            schema_manager.generate_schema_json()
            print("✓ schema.json 已生成")
        else:
            print("✓ schema.json 已存在")
            schema_manager.load_schema()
            print("✓ schema.json 已加载")
        
        # 测试智能匹配
        test_question = "查询客户信息"
        relevant_tables = schema_manager.find_relevant_tables(test_question)
        print(f"✓ 测试问题 '{test_question}' 匹配到表: {relevant_tables}")
        
        return True
    except Exception as e:
        print(f"✗ Schema Manager 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm_client():
    """测试 LLM 客户端"""
    print("\n" + "=" * 60)
    print("Step 3: 测试 LLM 客户端")
    print("=" * 60)
    
    try:
        from tools.llm_client import llm_client
        from configs.config import config
        
        # 检查配置
        llm_config = config.get_llm_config()
        provider = llm_config.get("provider")
        api_key = llm_config.get("api_key")
        
        print(f"LLM Provider: {provider}")
        
        if not api_key:
            print(f"⚠️  警告: {provider.upper()} API Key 未设置")
            print("  请在 .env 文件中设置相应的 API Key:")
            if provider == "deepseek":
                print("    DEEPSEEK_API_KEY=your_key")
            elif provider == "qwen":
                print("    QWEN_API_KEY=your_key")
            elif provider == "openai":
                print("    OPENAI_API_KEY=your_key")
            return False
        
        print(f"✓ API Key 已配置")
        
        # 简单测试
        test_prompt = "你好，请回复'测试成功'"
        print(f"发送测试请求...")
        response = llm_client.chat(prompt=test_prompt)
        print(f"✓ LLM 响应: {response[:50]}...")
        
        return True
    except Exception as e:
        print(f"✗ LLM 客户端错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_graph(question: str = None):
    """测试完整的 Graph 流程"""
    print("\n" + "=" * 60)
    print("Step 4: 测试完整 Graph 流程")
    print("=" * 60)
    
    if question is None:
        # 默认测试问题
        question = "查询前5个客户的名字和邮箱"
    
    print(f"测试问题: {question}")
    print("-" * 60)
    
    try:
        # 运行查询
        result = run_query(question)
        
        # 检查结果
        print("\n" + "=" * 60)
        print("最终结果检查")
        print("=" * 60)
        
        # 检查各个步骤
        checks = {
            "问题": result.get("question"),
            "意图解析": result.get("intent") is not None,
            "SQL 生成": result.get("candidate_sql") is not None,
            "SQL 执行": result.get("execution_result") is not None,
        }
        
        for key, value in checks.items():
            status = "✓" if value else "✗"
            print(f"{status} {key}: {value}")
        
        # 显示 SQL
        if result.get("candidate_sql"):
            print(f"\n生成的 SQL:")
            print(f"  {result['candidate_sql']}")
        
        # 显示执行结果
        exec_result = result.get("execution_result")
        if exec_result:
            if exec_result.get("ok"):
                print(f"\n✓ 执行成功")
                print(f"  返回行数: {exec_result.get('row_count', 0)}")
                print(f"  列名: {', '.join(exec_result.get('columns', []))}")
                
                # 显示前3行数据
                rows = exec_result.get("rows", [])
                if rows:
                    print(f"\n  前3行数据:")
                    for i, row in enumerate(rows[:3], 1):
                        print(f"    行 {i}: {dict(list(row.items())[:3])}...")
            else:
                print(f"\n✗ 执行失败: {exec_result.get('error')}")
        
        return result
        
    except Exception as e:
        print(f"\n✗ Graph 执行错误: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("NL2SQL 系统完整测试")
    print("=" * 60)
    
    # 步骤 1: 测试数据库连接
    if not test_connection():
        print("\n❌ 数据库连接失败，请先解决数据库问题")
        return
    
    # 步骤 2: 测试 Schema Manager
    if not test_schema_manager():
        print("\n❌ Schema Manager 测试失败")
        return
    
    # 步骤 3: 测试 LLM 客户端
    if not test_llm_client():
        print("\n⚠️  LLM 客户端测试失败，但可以继续测试 Graph（可能会失败）")
        user_input = input("\n是否继续测试 Graph? (y/n): ")
        if user_input.lower() != 'y':
            return
    
    # 步骤 4: 测试完整流程
    print("\n" + "=" * 60)
    print("开始测试完整流程")
    print("=" * 60)
    
    # 可以自定义测试问题
    import sys
    if len(sys.argv) > 1:
        test_question = " ".join(sys.argv[1:])
    else:
        test_question = None
    
    result = test_full_graph(test_question)
    
    if result:
        print("\n" + "=" * 60)
        print("✅ 测试完成!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ 测试失败")
        print("=" * 60)


if __name__ == "__main__":
    main()

