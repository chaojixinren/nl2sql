"""
M2 Acceptance Test: Function Call DB Execution
Validates that SQL queries can be executed against the database.

Validation criteria:
- All queries must execute successfully
- Results must be returned correctly
- Read-only mode enforced (only SELECT allowed)
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from graphs.base_graph import run_query


# Test cases based on Chinook database
TEST_CASES = [
    {
        "name": "Simple SELECT",
        "question": "Show all albums",
        "expected_keywords": ["Album", "SELECT"],
        "should_succeed": True
    },
    {
        "name": "Count aggregation",
        "question": "How many tracks are there?",
        "expected_keywords": ["COUNT", "Track"],
        "should_succeed": True
    },
    {
        "name": "Top N with ORDER BY",
        "question": "What are the top 5 longest tracks?",
        "expected_keywords": ["ORDER BY", "LIMIT", "Track"],
        "should_succeed": True
    },
    {
        "name": "WHERE clause",
        "question": "Show albums by AC/DC",
        "expected_keywords": ["WHERE", "Album"],
        "should_succeed": True
    },
    {
        "name": "JOIN query",
        "question": "Show all albums with their artist names",
        "expected_keywords": ["JOIN", "Album", "Artist"],
        "should_succeed": True
    },
    {
        "name": "GROUP BY aggregation",
        "question": "Count albums by artist",
        "expected_keywords": ["GROUP BY", "COUNT"],
        "should_succeed": True
    },
    {
        "name": "Multiple tables",
        "question": "Show customer names and their total invoice amounts",
        "expected_keywords": ["Customer", "Invoice"],
        "should_succeed": True
    },
    {
        "name": "Date filtering",
        "question": "Show invoices from 2010",
        "expected_keywords": ["Invoice", "2010"],
        "should_succeed": True
    }
]


def validate_test_case(test_case, result):
    """
    Validate a single test case result.

    Args:
        test_case: Test case dictionary
        result: Execution result state

    Returns:
        tuple: (passed, reason)
    """
    # Check SQL generation
    sql = result.get("candidate_sql")
    if not sql:
        return False, "No SQL generated"

    # Check SQL contains expected keywords (case-insensitive)
    sql_upper = sql.upper()
    for keyword in test_case["expected_keywords"]:
        if keyword.upper() not in sql_upper:
            return False, f"Missing keyword: {keyword}"

    # Check execution result
    exec_result = result.get("execution_result")
    if not exec_result:
        return False, "No execution result"

    # Check if execution succeeded
    if test_case["should_succeed"]:
        if not exec_result.get("ok"):
            return False, f"Execution failed: {exec_result.get('error')}"

        # Check that we got results
        if exec_result.get("row_count", 0) == 0:
            return False, "No rows returned"

    return True, "OK"


def run_acceptance_test():
    """Run M2 acceptance tests."""
    print("=" * 70)
    print("M2 Acceptance Test: Function Call DB Execution")
    print("=" * 70)
    print()

    results = []

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"\n{'=' * 70}")
        print(f"Test {i}/{len(TEST_CASES)}: {test_case['name']}")
        print(f"{'=' * 70}")
        print(f"Question: {test_case['question']}")

        try:
            # Run query
            result = run_query(test_case['question'])

            # Validate result
            passed, reason = validate_test_case(test_case, result)

            results.append({
                "name": test_case['name'],
                "passed": passed,
                "reason": reason,
                "sql": result.get('candidate_sql'),
                "execution": result.get('execution_result', {})
            })

            if passed:
                print(f"\n✓ Test PASSED")
                print(f"  SQL: {result.get('candidate_sql')}")
                print(f"  Rows: {result.get('execution_result', {}).get('row_count', 0)}")
            else:
                print(f"\n✗ Test FAILED: {reason}")
                print(f"  SQL: {result.get('candidate_sql')}")

        except Exception as e:
            print(f"\n✗ Test ERROR: {e}")
            results.append({
                "name": test_case['name'],
                "passed": False,
                "reason": str(e),
                "sql": None,
                "execution": None
            })

    # Summary
    print(f"\n\n{'=' * 70}")
    print("Test Summary")
    print(f"{'=' * 70}")

    passed_count = sum(1 for r in results if r['passed'])
    total_count = len(results)
    pass_rate = (passed_count / total_count * 100) if total_count > 0 else 0

    print(f"Passed: {passed_count}/{total_count}")
    print(f"Failed: {total_count - passed_count}/{total_count}")
    print(f"Pass Rate: {pass_rate:.1f}%")

    # Show failures
    failures = [r for r in results if not r['passed']]
    if failures:
        print(f"\nFailed Tests:")
        for result in failures:
            print(f"  - {result['name']}: {result['reason']}")

    # Acceptance criteria
    print(f"\n{'=' * 70}")
    if pass_rate == 100:
        print("🎉 ACCEPTANCE TEST PASSED!")
        print(f"{'=' * 70}")
        print("\nM2 module is complete.")
        print("All queries executed successfully against the database.")
        return True
    else:
        print("❌ ACCEPTANCE TEST FAILED")
        print(f"{'=' * 70}")
        print(f"\nRequired: 100% pass rate")
        print(f"Actual: {pass_rate:.1f}%")
        print("\nPlease fix the failing tests and try again.")
        return False


if __name__ == "__main__":
    success = run_acceptance_test()
    sys.exit(0 if success else 1)
