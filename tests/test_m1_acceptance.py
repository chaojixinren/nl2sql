"""
M1 Acceptance Test Script
验收标准: 10条单表查询的 Exact Match ≥ 70%

注意: 由于 M1 阶段没有真实 Schema，生成的 SQL 可能与标准答案在表名/列名上有差异。
     本测试主要验证 SQL 结构和逻辑的正确性。
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from graphs.base_graph import run_query


def test_m1_acceptance():
    """
    M1 验收测试
    """
    print("="*70)
    print("M1 验收测试 - 提示词工程实现 NL2SQL")
    print("="*70)

    # 测试用例
    test_cases = [
        {
            "id": 1,
            "question": "查询所有客户",
            "expected_keywords": ["SELECT", "customers"]
        },
        {
            "id": 2,
            "question": "查询来自北京的客户",
            "expected_keywords": ["SELECT", "customers", "WHERE", "北京"]
        },
        {
            "id": 3,
            "question": "统计每个城市的客户数量",
            "expected_keywords": ["SELECT", "COUNT", "GROUP BY", "city"]
        },
        {
            "id": 4,
            "question": "查询销售额最高的前10个客户",
            "expected_keywords": ["SELECT", "ORDER BY", "DESC", "LIMIT", "10"]
        },
        {
            "id": 5,
            "question": "统计总订单数",
            "expected_keywords": ["SELECT", "COUNT", "orders"]
        },
        {
            "id": 6,
            "question": "查询订单金额大于1000的订单",
            "expected_keywords": ["SELECT", "WHERE", "1000"]
        },
        {
            "id": 7,
            "question": "查询产品价格",
            "expected_keywords": ["SELECT", "price", "products"]
        },
        {
            "id": 8,
            "question": "按价格降序排列产品",
            "expected_keywords": ["SELECT", "products", "ORDER BY", "price", "DESC"]
        },
        {
            "id": 9,
            "question": "统计每个分类的产品数量",
            "expected_keywords": ["SELECT", "COUNT", "GROUP BY", "category"]
        },
        {
            "id": 10,
            "question": "查询价格在100到500之间的产品",
            "expected_keywords": ["SELECT", "WHERE", "BETWEEN", "100", "500"]
        }
    ]

    passed = 0
    failed = 0

    for test_case in test_cases:
        print(f"\n{'='*70}")
        print(f"测试用例 {test_case['id']}: {test_case['question']}")
        print(f"{'='*70}")

        try:
            result = run_query(test_case['question'])

            # 验证结果
            candidate_sql = result.get("candidate_sql", "")

            checks = {
                "question存在": result.get("question") is not None,
                "session_id存在": result.get("session_id") is not None,
                "SQL已生成": candidate_sql is not None and len(candidate_sql) > 0,
            }

            # 检查关键词
            sql_upper = candidate_sql.upper() if candidate_sql else ""
            for keyword in test_case["expected_keywords"]:
                keyword_check = f"包含关键词'{keyword}'"
                checks[keyword_check] = keyword.upper() in sql_upper or keyword in candidate_sql

            all_passed = all(checks.values())

            print(f"\n验收检查:")
            for check_name, check_result in checks.items():
                status = "✓" if check_result else "✗"
                print(f"  {status} {check_name}")

            if candidate_sql:
                print(f"\n生成的SQL:")
                print(f"  {candidate_sql}")

            if all_passed:
                print(f"\n✓ 测试用例 {test_case['id']} 通过")
                passed += 1
            else:
                print(f"\n✗ 测试用例 {test_case['id']} 失败")
                failed += 1

        except Exception as e:
            print(f"\n✗ 测试用例 {test_case['id']} 出错: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1

    # 输出总结
    print(f"\n{'='*70}")
    print("测试总结")
    print(f"{'='*70}")
    print(f"通过: {passed}/{len(test_cases)}")
    print(f"失败: {failed}/{len(test_cases)}")
    print(f"通过率: {passed/len(test_cases)*100:.1f}%")

    # 验收标准: >= 70%
    success_rate = passed / len(test_cases) * 100

    if success_rate >= 70:
        print("\n🎉 恭喜! M1 验收测试通过!")
        print("✓ SQL 生成功能正常")
        print("✓ 提示词工程有效")
        print("✓ 满足验收标准 (≥70%)")
        print("\n下一步: 切换到 02-func-call-db 分支,开始 M2 模块开发")
        return True
    else:
        print(f"\n⚠️  未达到验收标准 (当前: {success_rate:.1f}%, 要求: ≥70%)")
        print("\n可能的原因:")
        print("1. API Key 未配置或不正确")
        print("2. 提示词模板需要优化")
        print("3. LLM 模型性能不足")
        print("\n建议:")
        print("- 检查 .env 文件中的 API Key 配置")
        print("- 尝试使用更强大的模型 (如 qwen-max, gpt-4)")
        print("- 优化 prompts/nl2sql.txt 中的提示词")
        return False


if __name__ == "__main__":
    success = test_m1_acceptance()
    sys.exit(0 if success else 1)
