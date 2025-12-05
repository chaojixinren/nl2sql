"""
M0 双语测试：测试中英文混合问题
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graphs.base_graph import run_query

def test_bilingual_questions():
    """测试中英文混合问题"""
    test_cases = [
        "查询 user 的订单",
        "Show me all 客户 in 北京",
        "统计 sales by region"
    ]

    print("=== M0 双语测试 ===\n")

    passed = 0
    for i, question in enumerate(test_cases, 1):
        print(f"Test Case {i}: {question}")

        result = run_query(question)

        # 验证基本字段存在
        assert result.get("question") == question
        assert result.get("intent") is not None
        assert result.get("session_id") is not None

        # 验证 intent 包含必要信息
        intent = result.get("intent")
        assert "type" in intent
        assert "question_length" in intent

        print(f"✓ Test Case {i} passed\n")
        passed += 1

    print(f"=== 测试结果: {passed}/{len(test_cases)} passed ===")

if __name__ == "__main__":
    test_bilingual_questions()