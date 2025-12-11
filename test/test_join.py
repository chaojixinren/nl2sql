"""
测试 Multi-Table JOIN (M8) 功能
验证多表联结SQL生成功能是否正常工作
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
# 安全修复：test文件在test子目录中，需要使用parent.parent获取项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.schema_manager import schema_manager
from graphs.base_graph import run_query


def test_relationship_graph():
    """测试关系图构建"""
    print("=" * 60)
    print("测试 1: 构建表关系图")
    print("=" * 60)
    
    try:
        graph = schema_manager.build_relationship_graph()
        
        print(f"✓ 关系图构建成功")
        print(f"  包含 {len(graph)} 个表的连接关系")
        
        # 显示一些示例关系
        sample_count = 0
        for table, relations in graph.items():
            if relations and sample_count < 5:
                print(f"\n  表 {table} 的连接关系:")
                for rel in relations[:3]:  # 只显示前3个
                    print(f"    - {rel['direction']}: {table} -> {rel['table']} (via {rel['via']})")
                sample_count += 1
        
        return True
    except Exception as e:
        print(f"✗ 关系图构建失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_find_join_path():
    """测试JOIN路径查找"""
    print("\n" + "=" * 60)
    print("测试 2: 查找JOIN路径")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "两表JOIN - customer和invoice",
            "tables": ["customer", "invoice"],
            "expected_steps": 1
        },
        {
            "name": "三表JOIN - artist, album, track",
            "tables": ["artist", "album", "track"],
            "expected_steps": 2
        },
        {
            "name": "两表JOIN - customer和employee",
            "tables": ["customer", "employee"],
            "expected_steps": 1
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        try:
            join_steps = schema_manager.find_join_path(case["tables"])
            
            if join_steps and len(join_steps) >= case["expected_steps"]:
                print(f"✓ 测试 {i}: {case['name']}")
                print(f"  表: {', '.join(case['tables'])}")
                print(f"  JOIN步骤数: {len(join_steps)}")
                for j, step in enumerate(join_steps, 1):
                    print(f"    {j}. {step['join_type']} JOIN {step['join_table']}")
                    print(f"       条件: {step['condition']}")
                passed += 1
            else:
                print(f"✗ 测试 {i}: {case['name']}")
                print(f"  预期至少 {case['expected_steps']} 个JOIN步骤")
                print(f"  实际: {len(join_steps) if join_steps else 0} 个")
                failed += 1
        except Exception as e:
            print(f"✗ 测试 {i}: {case['name']} - 错误: {e}")
            failed += 1
    
    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_format_join_suggestions():
    """测试JOIN建议格式化"""
    print("\n" + "=" * 60)
    print("测试 3: 格式化JOIN建议")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "两表JOIN建议",
            "tables": ["customer", "invoice"]
        },
        {
            "name": "三表JOIN建议",
            "tables": ["artist", "album", "track"]
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        try:
            suggestions = schema_manager.format_join_suggestions(case["tables"])
            
            if suggestions and len(suggestions) > 0:
                print(f"✓ 测试 {i}: {case['name']}")
                print(f"  表: {', '.join(case['tables'])}")
                print(f"  建议长度: {len(suggestions)} 字符")
                # 显示前200个字符
                preview = suggestions[:200] + "..." if len(suggestions) > 200 else suggestions
                print(f"  预览:\n{preview}\n")
                passed += 1
            else:
                print(f"✗ 测试 {i}: {case['name']} - 未生成建议")
                failed += 1
        except Exception as e:
            print(f"✗ 测试 {i}: {case['name']} - 错误: {e}")
            failed += 1
    
    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_single_table_query():
    """测试单表查询（不应该生成JOIN）"""
    print("\n" + "=" * 60)
    print("测试 4: 单表查询（不应生成JOIN）")
    print("=" * 60)
    
    try:
        # 单表查询不应该生成JOIN建议
        suggestions = schema_manager.format_join_suggestions(["customer"])
        
        if not suggestions or len(suggestions) == 0:
            print("✓ 单表查询正确：未生成JOIN建议")
            return True
        else:
            print("✗ 单表查询错误：生成了JOIN建议")
            return False
    except Exception as e:
        print(f"✗ 测试失败: {e}")
        return False


def test_multi_table_query_integration():
    """测试多表查询集成（需要LLM和数据库）"""
    print("\n" + "=" * 60)
    print("测试 5: 多表查询集成测试（端到端）")
    print("=" * 60)
    print("注意：此测试需要LLM API和数据库连接")
    
    test_cases = [
        {
            "question": "查询每个客户的订单数量",
            "expected_tables": ["customer", "invoice"],
            "description": "两表JOIN查询"
        },
        {
            "question": "查询每个艺术家发行的专辑数量",
            "expected_tables": ["artist", "album"],
            "description": "两表JOIN查询"
        },
        {
            "question": "查询每个专辑的曲目数量",
            "expected_tables": ["album", "track"],
            "description": "两表JOIN查询"
        }
    ]
    
    try:
        from tools.llm_client import llm_client
        from tools.db import db_client
        
        # 测试LLM连接
        test_prompt = "测试"
        llm_client.chat(prompt=test_prompt)
        
        # 测试数据库连接
        if not db_client.test_connection():
            print("⚠️  数据库未连接，跳过集成测试")
            return False
        
        passed = 0
        failed = 0
        
        for i, case in enumerate(test_cases, 1):
            print(f"\n--- 测试 {i}: {case['description']} ---")
            print(f"问题: {case['question']}")
            
            try:
                result = run_query(
                    question=case["question"],
                    session_id=f"test_join_{i}",
                    user_id="test_user"
                )
                
                candidate_sql = result.get("candidate_sql", "")
                relevant_tables = schema_manager.find_relevant_tables(case["question"])
                
                # 检查是否识别了相关表
                if relevant_tables:
                    print(f"✓ 识别到相关表: {', '.join(relevant_tables)}")
                    
                    # 检查是否生成了JOIN
                    has_join = "JOIN" in candidate_sql.upper() if candidate_sql else False
                    
                    if len(relevant_tables) >= 2:
                        if has_join:
                            print(f"✓ 生成了JOIN SQL")
                            print(f"  SQL预览: {candidate_sql[:100]}...")
                            
                            # 检查SQL验证
                            if result.get("validation_passed"):
                                print(f"✓ SQL验证通过")
                                passed += 1
                            else:
                                print(f"⚠️  SQL验证失败: {result.get('validation_errors')}")
                                failed += 1
                        else:
                            print(f"⚠️  多表查询但未生成JOIN")
                            failed += 1
                    else:
                        print(f"✓ 单表查询（不需要JOIN）")
                        passed += 1
                else:
                    print(f"⚠️  未识别到相关表")
                    failed += 1
                    
            except Exception as e:
                print(f"✗ 测试失败: {e}")
                import traceback
                traceback.print_exc()
                failed += 1
        
        print(f"\n结果: {passed} 通过, {failed} 失败")
        return failed == 0
        
    except Exception as e:
        print(f"⚠️  LLM或数据库未配置: {e}")
        print("  跳过集成测试")
        return False


def test_complex_join_scenarios():
    """测试复杂JOIN场景"""
    print("\n" + "=" * 60)
    print("测试 6: 复杂JOIN场景")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "三表JOIN路径",
            "tables": ["customer", "invoice", "invoiceline"],
            "description": "customer -> invoice -> invoiceline"
        },
        {
            "name": "四表JOIN路径",
            "tables": ["artist", "album", "track", "genre"],
            "description": "artist -> album -> track -> genre"
        }
    ]
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        try:
            join_steps = schema_manager.find_join_path(case["tables"])
            
            if join_steps and len(join_steps) >= len(case["tables"]) - 1:
                print(f"✓ 测试 {i}: {case['name']}")
                print(f"  描述: {case['description']}")
                print(f"  JOIN步骤数: {len(join_steps)}")
                for j, step in enumerate(join_steps, 1):
                    print(f"    {j}. {step['join_type']} JOIN {step['join_table']} ON {step['condition']}")
                passed += 1
            else:
                print(f"✗ 测试 {i}: {case['name']}")
                print(f"  预期至少 {len(case['tables']) - 1} 个JOIN步骤")
                print(f"  实际: {len(join_steps) if join_steps else 0} 个")
                failed += 1
        except Exception as e:
            print(f"✗ 测试 {i}: {case['name']} - 错误: {e}")
            failed += 1
    
    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def main():
    """运行所有测试"""
    print("=" * 60)
    print("M8 Multi-Table JOIN 功能测试")
    print("=" * 60)
    
    results = []
    
    # 基础功能测试（不需要LLM和数据库）
    results.append(("构建关系图", test_relationship_graph()))
    results.append(("查找JOIN路径", test_find_join_path()))
    results.append(("格式化JOIN建议", test_format_join_suggestions()))
    results.append(("单表查询", test_single_table_query()))
    results.append(("复杂JOIN场景", test_complex_join_scenarios()))
    
    # 需要LLM和数据库的测试
    print("\n" + "=" * 60)
    print("以下测试需要LLM API和数据库支持")
    print("=" * 60)
    
    results.append(("多表查询集成", test_multi_table_query_integration()))
    
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

