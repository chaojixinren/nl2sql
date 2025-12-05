"""
State definition for NL2SQL LangGraph system.
"""
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


class NL2SQLState(TypedDict):
    """
    Base state for the NL2SQL graph.

    This state will be extended in future modules with:
    - normalized_question (M7)
    - schema (M3)
    - rag_evidence (M6)
    - candidate_sql (M1) ✓ Added
    - validation (M4)
    - execution (M2)
    - answer (M9)
    - trace (M11)
    """
    # User input
    question: str

    # Metadata
    timestamp: Optional[str]
    session_id: Optional[str]

    # Intent parsing (M0 baseline)
    intent: Optional[Dict[str, Any]]

    # SQL Generation (M1)
    candidate_sql: Optional[str]
    sql_generated_at: Optional[str]

    # SQL Execution (M2)
    execution_result: Optional[Dict[str, Any]]
    executed_at: Optional[str]
