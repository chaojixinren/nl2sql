"""
SQL Execution Node for NL2SQL system.
M2: Executes SQL queries against the database using Function Call.
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from graphs.state import NL2SQLState
from tools.db import db_client


def execute_sql_node(state: NL2SQLState) -> NL2SQLState:
    """
    Execute SQL query against the database.

    M2: Simple execution without retry or validation.
    M4: Will add SQL validation before execution.
    M5: Will add sandbox safety checks.

    Args:
        state: Current NL2SQL state

    Returns:
        Updated state with execution results
    """
    candidate_sql = state.get("candidate_sql")

    print(f"\n=== Execute SQL Node ===")
    print(f"SQL: {candidate_sql}")

    # Check if SQL exists
    if not candidate_sql:
        print("✗ No SQL to execute")
        return {
            **state,
            "execution_result": {
                "ok": False,
                "error": "No SQL query provided",
                "rows": [],
                "columns": [],
                "row_count": 0
            },
            "executed_at": datetime.now().isoformat()
        }

    try:
        # Execute SQL using database client
        result = db_client.query(candidate_sql)

        if result["ok"]:
            print(f"✓ Query successful")
            print(f"  Rows returned: {result['row_count']}")
            print(f"  Columns: {', '.join(result['columns'])}")

            # Show first few rows
            if result['rows']:
                print(f"\n  First row:")
                for key, value in list(result['rows'][0].items())[:5]:
                    print(f"    {key}: {value}")
                if len(result['rows'][0]) > 5:
                    print(f"    ... ({len(result['rows'][0]) - 5} more columns)")
        else:
            print(f"✗ Query failed: {result['error']}")

        return {
            **state,
            "execution_result": result,
            "executed_at": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"✗ Error executing SQL: {e}")

        return {
            **state,
            "execution_result": {
                "ok": False,
                "error": str(e),
                "rows": [],
                "columns": [],
                "row_count": 0
            },
            "executed_at": datetime.now().isoformat()
        }


if __name__ == "__main__":
    """Test SQL execution node"""
    import sys

    print("=== SQL Execution Node Test ===\n")

    # Test cases
    test_cases = [
        {
            "name": "Simple SELECT",
            "sql": "SELECT * FROM Album LIMIT 5"
        },
        {
            "name": "Aggregation",
            "sql": "SELECT COUNT(*) as total FROM Album"
        },
        {
            "name": "JOIN query",
            "sql": """
                SELECT a.Title, ar.Name as Artist
                FROM Album a
                JOIN Artist ar ON a.ArtistId = ar.ArtistId
                LIMIT 5
            """
        },
        {
            "name": "Invalid SQL",
            "sql": "SELECT * FROM NonExistentTable"
        }
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}: {test['name']}")
        print(f"{'='*60}")

        test_state: NL2SQLState = {
            "question": f"Test {i}",
            "session_id": f"test-{i}",
            "timestamp": None,
            "intent": None,
            "candidate_sql": test['sql'],
            "sql_generated_at": datetime.now().isoformat(),
            "execution_result": None,
            "executed_at": None
        }

        result = execute_sql_node(test_state)

        exec_result = result.get('execution_result', {})
        if exec_result.get('ok'):
            print(f"\n✓ Test passed")
        else:
            print(f"\n✗ Test failed (expected for invalid SQL test)")

    print(f"\n{'='*60}")
    print("Test Complete!")
    print(f"{'='*60}")
