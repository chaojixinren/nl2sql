"""
测试 Dialog Clarification (M7) 功能
验证多轮对话与澄清问题功能是否正常工作
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from graphs.nodes.clarify import (
    check_if_needs_clarification,
    clarify_node,
    parse_clarification_response,
    should_ask_clarification
)
from graphs.state import NL2SQLState
from graphs.base_graph import run_query


def test_clarification_criteria():
    """测试澄清判据"""
    print("=" * 60)
    print("测试 1: 澄清判据检查")
    print("=" * 60)
    
    test_cases = [
        {
            "question": "查询最近的销售数据",
            "should_clarify": True,
            "reason": "缺少具体时间范围"
        },
        {
            "question": "查询最近一个月的销售数据",
            "should_clarify": False,
            "reason": "时间范围明确"
        },
        {
            "question": "统计客户信息",
            "should_clarify": True,
            "reason": "聚合方式不明确"
        },
        {
            "question": "统计客户总数",
            "should_clarify": False,
            "reason": "聚合方式明确（总数）"
        },
        {
            "question": "查看订单情况",
            "should_clarify": True,
            "reason": "字段需求不明确"
        },
        {
            "question": "查询订单ID和订单日期",
            "should_clarify": False,
            "reason": "字段需求明确"
        },
        {
            "question": "查询最重要的客户",
            "should_clarify": True,
            "reason": "存在歧义词汇（最重要）"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        result = check_if_needs_clarification(case["question"])
        needs_clarify = result["needs_clarification"]
        expected = case["should_clarify"]
        
        if needs_clarify == expected:
            print(f"✓ 测试 {i}: '{case['question']}'")
            print(f"  预期: {'需要澄清' if expected else '不需要澄清'}")
            print(f"  实际: {'需要澄清' if needs_clarify else '不需要澄清'}")
            if result.get("reasons"):
                print(f"  原因: {', '.join(result['reasons'])}")
            passed += 1
        else:
            print(f"✗ 测试 {i}: '{case['question']}'")
            print(f"  预期: {'需要澄清' if expected else '不需要澄清'}")
            print(f"  实际: {'需要澄清' if needs_clarify else '不需要澄清'}")
            failed += 1
    
    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_parse_clarification_response():
    """测试解析澄清问题响应"""
    print("\n" + "=" * 60)
    print("测试 2: 解析澄清问题响应")
    print("=" * 60)
    
    test_cases = [
        {
            "response": """问题: 请选择您想查询的时间范围

选项:
1. 最近一周
2. 最近一个月
3. 最近三个月
4. 今年""",
            "expected_question": "请选择您想查询的时间范围",
            "expected_options_count": 4
        },
        {
            "response": """澄清问题: 您希望如何统计客户信息？

