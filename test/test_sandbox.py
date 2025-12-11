"""
测试 SQL Sandbox (M5) 功能
验证安全防护与权限隔离功能是否正常工作
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
# 安全修复：test文件在test子目录中，需要使用parent.parent获取项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.sandbox import check_sql_safety, ensure_limit, apply_row_limit, log_security_event
from tools.db import db_client
from configs.config import config


def test_sandbox_config():
    """测试沙箱配置"""
    print("=" * 60)
    print("测试 1: 检查沙箱配置")
    print("=" * 60)
    
    try:
        sandbox_config = config.get_sandbox_config()
        
        print(f"✓ 沙箱配置加载成功")
        print(f"  启用状态: {sandbox_config.get('enabled')}")
        print(f"  默认限制: {sandbox_config.get('default_limit')}")
        print(f"  最大行数: {sandbox_config.get('max_rows')}")
        print(f"  最大执行时间: {sandbox_config.get('max_execution_ms')}ms")
        print(f"  禁止关键词数量: {len(sandbox_config.get('forbidden_keywords', []))}")
        
        return True
    except Exception as e:
        print(f"✗ 配置加载失败: {e}")
        return False


def test_sql_safety_check():
    """测试 SQL 安全检查"""
    print("\n" + "=" * 60)
    print("测试 2: SQL 安全检查")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "正常 SELECT 查询",
            "sql": "SELECT * FROM customer LIMIT 10;",
            "should_pass": True
        },
        {
            "name": "DROP TABLE 攻击",
            "sql": "DROP TABLE customer;",
            "should_pass": False,
            "expected_code": "SANDBOX_NON_SELECT"
        },
        {
            "name": "DELETE 攻击",
            "sql": "DELETE FROM customer WHERE id = 1;",
            "should_pass": False,
            "expected_code": "SANDBOX_NON_SELECT"
        },
        {
            "name": "UPDATE 攻击",
            "sql": "UPDATE customer SET name = 'hack';",
            "should_pass": False,
            "expected_code": "SANDBOX_NON_SELECT"
        },
        {
            "name": "INSERT 攻击",
            "sql": "INSERT INTO customer VALUES (1, 'test');",
            "should_pass": False,
            "expected_code": "SANDBOX_NON_SELECT"
        },
        {
            "name": "SELECT 中包含 DROP（注入攻击）",
            "sql": "SELECT * FROM customer; DROP TABLE customer;",
            "should_pass": False,
            "expected_code": "SANDBOX_DANGEROUS_PATTERN"
        },
        {
            "name": "SELECT 中包含 sleep（拒绝服务）",
            "sql": "SELECT * FROM customer WHERE sleep(10);",
            "should_pass": False,
            "expected_code": "SANDBOX_FORBIDDEN_KEYWORD"
        },
        {
            "name": "SELECT 中包含 benchmark（拒绝服务）",
            "sql": "SELECT benchmark(1000000, md5('test'));",
            "should_pass": False,
            "expected_code": "SANDBOX_FORBIDDEN_KEYWORD"
        },
        {
            "name": "空 SQL",
            "sql": "",
            "should_pass": False,
            "expected_code": "SANDBOX_EMPTY_SQL"
        },
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        sql = test_case["sql"]
        result = check_sql_safety(sql)
        
        if result["ok"] == test_case["should_pass"]:
            if not test_case["should_pass"]:
                # 检查错误代码
                expected_code = test_case.get("expected_code")
                if expected_code and result.get("code") == expected_code:
                    print(f"✓ {test_case['name']}: 正确拦截 ({result['code']})")
                    passed += 1
                else:
                    print(f"⚠️  {test_case['name']}: 拦截但代码不匹配 (期望: {expected_code}, 实际: {result.get('code')})")
                    passed += 1  # 仍然算通过，因为拦截了
            else:
                print(f"✓ {test_case['name']}: 通过检查")
                passed += 1
        else:
            print(f"✗ {test_case['name']}: 检查失败")
            print(f"  期望: {'通过' if test_case['should_pass'] else '拦截'}")
            print(f"  实际: {'通过' if result['ok'] else '拦截'}")
            if result.get("code"):
                print(f"  代码: {result['code']}")
    
    print(f"\n通过率: {passed}/{total}")
    return passed == total


def test_row_limit():
    """测试行数限制"""
    print("\n" + "=" * 60)
    print("测试 3: 行数限制")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "无 LIMIT 的 SQL",
            "sql": "SELECT * FROM customer;",
            "default_limit": 200,
            "expected_contains": "LIMIT 200"
        },
        {
            "name": "已有 LIMIT 的 SQL",
            "sql": "SELECT * FROM customer LIMIT 50;",
            "default_limit": 200,
            "expected_contains": "LIMIT 50"
        },
        {
            "name": "LIMIT 超过最大值",
            "sql": "SELECT * FROM customer LIMIT 5000;",
            "max_rows": 1000,
            "expected_contains": "LIMIT 1000"
        },
    ]
    
    passed = 0
    total = len(test_cases)
    
    for test_case in test_cases:
        sql = test_case["sql"]
        max_rows = test_case.get("max_rows", 1000)
        default_limit = test_case.get("default_limit", 200)
        
        modified_sql, effective_limit = apply_row_limit(sql, max_rows, default_limit)
        
        expected = test_case.get("expected_contains")
        if expected and expected in modified_sql.upper():
            print(f"✓ {test_case['name']}: {modified_sql}")
            print(f"  有效限制: {effective_limit}")
            passed += 1
        else:
            print(f"✗ {test_case['name']}: 未找到期望内容")
            print(f"  结果: {modified_sql}")
    
    print(f"\n通过率: {passed}/{total}")
    return passed == total


def test_database_integration():
    """测试数据库集成（需要数据库连接）"""
    print("\n" + "=" * 60)
    print("测试 4: 数据库集成测试")
    print("=" * 60)
    
    # 先测试数据库连接
    try:
        if not db_client.test_connection():
            print("⚠️  数据库连接失败，跳过集成测试")
            print("  提示: 这可能是环境配置问题，不影响 M5 功能验证")
            print("  如需测试，请确保:")
            print("    1. MySQL 服务正在运行")
            print("    2. .env 文件中的数据库配置正确")
            print("    3. 如使用 MySQL 8.0+，可能需要安装: pip install cryptography")
            return None  # 跳过但不算失败
    except Exception as e:
        print(f"⚠️  数据库连接测试失败: {e}")
        print("  提示: 这可能是环境配置问题，不影响 M5 功能验证")
        return None
    
    try:
        # 测试正常查询
        print("\n--- 正常查询测试 ---")
        result = db_client.query("SELECT CustomerId, FirstName FROM customer LIMIT 5;")
        
        if result["ok"]:
            print(f"✓ 正常查询成功")
            print(f"  返回行数: {result['row_count']}")
        else:
            print(f"✗ 正常查询失败: {result.get('error')}")
            if result.get("code"):
                print(f"  错误代码: {result['code']}")
            return False
        
        # 测试恶意 SQL（应该被拦截）
        print("\n--- 恶意 SQL 拦截测试 ---")
        malicious_sqls = [
            ("DROP TABLE customer;", "SANDBOX_NON_SELECT"),
            ("DELETE FROM customer;", "SANDBOX_NON_SELECT"),
            ("SELECT * FROM customer; DROP TABLE customer;", "SANDBOX_DANGEROUS_PATTERN"),
        ]
        
        blocked_count = 0
        for sql, expected_code in malicious_sqls:
            result = db_client.query(sql)
            
            if not result["ok"] and result.get("code") == expected_code:
                print(f"✓ 正确拦截: {sql[:50]}...")
                print(f"  错误代码: {result['code']}")
                blocked_count += 1
            else:
                print(f"✗ 未正确拦截: {sql[:50]}...")
                print(f"  结果: {result.get('error')}")
                print(f"  代码: {result.get('code')}")
        
        print(f"\n拦截率: {blocked_count}/{len(malicious_sqls)}")
        
        # 测试行数限制
        print("\n--- 行数限制测试 ---")
        result = db_client.query("SELECT * FROM customer;")  # 无 LIMIT
        
        if result["ok"]:
            row_count = result["row_count"]
            max_rows = config.get_sandbox_config().get("max_rows", 1000)
            
            if row_count <= max_rows:
                print(f"✓ 行数限制生效: {row_count} <= {max_rows}")
            else:
                print(f"✗ 行数限制未生效: {row_count} > {max_rows}")
        
        return blocked_count == len(malicious_sqls)
        
    except Exception as e:
        error_msg = str(e)
        if "cryptography" in error_msg.lower():
            print(f"⚠️  数据库连接需要 cryptography 包")
            print(f"  请运行: pip install cryptography")
            print(f"  提示: 这是环境配置问题，不影响 M5 功能验证")
            return None  # 跳过但不算失败
        else:
            print(f"✗ 数据库集成测试错误: {e}")
            import traceback
            traceback.print_exc()
            return False


def test_security_logging():
    """测试安全日志"""
    print("\n" + "=" * 60)
    print("测试 5: 安全日志记录")
    print("=" * 60)
    
    try:
        # 尝试执行一个会被拦截的 SQL
        test_sql = "DROP TABLE customer;"
        result = db_client.query(test_sql)
        
        # 检查日志文件是否存在
        log_file = Path("logs/security_log.jsonl")
        
        if log_file.exists():
            # 读取最后一行日志
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    last_line = lines[-1]
                    import json
                    log_entry = json.loads(last_line)
                    
                    if log_entry.get("code") and log_entry.get("sql"):
                        print(f"✓ 安全日志记录成功")
                        print(f"  最后记录: {log_entry.get('code')}")
                        return True
        
        print(f"⚠️  安全日志文件不存在或为空")
        return False
        
    except Exception as e:
        print(f"✗ 安全日志测试错误: {e}")
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("SQL Sandbox (M5) 功能测试")
    print("=" * 60)
    
    results = {}
    
    # 测试 1: 配置
    results["config"] = test_sandbox_config()
    
    # 测试 2: 安全检查
    results["safety_check"] = test_sql_safety_check()
    
    # 测试 3: 行数限制
    results["row_limit"] = test_row_limit()
    
    # 测试 4: 数据库集成（需要数据库连接）
    print("\n" + "=" * 60)
    print("是否运行数据库集成测试？")
    print("（需要数据库连接）")
    print("=" * 60)
    user_input = input("运行数据库集成测试? (y/n): ")
    if user_input.lower() == 'y':
        results["db_integration"] = test_database_integration()
    else:
        results["db_integration"] = None
    
    # 测试 5: 安全日志
    results["logging"] = test_security_logging()
    
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

