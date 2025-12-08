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
    - execution (M2) ✓ Added
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

    # 用户信息（M7 多轮对话需要）
    user_id: Optional[str]
    
    # 对话历史（M7 需要）
    dialog_history: Optional[List[Dict]]

    # SQL Validation (M4)
    validation_result: Optional[Dict[str, Any]]  # 验证结果
    validation_errors: Optional[List[str]]  # 验证错误列表
    validation_passed: Optional[bool]  # 是否通过验证
    
    # SQL Critique and Regeneration (M4)
    critique: Optional[str]  # 错误分析和修复建议
    regeneration_count: Optional[int]  # 重新生成次数（防止无限循环）
    max_regenerations: Optional[int]  # 最大重新生成次数（默认3次）
