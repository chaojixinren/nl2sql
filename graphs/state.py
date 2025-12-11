"""
State definition for NL2SQL LangGraph system.
"""
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime


class NL2SQLState(TypedDict):
    """
    Base state for the NL2SQL graph.

    This state will be extended in future modules with:
    - normalized_question (M7) ✓ Added
    - schema (M3) ✓ Added
    - rag_evidence (M6)
    - candidate_sql (M1) ✓ Added
    - validation (M4) ✓ Added
    - execution (M2) ✓ Added
    - answer (M9) ✓ Added
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


    # SQL Validation (M4)
    validation_result: Optional[Dict[str, Any]]  # 验证结果
    validation_errors: Optional[List[str]]  # 验证错误列表
    validation_passed: Optional[bool]  # 是否通过验证
    
    # SQL Critique and Regeneration (M4)
    critique: Optional[str]  # 错误分析和修复建议
    regeneration_count: Optional[int]  # 重新生成次数（防止无限循环）
    max_regenerations: Optional[int]  # 最大重新生成次数（默认3次）
    
    # Dialog Clarification (M7)
    user_id: Optional[str] # 用户信息（M7 多轮对话需要）
    dialog_history: Optional[List[Dict]] # 对话历史（M7 需要）
    needs_clarification: Optional[bool]  # 是否需要澄清
    clarification_question: Optional[str]  # 澄清问题
    clarification_options: Optional[List[str]]  # 澄清选项（封闭式问题）
    clarification_answer: Optional[str]  # 用户回答
    clarification_count: Optional[int]  # 澄清轮次计数
    max_clarifications: Optional[int]  # 最大澄清次数（默认3次）
    normalized_question: Optional[str]  # 规范化后的问题（包含澄清信息）
    
    # Answer Generation (M9)
    answer: Optional[str]  # 生成的自然语言答案
    answer_generated_at: Optional[str]  # 答案生成时间