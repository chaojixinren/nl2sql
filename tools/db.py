"""
Database tools for NL2SQL system.
M2: Implements function call-based database query execution.
M5: Adds sandbox security checks and limits.
Supports MySQL only.
"""
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import traceback

import pymysql

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from configs.config import config
from tools.sandbox import check_sql_safety, apply_row_limit, log_security_event


class DatabaseClient:
    """
    MySQL database client for NL2SQL system.
    """

    def __init__(self):
        """Initialize MySQL database client."""
        self.db_type = "mysql"
        self.mysql_config = {
            "host": config.get("mysql_host", "localhost"),
            "port": config.get("mysql_port", 3306),
            "user": config.get("mysql_user", "root"),
            "password": config.get("mysql_password", ""),
            "database": config.get("mysql_database", "chinook"),
            "charset": "utf8mb4"
        }
        print(f"✓ Database configured (MySQL): {self.mysql_config['host']}:{self.mysql_config['port']}/{self.mysql_config['database']}")

    def _get_connection(self):
        """获取 MySQL 数据库连接"""
        return pymysql.connect(**self.mysql_config, cursorclass=pymysql.cursors.DictCursor)

    def query(
        self,
        sql: str,
        params: Optional[Tuple] = None,
        fetch_limit: int = 100
    ) -> Dict[str, Any]:
        """
        Execute SQL query with sandbox security checks.

        M5: Adds security validation, row limits, and timeout controls.

        Args:
            sql: SQL query string
            params: Optional query parameters (for prepared statements)
            fetch_limit: Maximum number of rows to return (default: 100)

        Returns:
            Dictionary with:
            - ok: bool - whether query succeeded
            - rows: list - query results (list of dicts)
            - columns: list - column names
            - row_count: int - number of rows returned
            - error: str - error message if failed
            - code: str - error code if blocked by sandbox (M5)
        """
        result = {
            "ok": False,
            "rows": [],
            "columns": [],
            "row_count": 0,
            "error": None,
            "code": None  # M5: Security error code
        }

        if not sql or not sql.strip():
            result["error"] = "Empty SQL query"
            result["code"] = "SANDBOX_EMPTY_SQL"
            return result

        # M5: Get sandbox configuration
        sandbox_config = config.get_sandbox_config()
        
        # M5: Security check if sandbox is enabled
        if sandbox_config.get("enabled", True):
            safety_check = check_sql_safety(
                sql,
                forbidden_keywords=sandbox_config.get("forbidden_keywords"),
                max_rows=sandbox_config.get("max_rows")
            )
            
            if not safety_check["ok"]:
                # Log security event
                log_security_event({
                    "sql": sql,
                    "code": safety_check["code"],
                    "reason": safety_check["reason"],
                    "action": "blocked"
                })
                
                result["error"] = f"Blocked by sandbox: {safety_check['reason']}"
                result["code"] = safety_check["code"]
                return result

        # M5: Apply row limits
        max_rows = sandbox_config.get("max_rows", 1000)
        default_limit = sandbox_config.get("default_limit", 200)
        
        # Apply LIMIT to SQL if needed
        sql_with_limit, effective_limit = apply_row_limit(sql, max_rows, default_limit)
        
        # Ensure fetch_limit doesn't exceed max_rows
        fetch_limit = min(fetch_limit, max_rows, effective_limit)

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # M5: Set execution timeout (MySQL 5.7+)
            max_execution_ms = sandbox_config.get("max_execution_ms", 3000)
            if max_execution_ms > 0:
                try:
                    cursor.execute(f"SET SESSION max_execution_time = {max_execution_ms}")
                except Exception:
                    # Ignore if max_execution_time is not supported (older MySQL versions)
                    pass

            # Execute query with applied limits
            if params:
                cursor.execute(sql_with_limit, params)
            else:
                cursor.execute(sql_with_limit)

            raw_rows = cursor.fetchmany(fetch_limit)

            # MySQL with DictCursor returns dict rows directly
            columns = list(raw_rows[0].keys()) if raw_rows else []
            rows = list(raw_rows)

            cursor.close()
            conn.close()

            result["ok"] = True
            result["rows"] = rows
            result["columns"] = columns
            result["row_count"] = len(rows)

            return result

        except pymysql.Error as e:
            error_msg = str(e)
            result["error"] = f"Database error: {error_msg}"
            
            # M5: Check if error is due to timeout
            if "max_execution_time" in error_msg.lower() or "timeout" in error_msg.lower():
                result["code"] = "SANDBOX_TIMEOUT"
                log_security_event({
                    "sql": sql_with_limit,
                    "code": "SANDBOX_TIMEOUT",
                    "reason": "Query exceeded maximum execution time",
                    "action": "timeout"
                })
            
            return result

        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            return result

    def get_table_names(self) -> List[str]:
        """Get all table names in the database."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SHOW TABLES")
            tables = [list(row.values())[0] for row in cursor.fetchall()]

            cursor.close()
            conn.close()

            return tables

        except Exception as e:
            print(f"Error getting table names: {e}")
            return []

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get schema information for a specific table."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()
            schema = {
                "table_name": table_name,
                "columns": [
                    {
                        "name": col["Field"],
                        "type": col["Type"],
                        "not_null": col["Null"] == "NO",
                        "primary_key": col["Key"] == "PRI"
                    }
                    for col in columns
                ]
            }

            cursor.close()
            conn.close()

            return schema

        except Exception as e:
            print(f"Error getting schema for {table_name}: {e}")
            return {"table_name": table_name, "columns": []}

    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """Get schema information for all tables."""
        tables = self.get_table_names()
        return [self.get_table_schema(table) for table in tables]

    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False


# Global database client instance
db_client = DatabaseClient()
