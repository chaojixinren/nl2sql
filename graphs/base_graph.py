"""
Base LangGraph for NL2SQL system.
M0: Minimal runnable implementation with input/output nodes.
M1: Added SQL generation using prompt engineering.
M2: Added SQL execution using function call.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from langgraph.graph import StateGraph, END
from datetime import datetime
import uuid
import json
from typing import TypedDict, Dict, Any, List, Optional

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from graphs.state import NL2SQLState
from graphs.nodes.generate_sql import generate_sql_node
from graphs.nodes.execute_sql import execute_sql_node
from graphs.nodes.validate_sql import validate_sql_node, should_retry_sql  # M4
from graphs.nodes.critique_sql import critique_sql_node  # M4
from graphs.nodes.clarify import clarify_node, should_ask_clarification  # M7

def log_node(state: NL2SQLState) -> NL2SQLState:
    """
    记录查询日志到文件
    """
    import json
    from pathlib import Path

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "query_log.jsonl"

    log_entry = {
        "session_id": state.get("session_id"),
        "question": state.get("question"),
        "intent": state.get("intent"),
        "timestamp": state.get("timestamp")
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    print(f"✓ Log written to {log_file}")

    return state

def parse_intent_node(state: NL2SQLState) -> NL2SQLState:
    """
    增强版意图解析
    """
    question = state.get("question", "")
    question_lower = question.lower()

    # 1. 识别问题类型
    if any(kw in question_lower for kw in ["统计", "多少", "总计", "count", "sum"]):
        question_type = "aggregation"
    elif any(kw in question_lower for kw in ["排名", "top", "前", "最"]):
        question_type = "ranking"
    elif any(kw in question_lower for kw in ["查询", "显示", "show", "select"]):
        question_type = "select"
    else:
        question_type = "unknown"

    # 2. 提取数量词
    import re
    numbers = re.findall(r'\d+', question)
    limit = int(numbers[0]) if numbers else None

    # 3. 检测时间范围
    has_time = any(kw in question_lower
                   for kw in ["今天", "本月", "本年", "yesterday", "last"])

    intent = {
        "type": question_type,
        "limit": limit,
        "has_time_range": has_time,
        "question_length": len(question),
        "parsed_at": datetime.now().isoformat()
    }

    print(f"\n=== Enhanced Intent ===")
    print(f"Type: {question_type}")
    print(f"Limit: {limit}")
    print(f"Has Time Range: {has_time}")

    return {
        **state,
        "intent": intent,
        "timestamp": datetime.now().isoformat()
    }


def echo_node(state: NL2SQLState) -> NL2SQLState:
    """
    Echo node - prints current state for verification.
    M0: Simple output verification.
    M1: Also shows generated SQL.
    M2: Also shows execution results.
    M7: Also shows clarification questions if needed.
    """
    print(f"\n=== Echo Node ===")
    print(f"Session ID: {state.get('session_id')}")
    if state.get('user_id'):
        print(f"User ID: {state.get('user_id')}")
    print(f"Question: {state.get('question')}")
    print(f"Intent: {json.dumps(state.get('intent', {}), indent=2, ensure_ascii=False)}")

    # M7: Show clarification question if needed
    if state.get('needs_clarification') and state.get('clarification_question'):
        print(f"\n{'='*50}")
        print("⚠️  需要澄清问题")
        print(f"{'='*50}")
        print(f"澄清问题: {state.get('clarification_question')}")
        if state.get('clarification_options'):
            print("\n选项:")
            for i, opt in enumerate(state.get('clarification_options', []), 1):
                print(f"  {i}. {opt}")
        print(f"{'='*50}\n")
        
        # M7: 显示对话历史摘要
        dialog_history = state.get('dialog_history', [])
        if dialog_history:
            print(f"对话历史 ({len(dialog_history)} 条消息)\n")
        
        return state  # 返回状态，等待用户回答

    # M1: Show generated SQL
    candidate_sql = state.get('candidate_sql')
    if candidate_sql:
        print(f"\nGenerated SQL:")
        print(f"  {candidate_sql}")

    # M2: Show execution results
    execution_result = state.get('execution_result')
    if execution_result:
        print(f"\nExecution Result:")
        if execution_result.get('ok'):
            print(f"  ✓ Success")
            print(f"  Rows: {execution_result.get('row_count', 0)}")
            print(f"  Columns: {', '.join(execution_result.get('columns', []))}")
            # Show first row
            if execution_result.get('rows'):
                print(f"  First row: {execution_result['rows'][0]}")
        else:
            print(f"  ✗ Failed: {execution_result.get('error')}")

    # M7: Show dialog history if exists
    dialog_history = state.get('dialog_history', [])
    if dialog_history:
        print(f"\n对话历史 ({len(dialog_history)} 条消息)")

    print(f"Timestamp: {state.get('timestamp')}")
    print(f"\n{'='*50}\n")

    return state


def build_graph() -> StateGraph:
    """
    Build the base NL2SQL graph.
    M0: Minimal graph with parse_intent -> echo
    M1: Added generate_sql node: parse_intent -> generate_sql -> echo
    M2: Added execute_sql node: parse_intent -> generate_sql -> execute_sql -> echo
    M4: Added validation and self-healing: generate -> validate -> (fail) -> critique -> regenerate
    M7: Added clarification node: generate_sql -> clarify -> (clarify/continue) -> validate_sql
    """
    # Create graph
    workflow = StateGraph(NL2SQLState)

    # Add nodes
    workflow.add_node("parse_intent", parse_intent_node)
    workflow.add_node("log", log_node)
    workflow.add_node("generate_sql", generate_sql_node)
    workflow.add_node("clarify", clarify_node)  # M7: New clarification node
    workflow.add_node("validate_sql", validate_sql_node)  # M4: New validation node
    workflow.add_node("critique_sql", critique_sql_node)  # M4: New critique node
    workflow.add_node("execute_sql", execute_sql_node)
    workflow.add_node("echo", echo_node)

    # Define edges
    workflow.set_entry_point("parse_intent")
    workflow.add_edge("parse_intent", "log") 
    workflow.add_edge("log", "generate_sql")
    
    # M7: After generating SQL, check if clarification is needed
    workflow.add_edge("generate_sql", "clarify")
    
    # M7: Conditional edge after clarification
    workflow.add_conditional_edges(
        "clarify",
        should_ask_clarification,  # Decision function
        {
            "clarify": "echo",  # Need clarification, return to user (via echo)
            "regenerate": "generate_sql",  # User answered, regenerate SQL with updated question
            "continue": "validate_sql"  # No clarification needed, continue
        }
    )
    
    # M4: Conditional edge after validation
    workflow.add_conditional_edges(
        "validate_sql",
        should_retry_sql,  # Decision function
        {
            "execute": "execute_sql",  # Validation passed, execute SQL
            "retry": "critique_sql",    # Validation failed, critique and retry
            "fail": "echo"              # Max retries exceeded, show error
        }
    )
    
    # M4: After critique, regenerate SQL
    workflow.add_edge("critique_sql", "generate_sql")  # Loop back to generate
    
    # Original execution flow
    workflow.add_edge("execute_sql", "echo")
    workflow.add_edge("echo", END)

    # Compile graph
    graph = workflow.compile()

    return graph


def run_query(question: str, session_id: str = None, user_id: str = None, clarification_answer: str = None) -> NL2SQLState:
    """
    Run a single query through the graph.
    M4: Now includes validation and self-healing.
    M7: Now supports clarification answers and user_id.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    # Build graph
    graph = build_graph()

    # Initialize state
    initial_state: NL2SQLState = {
        "question": question,
        "session_id": session_id,
        "timestamp": None,
        "intent": None,
        "candidate_sql": None,
        "sql_generated_at": None,
        "execution_result": None,
        "executed_at": None,
        "validation_result": None,      # M4
        "validation_errors": None,      # M4
        "validation_passed": None,      # M4
        "critique": None,               # M4
        "regeneration_count": 0,        # M4
        "max_regenerations": 3,         # M4
        # M7: Use existing fields
        "user_id": user_id,  
        "dialog_history": [],  
        # M7: Clarification fields
        "needs_clarification": None,
        "clarification_question": None,
        "clarification_options": None,
        "clarification_answer": clarification_answer,  # M7: User's answer
        "clarification_count": 0,
        "max_clarifications": 3,
        "normalized_question": None
    }

    # Run graph
    print(f"\n{'='*50}")
    print(f"Starting NL2SQL Graph (M7 - Dialog Clarification)")
    print(f"{'='*50}")

    result = graph.invoke(initial_state)

    return result
