"""
SQL Execution Node for NL2SQL system.
M2: Executes SQL queries against the database using Function Call.
M4: Added SQL validation before execution.
M5: Added sandbox safety checks and structured error handling.
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
from graphs.utils.performance import monitor_performance


@monitor_performance
def execute_sql_node(state: NL2SQLState) -> NL2SQLState:
    """
    Execute SQL query against the database with sandbox security.

    M5: Now includes sandbox safety checks and structured error reporting.

    Args:
        state: Current NL2SQL state

    Returns:
        Updated state with execution results
    """
    candidate_sql = state.get("candidate_sql")

    print(f"\n=== Execute SQL Node (M5) ===")
    print(f"SQL: {candidate_sql}")

    # Check if SQL exists
    if not candidate_sql:
        print("✗ No SQL to execute")
        return {
            **state,
            "execution_result": {
                "ok": False,
                "error": "No SQL query provided",
                "code": "SANDBOX_EMPTY_SQL",
                "rows": [],
                "columns": [],
                "row_count": 0
            },
            "executed_at": datetime.now().isoformat()
        }

    try:
        # Execute SQL using database client (with sandbox checks)
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
            # M5: Enhanced error reporting
            error_code = result.get("code", "UNKNOWN_ERROR")
            error_msg = result.get("error", "Unknown error")
            
            print(f"✗ Query failed: {error_msg}")
            
            # M5: Show security error details if blocked by sandbox
            if error_code and error_code.startswith("SANDBOX_"):
                print(f"  Security Code: {error_code}")
                print(f"  Reason: {error_msg}")
                print(f"  ⚠️  This query was blocked by security sandbox")

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
                "code": "EXECUTION_ERROR",
                "rows": [],
                "columns": [],
                "row_count": 0
            },
            "executed_at": datetime.now().isoformat()
        }