选项:
1. 统计客户总数
2. 按城市分组统计
3. 按国家分组统计""",
            "expected_question": "您希望如何统计客户信息？",
            "expected_options_count": 3
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        question, options = parse_clarification_response(case["response"])
        
        question_match = question == case["expected_question"]
        options_match = len(options) == case["expected_options_count"]
        
        if question_match and options_match:
            print(f"✓ 测试 {i}: 解析成功")
            print(f"  问题: {question}")
            print(f"  选项数量: {len(options)}")
            for j, opt in enumerate(options, 1):
                print(f"    {j}. {opt}")
            passed += 1
        else:
            print(f"✗ 测试 {i}: 解析失败")
            print(f"  预期问题: {case['expected_question']}")
            print(f"  实际问题: {question}")
            print(f"  预期选项数: {case['expected_options_count']}")
            print(f"  实际选项数: {len(options)}")
            failed += 1
    
    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_clarify_node_without_answer():
    """测试澄清节点（无用户回答）"""
    print("\n" + "=" * 60)
    print("测试 3: 澄清节点 - 生成澄清问题")
    print("=" * 60)
    
    state: NL2SQLState = {
        "question": "查询最近的销售数据",
        "session_id": "test_session_001",
        "user_id": "test_user",
        "dialog_history": [],
        "candidate_sql": "SELECT * FROM invoices ORDER BY InvoiceDate DESC LIMIT 100;",
        "clarification_answer": None,
        "clarification_count": 0,
        "max_clarifications": 3,
        "needs_clarification": None,
        "clarification_question": None,
        "clarification_options": None,
        "normalized_question": None,
        "timestamp": None,
        "intent": None,
        "sql_generated_at": None,
        "execution_result": None,
        "executed_at": None,
        "validation_result": None,
        "validation_errors": None,
        "validation_passed": None,
        "critique": None,
        "regeneration_count": 0,
        "max_regenerations": 3
    }
    
    try:
        result = clarify_node(state)
        
        if result.get("needs_clarification"):
            print("✓ 澄清节点执行成功")
            print(f"  需要澄清: {result.get('needs_clarification')}")
            print(f"  澄清问题: {result.get('clarification_question')}")
            if result.get("clarification_options"):
                print(f"  选项数量: {len(result['clarification_options'])}")
                for i, opt in enumerate(result["clarification_options"], 1):
                    print(f"    {i}. {opt}")
            print(f"  澄清次数: {result.get('clarification_count')}")
            print(f"  对话历史长度: {len(result.get('dialog_history', []))}")
            return True
        else:
            print("⚠️  未生成澄清问题（可能不需要澄清或生成失败）")
            return False
    except Exception as e:
        print(f"✗ 澄清节点执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_clarify_node_with_answer():
    """测试澄清节点（有用户回答）"""
    print("\n" + "=" * 60)
    print("测试 4: 澄清节点 - 处理用户回答")
    print("=" * 60)
    
    state: NL2SQLState = {
        "question": "查询最近的销售数据",
        "session_id": "test_session_002",
        "user_id": "test_user",
        "dialog_history": [
            {
                "role": "user",
                "content": "查询最近的销售数据",
                "timestamp": "2024-01-15T10:00:00",
                "type": "question"
            },
            {
                "role": "assistant",
                "content": "请选择您想查询的时间范围",
                "timestamp": "2024-01-15T10:00:01",
                "type": "clarification",
                "options": ["最近一周", "最近一个月", "最近三个月"]
            }
        ],
        "candidate_sql": None,
        "clarification_answer": "最近一个月",  # 用户回答
        "clarification_question": "请选择您想查询的时间范围",
        "clarification_options": ["最近一周", "最近一个月", "最近三个月"],
        "clarification_count": 1,
        "max_clarifications": 3,
        "needs_clarification": True,
        "normalized_question": None,
        "timestamp": None,
        "intent": None,
        "sql_generated_at": None,
        "execution_result": None,
        "executed_at": None,
        "validation_result": None,
        "validation_errors": None,
        "validation_passed": None,
        "critique": None,
        "regeneration_count": 0,
        "max_regenerations": 3
    }
    
    try:
        result = clarify_node(state)
        
        if result.get("normalized_question"):
            print("✓ 用户回答处理成功")
            print(f"  原始问题: {state['question']}")
            print(f"  规范化问题: {result.get('normalized_question')}")
            print(f"  澄清回答已清空: {result.get('clarification_answer') is None}")
            print(f"  不再需要澄清: {not result.get('needs_clarification', True)}")
            print(f"  对话历史长度: {len(result.get('dialog_history', []))}")
            return True
        else:
            print("✗ 用户回答处理失败：未生成规范化问题")
            return False
    except Exception as e:
        print(f"✗ 用户回答处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_should_ask_clarification():
    """测试澄清判断函数"""
    print("\n" + "=" * 60)
    print("测试 5: 澄清判断函数")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "需要澄清且未生成问题",
            "state": {
                "needs_clarification": True,
                "clarification_question": None,
                "clarification_answer": None
            },
            "expected": "clarify"
        },
        {
            "name": "用户已回答澄清问题",
            "state": {
                "needs_clarification": True,
                "clarification_question": "请选择时间范围",
                "clarification_answer": "最近一个月"
            },
            "expected": "regenerate"
        },
        {
            "name": "不需要澄清",
            "state": {
                "needs_clarification": False,
                "clarification_question": None,
                "clarification_answer": None
            },
            "expected": "continue"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        # 创建完整state
        state: NL2SQLState = {
            "question": "测试问题",
            "session_id": "test",
            **case["state"],
            "user_id": None,
            "dialog_history": [],
            "candidate_sql": None,
            "clarification_count": 0,
            "max_clarifications": 3,
            "clarification_options": None,
            "normalized_question": None,
            "timestamp": None,
            "intent": None,
            "sql_generated_at": None,
            "execution_result": None,
            "executed_at": None,
            "validation_result": None,
            "validation_errors": None,
            "validation_passed": None,
            "critique": None,
            "regeneration_count": 0,
            "max_regenerations": 3
        }
        
        result = should_ask_clarification(state)
        expected = case["expected"]
        
        if result == expected:
            print(f"✓ 测试 {i}: {case['name']}")
            print(f"  预期: {expected}, 实际: {result}")
            passed += 1
        else:
            print(f"✗ 测试 {i}: {case['name']}")
            print(f"  预期: {expected}, 实际: {result}")
            failed += 1
    
    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_full_clarification_flow():
    """测试完整的澄清流程（需要LLM和数据库）"""
    print("\n" + "=" * 60)
    print("测试 6: 完整澄清流程（端到端测试）")
    print("=" * 60)
    print("注意：此测试需要LLM API和数据库连接")
    
    try:
        # 第一轮：用户提问（应该触发澄清）
        print("\n--- 第一轮：用户提问 ---")
        result1 = run_query(
            question="查询最近的销售数据",
            session_id="test_full_flow",
            user_id="test_user"
        )
        
        needs_clarify = result1.get("needs_clarification")
        clarification_question = result1.get("clarification_question")
        
        if needs_clarify and clarification_question:
            print("✓ 第一轮：成功生成澄清问题")
            print(f"  澄清问题: {clarification_question}")
            if result1.get("clarification_options"):
                print("  选项:")
                for i, opt in enumerate(result1.get("clarification_options", []), 1):
                    print(f"    {i}. {opt}")
            
            # 模拟用户选择第一个选项
            user_answer = result1.get("clarification_options", [])[0] if result1.get("clarification_options") else "最近一个月"
            
            print(f"\n--- 第二轮：用户回答 '{user_answer}' ---")
            result2 = run_query(
                question="查询最近的销售数据",
                session_id="test_full_flow",  # 相同session
                user_id="test_user",
                clarification_answer=user_answer
            )
            
            normalized_question = result2.get("normalized_question")
            candidate_sql = result2.get("candidate_sql")
            
            if normalized_question:
                print("✓ 第二轮：成功处理用户回答")
                print(f"  规范化问题: {normalized_question}")
                if candidate_sql:
                    print(f"  生成的SQL: {candidate_sql[:100]}...")
                    return True
                else:
                    print("⚠️  SQL未生成（可能流程中断）")
                    return False
            else:
                print("✗ 第二轮：处理用户回答失败")
                return False
        else:
            print("⚠️  第一轮：未生成澄清问题（可能问题已经足够明确）")
            return False
            
    except Exception as e:
        print(f"✗ 完整流程测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_max_clarifications():
    """测试最大澄清次数限制"""
    print("\n" + "=" * 60)
    print("测试 7: 最大澄清次数限制")
    print("=" * 60)
    
    state: NL2SQLState = {
        "question": "查询数据",  # 非常模糊的问题
        "session_id": "test_max_clarify",
        "user_id": "test_user",
        "dialog_history": [],
        "candidate_sql": None,
        "clarification_answer": None,
        "clarification_count": 3,  # 已达到最大次数
        "max_clarifications": 3,
        "needs_clarification": None,
        "clarification_question": None,
        "clarification_options": None,
        "normalized_question": None,
        "timestamp": None,
        "intent": None,
        "sql_generated_at": None,
        "execution_result": None,
        "executed_at": None,
        "validation_result": None,
        "validation_errors": None,
        "validation_passed": None,
        "critique": None,
        "regeneration_count": 0,
        "max_regenerations": 3
    }
    
    try:
        result = clarify_node(state)
        
        if not result.get("needs_clarification"):
            print("✓ 达到最大澄清次数后，不再生成澄清问题")
            print(f"  澄清次数: {result.get('clarification_count')}")
            print(f"  需要澄清: {result.get('needs_clarification')}")
            return True
        else:
            print("✗ 达到最大澄清次数后，仍然生成澄清问题")
            return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("=" * 60)
    print("M7 Dialog Clarification 功能测试")
    print("=" * 60)
    
    results = []
    
    # 基础功能测试（不需要LLM和数据库）
    results.append(("澄清判据检查", test_clarification_criteria()))
    results.append(("解析澄清响应", test_parse_clarification_response()))
    results.append(("澄清判断函数", test_should_ask_clarification()))
    results.append(("最大澄清次数", test_max_clarifications()))
    
    # 需要LLM的测试
    print("\n" + "=" * 60)
    print("以下测试需要LLM API支持")
    print("=" * 60)
    
    try:
        from tools.llm_client import llm_client
        # 测试LLM连接
        test_prompt = "测试"
        llm_client.chat(prompt=test_prompt)
        
        results.append(("生成澄清问题", test_clarify_node_without_answer()))
        results.append(("处理用户回答", test_clarify_node_with_answer()))
        
        # 完整流程测试（需要数据库）
        print("\n" + "=" * 60)
        print("以下测试需要数据库连接")
        print("=" * 60)
        
        try:
            from tools.db import db_client
            if db_client.test_connection():
                results.append(("完整澄清流程", test_full_clarification_flow()))
            else:
                print("⚠️  数据库未连接，跳过完整流程测试")
        except Exception as e:
            print(f"⚠️  数据库连接失败: {e}")
            print("  跳过完整流程测试")
    except Exception as e:
        print(f"⚠️  LLM未配置或连接失败: {e}")
        print("  跳过需要LLM的测试")
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status}: {name}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())

