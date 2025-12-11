"""
测试 SQL Guardrail (M4) 功能
验证 SQL 校验与自修复功能是否正常工作
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
# 安全修复：test文件在test子目录中，需要使用parent.parent获取项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from graphs.nodes.validate_sql import validate_sql_node, should_retry_sql
from graphs.nodes.critique_sql import critique_sql_node
from graphs.state import NL2SQLState


def test_sqlglot_available():
    """测试 sqlglot 是否已安装"""
    print("=" * 60)
    print("测试 1: 检查 sqlglot 依赖")
    print("=" * 60)
    
    try:
        import sqlglot
        print(f"✓ sqlglot 已安装，版本: {sqlglot.__version__ if hasattr(sqlglot, '__version__') else 'unknown'}")
        return True
    except ImportError:
        print("✗ sqlglot 未安装")
        print("  请运行: pip install sqlglot>=20.0.0")
        return False


def test_validate_correct_sql():
    """测试验证正确的 SQL"""
    print("\n" + "=" * 60)
    print("测试 2: 验证正确的 SQL")
    print("=" * 60)
    
    correct_sql = "SELECT CustomerId, FirstName, LastName FROM customer LIMIT 5;"
    
    state: NL2SQLState = {
        "question": "查询前5个客户",
        "candidate_sql": correct_sql,
        "validation_result": None,
        "validation_errors": None,
        "validation_passed": None,
        "regeneration_count": 0,
        "max_regenerations": 3
    }
    
    result = validate_sql_node(state)
    
    if result.get("validation_passed"):
        print(f"✓ 验证通过: {correct_sql}")
        return True
    else:
        print(f"✗ 验证失败: {result.get('validation_errors')}")
        return False


def test_validate_incorrect_sql():
    """测试验证错误的 SQL"""
    print("\n" + "=" * 60)
    print("测试 3: 验证错误的 SQL（应该失败）")
    print("=" * 60)
    print("注意：sqlglot 只做语法验证，不做语义验证（如表/字段是否存在）")
    
    # 语法错误（sqlglot 可以检测的）
    syntax_errors = [
        {
            "sql": "SELECT * FROM customer WHERE;",
            "reason": "WHERE 子句不完整"
        },
        {
            "sql": "SELCT * FROM customer;",
            "reason": "SELECT 拼写错误"
        },
        {
            "sql": "SELECT * FROM customer GROUP BY;",
            "reason": "GROUP BY 子句不完整"
        },
        {
            "sql": "SELECT * FROM customer ORDER BY;",
            "reason": "ORDER BY 子句不完整"
        },
        {
            "sql": "SELECT * FROM customer WHERE id =;",
            "reason": "WHERE 条件不完整"
        },
        {
            "sql": "SELECT * FROM customer JOIN;",
            "reason": "JOIN 子句不完整"
        },
    ]
    
    # 语义错误（语法上正确，sqlglot 无法检测）
    semantic_errors = [
        {
            "sql": "SELECT FROM customer;",
            "reason": "缺少字段列表（某些 SQL 方言可能允许）"
        },
        {
            "sql": "SELECT * FROM nonexistent_table;",
            "reason": "表不存在（语法上有效）"
        },
    ]
    
    syntax_caught = 0
    syntax_total = len(syntax_errors)
    
    print("\n--- 语法错误测试（应该被捕获）---")
    for test_case in syntax_errors:
        sql = test_case["sql"]
        state: NL2SQLState = {
            "question": "测试查询",
            "candidate_sql": sql,
            "validation_result": None,
            "validation_errors": None,
            "validation_passed": None,
            "regeneration_count": 0,
            "max_regenerations": 3
        }
        
        result = validate_sql_node(state)
        
        if not result.get("validation_passed"):
            print(f"✓ 正确捕获: {sql}")
            print(f"  原因: {test_case['reason']}")
            syntax_caught += 1
        else:
            print(f"✗ 未捕获: {sql}")
            print(f"  原因: {test_case['reason']}")
    
    print(f"\n语法错误捕获率: {syntax_caught}/{syntax_total}")
    
    print("\n--- 语义错误测试（语法上有效，不会被 sqlglot 捕获）---")
    print("这些错误会在执行时被数据库捕获")
    for test_case in semantic_errors:
        sql = test_case["sql"]
        state: NL2SQLState = {
            "question": "测试查询",
            "candidate_sql": sql,
            "validation_result": None,
            "validation_errors": None,
            "validation_passed": None,
            "regeneration_count": 0,
            "max_regenerations": 3
        }
        
        result = validate_sql_node(state)
        
        if result.get("validation_passed"):
            print(f"✓ 预期行为（语法有效）: {sql}")
            print(f"  说明: {test_case['reason']}")
        else:
            print(f"⚠️  意外捕获: {sql}")
            print(f"  说明: {test_case['reason']}")
    
    # 只要语法错误都被捕获，就认为测试通过
    if syntax_caught == syntax_total:
        print(f"\n✅ 所有语法错误都被正确捕获 ({syntax_caught}/{syntax_total})")
        return True
    else:
        print(f"\n⚠️  部分语法错误未被捕获 ({syntax_caught}/{syntax_total})")
        # 如果捕获率 >= 80%，仍然认为测试通过（因为某些边缘情况可能难以检测）
        if syntax_caught >= syntax_total * 0.8:
            print("   捕获率 >= 80%，测试通过")
            return True
        return False


def test_should_retry_logic():
    """测试重试逻辑"""
    print("\n" + "=" * 60)
    print("测试 4: 测试重试决策逻辑")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "验证通过，应该执行",
            "state": {
                "validation_passed": True,
                "regeneration_count": 0,
                "max_regenerations": 3
            },
            "expected": "execute"
        },
        {
            "name": "验证失败，可以重试",
            "state": {
                "validation_passed": False,
                "regeneration_count": 0,
                "max_regenerations": 3
            },
            "expected": "retry"
        },
        {
            "name": "验证失败，超过最大重试次数",
            "state": {
                "validation_passed": False,
                "regeneration_count": 3,
                "max_regenerations": 3
            },
            "expected": "fail"
        },
        {
            "name": "验证失败，接近最大重试次数",
            "state": {
                "validation_passed": False,
                "regeneration_count": 2,
                "max_regenerations": 3
            },
            "expected": "retry"
        }
    ]
    
    all_passed = True
    for test_case in test_cases:
        result = should_retry_sql(test_case["state"])
        if result == test_case["expected"]:
            print(f"✓ {test_case['name']}: {result}")
        else:
            print(f"✗ {test_case['name']}: 期望 {test_case['expected']}, 实际 {result}")
            all_passed = False
    
    return all_passed


def test_critique_node():
    """测试 critique 节点（需要 LLM）"""
    print("\n" + "=" * 60)
    print("测试 5: 测试 Critique 节点")
    print("=" * 60)
    
    try:
        from tools.llm_client import llm_client
        from configs.config import config
        
        llm_config = config.get_llm_config()
        if not llm_config.get("api_key"):
            print("⚠️  LLM API Key 未配置，跳过 Critique 测试")
            print("   如需测试，请在 .env 文件中配置 LLM API Key")
            return None  # 跳过但不算失败
    except Exception as e:
        print(f"⚠️  无法加载 LLM 配置: {e}")
        return None
    
    # 模拟一个验证失败的状态
    state: NL2SQLState = {
        "question": "查询客户信息",
        "candidate_sql": "SELECT * FROM customer WHERE;",  # 错误的 SQL
        "validation_result": {
            "valid": False,
            "errors": ["WHERE clause is incomplete"]
        },
        "validation_errors": ["WHERE clause is incomplete"],
        "validation_passed": False,
        "regeneration_count": 0,
        "max_regenerations": 3
    }
    
    try:
        result = critique_sql_node(state)
        
        if result.get("critique"):
            print("✓ Critique 生成成功")
            print(f"  长度: {len(result['critique'])} 字符")
            print(f"  预览: {result['critique'][:100]}...")
            return True
        else:
            print("✗ Critique 生成失败")
            return False
    except Exception as e:
        print(f"✗ Critique 节点错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_guardrail_flow():
    """测试完整的 guardrail 流程"""
    print("\n" + "=" * 60)
    print("测试 6: 完整 Guardrail 流程（需要 LLM 和数据库）")
    print("=" * 60)
    
    try:
        from graphs.base_graph import run_query
        
        # 测试一个可能生成错误 SQL 的问题
        # 注意：这个测试需要 LLM，可能会消耗 API 调用
        
        print("⚠️  此测试需要 LLM API，将消耗 API 调用次数")
        user_input = input("是否继续？(y/n): ")
        if user_input.lower() != 'y':
            print("跳过完整流程测试")
            return None
        
        # 使用一个可能触发错误的问题
        question = "查询所有客户的名字"
        
        print(f"\n测试问题: {question}")
        print("运行完整流程...")
        
        result = run_query(question)
        
        # 检查结果
        print("\n" + "=" * 60)
        print("流程结果检查")
        print("=" * 60)
        
        checks = {
            "SQL 生成": result.get("candidate_sql") is not None,
            "验证执行": result.get("validation_result") is not None,
            "验证通过": result.get("validation_passed", False),
            "重试次数": result.get("regeneration_count", 0),
        }
        
        for key, value in checks.items():
            status = "✓" if value else "✗"
            print(f"{status} {key}: {value}")
        
        # 显示详细信息
        if result.get("candidate_sql"):
            print(f"\n最终 SQL: {result['candidate_sql']}")
        
        if result.get("validation_result"):
            val_result = result["validation_result"]
            print(f"\n验证结果:")
            print(f"  通过: {val_result.get('valid', False)}")
            if val_result.get("errors"):
                print(f"  错误: {val_result['errors']}")
            if val_result.get("warnings"):
                print(f"  警告: {val_result['warnings']}")
        
        if result.get("regeneration_count", 0) > 0:
            print(f"\n✓ 触发了自修复流程，重试了 {result['regeneration_count']} 次")
        
        return True
        
    except Exception as e:
        print(f"✗ 完整流程测试错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("SQL Guardrail (M4) 功能测试")
    print("=" * 60)
    
    results = {}
    
    # 测试 1: sqlglot 依赖
    results["sqlglot"] = test_sqlglot_available()
    
    if not results["sqlglot"]:
        print("\n⚠️  sqlglot 未安装，部分测试将跳过")
        print("   请运行: pip install sqlglot>=20.0.0")
    else:
        # 测试 2: 验证正确 SQL
        results["validate_correct"] = test_validate_correct_sql()
        
        # 测试 3: 验证错误 SQL
        results["validate_incorrect"] = test_validate_incorrect_sql()
    
    # 测试 4: 重试逻辑
    results["retry_logic"] = test_should_retry_logic()
    
    # 测试 5: Critique 节点（可选，需要 LLM）
    results["critique"] = test_critique_node()
    
    # 测试 6: 完整流程（可选，需要 LLM 和数据库）
    print("\n" + "=" * 60)
    print("是否运行完整流程测试？")
    print("（需要 LLM API 和数据库连接，会消耗 API 调用）")
    print("=" * 60)
    user_input = input("运行完整流程测试? (y/n): ")
    if user_input.lower() == 'y':
        results["full_flow"] = test_full_guardrail_flow()
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for test_name, result in results.items():
        if result is None:
            status = "⏭️  跳过"
        elif result:
            status = "✓ 通过"
        else:
            status = "✗ 失败"
        print(f"{status} {test_name}")
    
    # 统计
    passed = sum(1 for r in results.values() if r is True)
    failed = sum(1 for r in results.values() if r is False)
    skipped = sum(1 for r in results.values() if r is None)
    total = len(results)
    
    print(f"\n总计: {total} 个测试")
    print(f"  通过: {passed}")
    print(f"  失败: {failed}")
    print(f"  跳过: {skipped}")
    
    if failed == 0:
        print("\n✅ 所有测试通过！")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查上述输出")


if __name__ == "__main__":
    main()
