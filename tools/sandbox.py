"""
SQL Sandbox Security Module for NL2SQL system.
M5: Provides SQL safety checks, row limits, timeout controls, and security logging.
"""
import sys
import re
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def log_security_event(event: Dict[str, Any]) -> None:
    """
    Log security events to security log file.
    
    Args:
        event: Dictionary containing security event information
    """
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "security_log.jsonl"
    
    event["timestamp"] = datetime.now().isoformat()
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def check_sql_safety(
    sql: str,
    forbidden_keywords: Optional[List[str]] = None,
    max_rows: Optional[int] = None
) -> Dict[str, Any]:
    """
    Check SQL for safety violations.
    
    Args:
        sql: SQL query string
        forbidden_keywords: List of forbidden keywords (default: common dangerous keywords)
        max_rows: Maximum allowed rows (for validation, not enforcement)
        
    Returns:
        Dictionary with:
        - ok: bool - whether SQL is safe
        - code: str - error code if unsafe
        - reason: str - reason for blocking
    """
    if not sql or not sql.strip():
        return {
            "ok": False,
            "code": "SANDBOX_EMPTY_SQL",
            "reason": "Empty SQL query"
        }
    
    sql_lower = sql.strip().lower()
    
    # Check 1: Only SELECT statements allowed
    if not sql_lower.startswith("select"):
        return {
            "ok": False,
            "code": "SANDBOX_NON_SELECT",
            "reason": "Only SELECT queries are allowed (read-only mode)"
        }
    
    # Check 2: Dangerous patterns (check before keywords for better error classification)
    dangerous_patterns = [
        (r';\s*(drop|delete|update|insert|alter|create)', "Multiple statements with DML"),
        (r'union\s+.*select', "UNION injection attempt"),
        (r'/\*.*\*/', "SQL comment injection"),
        (r'--\s', "SQL comment injection"),
    ]
    
    for pattern, reason in dangerous_patterns:
        if re.search(pattern, sql_lower, re.IGNORECASE | re.DOTALL):
            return {
                "ok": False,
                "code": "SANDBOX_DANGEROUS_PATTERN",
                "reason": f"Dangerous pattern detected: {reason}"
            }
    
    # Check 3: Forbidden keywords (after pattern check)
    default_forbidden = [
        "insert", "update", "delete", "drop", "alter", "truncate",
        "create", "grant", "revoke", "rename", "replace",
        "into outfile", "load data", "sleep", "benchmark",
        "exec", "execute", "call", "procedure", "function",
        "lock", "unlock", "flush", "kill", "shutdown"
    ]
    
    forbidden = forbidden_keywords if forbidden_keywords is not None else default_forbidden
    
    for keyword in forbidden:
        # Use word boundary matching to avoid false positives
        pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
        if re.search(pattern, sql_lower):
            return {
                "ok": False,
                "code": "SANDBOX_FORBIDDEN_KEYWORD",
                "reason": f"Contains forbidden keyword: '{keyword}'"
            }
    
    return {
        "ok": True,
        "code": None,
        "reason": None
    }


def ensure_limit(sql: str, default_limit: int = 200) -> str:
    """
    Ensure SQL has a LIMIT clause. If not present, add one.
    
    Args:
        sql: SQL query string
        default_limit: Default limit to add if not present
        
    Returns:
        SQL with LIMIT clause
    """
    sql_lower = sql.strip().lower()
    
    # Check if LIMIT already exists
    if " limit " in sql_lower:
        return sql
    
    # Remove trailing semicolon if present
    sql_clean = sql.rstrip().rstrip(";")
    
    # Add LIMIT
    return f"{sql_clean} LIMIT {default_limit};"


def extract_limit(sql: str) -> Optional[int]:
    """
    Extract LIMIT value from SQL if present.
    
    Args:
        sql: SQL query string
        
    Returns:
        LIMIT value or None if not present
    """
    sql_lower = sql.lower()
    
    # Match LIMIT followed by number
    match = re.search(r'limit\s+(\d+)', sql_lower)
    if match:
        return int(match.group(1))
    
    return None


def apply_row_limit(sql: str, max_rows: int, default_limit: int = 200) -> tuple:
    """
    Apply row limit to SQL query.
    
    Args:
        sql: SQL query string
        max_rows: Maximum allowed rows
        default_limit: Default limit if not specified
        
    Returns:
        Tuple of (modified_sql, effective_limit)
    """
    # Extract existing limit
    existing_limit = extract_limit(sql)
    
    if existing_limit:
        # Use the smaller of existing limit and max_rows
        effective_limit = min(existing_limit, max_rows)
        # Replace existing limit
        sql_modified = re.sub(
            r'limit\s+\d+',
            f'LIMIT {effective_limit}',
            sql,
            flags=re.IGNORECASE
        )
        return sql_modified, effective_limit
    else:
        # Add default limit
        effective_limit = min(default_limit, max_rows)
        return ensure_limit(sql, effective_limit), effective_limit

