"""
Database tools for NL2SQL system.
M2: Implements function call-based database query execution.
"""
import sys
import sqlite3
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import traceback

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from configs.config import config


class DatabaseClient:
    """
    Unified database client supporting multiple database types.

    M2: Currently supports SQLite.
    Future: Will support MySQL, PostgreSQL, etc.
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database client.

        Args:
            db_path: Path to database file. If None, reads from config.
        """
        self.db_type = config.get("db_type", "sqlite")
        self.db_path = db_path or config.get("db_path", "data/chinook.db")

        # Resolve relative path
        if not Path(self.db_path).is_absolute():
            self.db_path = str(project_root / self.db_path)

        # Check if database exists
        if not Path(self.db_path).exists():
            print(f"⚠️  Warning: Database file not found: {self.db_path}")
            print(f"   Please ensure the database file exists.")
        else:
            print(f"✓ Database connected: {self.db_path}")

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

        # Validate SQL
        if not sql or not sql.strip():
            result["error"] = "Empty SQL query"
            return result

        # Security check: only allow SELECT queries in M2
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith("SELECT"):
            result["error"] = "Only SELECT queries are allowed (read-only mode)"
            return result

        try:
            # Connect to database
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column name access
            cursor = conn.cursor()

            # Execute query
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)

            # Fetch results with limit
            raw_rows = cursor.fetchmany(fetch_limit)

            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            # Convert rows to list of dicts
            rows = []
            for row in raw_rows:
                row_dict = {}
                for idx, col_name in enumerate(columns):
                    row_dict[col_name] = row[idx]
                rows.append(row_dict)

            # Close connection
            cursor.close()
            conn.close()

            # Success
            result["ok"] = True
            result["rows"] = rows
            result["columns"] = columns
            result["row_count"] = len(rows)

            return result

        except sqlite3.Error as e:
            result["error"] = f"Database error: {str(e)}"
            return result

        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}\n{traceback.format_exc()}"
            return result

    def get_table_names(self) -> List[str]:
        """
        Get all table names in the database.

        Returns:
            List of table names
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # SQLite query to get table names
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table'
                ORDER BY name
            """)

            tables = [row[0] for row in cursor.fetchall()]

            cursor.close()
            conn.close()

            return tables

        except Exception as e:
            print(f"Error getting table names: {e}")
            return []

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Get schema information for a specific table.

        Args:
            table_name: Name of the table

        Returns:
            Dictionary with table schema info
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get column info
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            schema = {
                "table_name": table_name,
                "columns": [
                    {
                        "name": col[1],
                        "type": col[2],
                        "not_null": bool(col[3]),
                        "primary_key": bool(col[5])
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
        """
        Get schema information for all tables.

        Returns:
            List of table schema dictionaries
        """
        tables = self.get_table_names()
        return [self.get_table_schema(table) for table in tables]

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
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


if __name__ == "__main__":
    """Test database client"""
    print("=== Database Client Test ===\n")

    # Test connection
    print("1. Testing connection...")
    if db_client.test_connection():
        print("✓ Connection successful\n")
    else:
        print("✗ Connection failed\n")
        sys.exit(1)

    # Get table names
    print("2. Getting table names...")
    tables = db_client.get_table_names()
    print(f"Found {len(tables)} tables:")
    for table in tables:
        print(f"  - {table}")
    print()

    # Get schema for first table
    if tables:
        print(f"3. Getting schema for '{tables[0]}'...")
        schema = db_client.get_table_schema(tables[0])
        print(f"Table: {schema['table_name']}")
        print("Columns:")
        for col in schema['columns']:
            pk = " (PK)" if col['primary_key'] else ""
            nn = " NOT NULL" if col['not_null'] else ""
            print(f"  - {col['name']}: {col['type']}{pk}{nn}")
        print()

    # Test query
    print("4. Testing query execution...")
    test_sql = f"SELECT * FROM {tables[0]} LIMIT 5" if tables else "SELECT 1"
    result = db_client.query(test_sql)

    if result["ok"]:
        print(f"✓ Query successful")
        print(f"  Columns: {', '.join(result['columns'])}")
        print(f"  Row count: {result['row_count']}")
        print(f"  First row: {result['rows'][0] if result['rows'] else 'N/A'}")
    else:
        print(f"✗ Query failed: {result['error']}")

    print("\n=== Test Complete ===")
