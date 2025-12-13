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
from graphs.nodes.answer_builder import answer_builder_node  # M9

def log_node(state: NL2SQLState) -> NL2SQLState:
    """
    记录查询日志到文件
    """
    import json
    from pathlib import Path

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / "query_log.jsonl"

    # 安全修复：记录日志但不包含敏感信息，用户问题可能包含敏感数据但这是业务需要
    # 建议在生产环境中对日志进行加密或脱敏处理
    question = state.get("question", "")
    # 安全修复：限制日志中问题长度，防止日志文件过大
    question_log = question[:500] if len(question) > 500 else question
    
    log_entry = {
        "session_id": state.get("session_id"),
        "question": question_log,  # 截断后的问题
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


def should_handle_chat_response(state: NL2SQLState) -> str:
    """
    M9.5/M9.75: 统一的上下文处理决策函数
    整合了聊天响应判断和澄清判断
    
    Returns:
        "chat" if LLM returned a chat response instead of SQL
        "clarify" if clarification is needed
        "continue" if it's a valid SQL query and no clarification needed
    """
    # 1. 检查是否是聊天响应
    is_chat_response = state.get("is_chat_response", False)
    if is_chat_response:
        print("💬 检测到聊天响应，直接返回LLM回复")
        return "chat"
    
    # 2. M9.75: 检查是否需要澄清（基于上下文）
    session_id = state.get("session_id")
    if session_id:
        from graphs.utils.context_memory import get_context_manager
        context_manager = get_context_manager(session_id)
        
        clarification_check = context_manager.check_needs_clarification(
            question=state.get("question", ""),
            candidate_sql=state.get("candidate_sql")
        )
        
        if clarification_check.get("needs_clarification", False):
            print(f"⚠️  需要澄清: {clarification_check.get('reasons', [])}")
            return "clarify"
    
    return "continue"


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

    # M9: Show generated natural language answer
    answer = state.get('answer')
    if answer:
        print(f"\n{'='*50}")
        print("📊 自然语言答案 (M9)")
        print(f"{'='*50}")
        print(answer)
        print(f"{'='*50}")

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
    M9: Added answer builder: execute_sql -> answer_builder -> echo
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
    workflow.add_node("answer_builder", answer_builder_node)  # M9: New answer builder node
    workflow.add_node("echo", echo_node)

    # Define edges
    workflow.set_entry_point("parse_intent")
    workflow.add_edge("parse_intent", "log") 
    workflow.add_edge("log", "generate_sql")
    
    # M9.5/M9.75: After generating SQL, unified decision: chat response, clarification, or continue
    workflow.add_conditional_edges(
        "generate_sql",
        should_handle_chat_response,  # M9.5/M9.75: 统一的上下文处理决策
        {
            "chat": "answer_builder",  # 如果是聊天响应，直接生成答案
            "clarify": "clarify",  # 如果需要澄清，进入澄清流程
            "continue": "validate_sql"  # 如果不需要澄清，直接验证SQL
        }
    )
    
    # M7/M9.75: Conditional edge after clarification
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
    
    # M9: After execution, build natural language answer
    workflow.add_edge("execute_sql", "answer_builder")
    workflow.add_edge("answer_builder", "echo")
    workflow.add_edge("echo", END)

    # Compile graph
    graph = workflow.compile()

    return graph


def run_query(question: str, session_id: str = None, user_id: str = None, 
              clarification_answer: str = None, 
              conversation_history: Optional[List[Dict[str, Any]]] = None) -> NL2SQLState:
    """
    Run a single query through the graph.
    M4: Now includes validation and self-healing.
    M7: Now supports clarification answers and user_id.
    M9: Now includes natural language answer generation.
    M9.75: Now supports context memory with conversation history.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    # M9.75: 初始化上下文记忆管理器
    from graphs.utils.context_memory import get_context_manager
    context_manager = get_context_manager(session_id, max_history=10)
    
    # M9.75: 如果有传入的历史，导入到管理器
    if conversation_history:
        for entry in conversation_history:
            context_manager.conversation_history.append(entry)
        context_manager._trim_history()
    
    # M9.75: 添加当前问题到历史（如果还没有添加）
    # 注意：这里先不添加，等确认是查询意图后再添加
    
    # 获取当前历史（用于初始化state）
    current_history = context_manager.get_all_history()

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
        "dialog_history": current_history,  # M9.75: 使用上下文记忆管理器的历史
        # M7: Clarification fields
        "needs_clarification": None,
        "clarification_question": None,
        "clarification_options": None,
        "clarification_answer": clarification_answer,  # M7: User's answer
        "clarification_count": 0,
        "max_clarifications": 3,
        "normalized_question": None,
        # M9: Answer generation fields
        "answer": None,
        "answer_generated_at": None,
        # M9.5: Chat response fields
        "is_chat_response": False,
        "chat_response": None
    }

    # Run graph
    print(f"\n{'='*50}")
    print(f"Starting NL2SQL Graph (M9 - Answer Builder)")
    print(f"{'='*50}")

    result = graph.invoke(initial_state)

    return result
