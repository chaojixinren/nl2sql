"""
Database tools for NL2SQL system.
M2: Implements function call-based database query execution.
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
        Execute SQL query and return results.

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
        """
        result = {
            "ok": False,
            "rows": [],
            "columns": [],
            "row_count": 0,
            "error": None
        }

        if not sql or not sql.strip():
            result["error"] = "Empty SQL query"
            return result

        sql_upper = sql.strip().upper()
        if not sql_upper.startswith("SELECT"):
            result["error"] = "Only SELECT queries are allowed (read-only mode)"
            return result

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

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
            result["error"] = f"Database error: {str(e)}"
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
