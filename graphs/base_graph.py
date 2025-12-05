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

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from graphs.state import NL2SQLState
from graphs.nodes.generate_sql import generate_sql_node
from graphs.nodes.execute_sql import execute_sql_node


def parse_intent_node(state: NL2SQLState) -> NL2SQLState:
    """
    Parse user intent from the question.
    M0: Simple intent extraction with metadata.
    """
    question = state.get("question", "")

    # Simple intent parsing - will be enhanced in future modules
    intent = {
        "type": "query",
        "question_length": len(question),
        "has_keywords": any(kw in question.lower() for kw in ["查询", "多少", "什么", "哪些", "统计", "show", "what", "how many"]),
        "parsed_at": datetime.now().isoformat()
    }

    print(f"\n=== Parse Intent Node ===")
    print(f"Question: {question}")
    print(f"Intent: {json.dumps(intent, indent=2, ensure_ascii=False)}")

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
    """
    print(f"\n=== Echo Node ===")
    print(f"Session ID: {state.get('session_id')}")
    print(f"Question: {state.get('question')}")
    print(f"Intent: {json.dumps(state.get('intent', {}), indent=2, ensure_ascii=False)}")

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

    print(f"Timestamp: {state.get('timestamp')}")
    print(f"\n{'='*50}\n")

    return state


def build_graph() -> StateGraph:
    """
    Build the base NL2SQL graph.
    M0: Minimal graph with parse_intent -> echo
    M1: Added generate_sql node: parse_intent -> generate_sql -> echo
    M2: Added execute_sql node: parse_intent -> generate_sql -> execute_sql -> echo
    """
    # Create graph
    workflow = StateGraph(NL2SQLState)

    # Add nodes
    workflow.add_node("parse_intent", parse_intent_node)
    workflow.add_node("generate_sql", generate_sql_node)  # M1
    workflow.add_node("execute_sql", execute_sql_node)    # M2: New node
    workflow.add_node("echo", echo_node)

    # Define edges
    workflow.set_entry_point("parse_intent")
    workflow.add_edge("parse_intent", "generate_sql")
    workflow.add_edge("generate_sql", "execute_sql")  # M2: Route to SQL execution
    workflow.add_edge("execute_sql", "echo")
    workflow.add_edge("echo", END)

    # Compile graph
    graph = workflow.compile()

    return graph


def run_query(question: str, session_id: str = None) -> NL2SQLState:
    """
    Run a single query through the graph.

    Args:
        question: Natural language question
        session_id: Optional session identifier

    Returns:
        Final state after graph execution
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
        "candidate_sql": None,        # M1
        "sql_generated_at": None,     # M1
        "execution_result": None,     # M2
        "executed_at": None           # M2
    }

    # Run graph
    print(f"\n{'='*50}")
    print(f"Starting NL2SQL Graph (M2 - Function Call DB)")
    print(f"{'='*50}")

    result = graph.invoke(initial_state)

    return result


if __name__ == "__main__":
    """
    M2 Acceptance Test:
    Input a question, generate SQL, and execute against database.
    """
    # Test cases - will work with Chinook database
    test_questions = [
        "Show all albums",
        "How many tracks are there?",
        "What are the top 5 longest tracks?"
    ]

    print("\n" + "="*70)
    print("M2 - NL2SQL with Function Call Test")
    print("="*70)

    for i, question in enumerate(test_questions, 1):
        print(f"\n### Test Case {i} ###")
        result = run_query(question)
        print(f"\nFinal State Keys: {list(result.keys())}")
        print(f"SQL Generated: {'✓' if result.get('candidate_sql') else '✗'}")
        exec_result = result.get('execution_result', {})
        print(f"SQL Executed: {'✓' if exec_result.get('ok') else '✗'}")

    print("\n" + "="*70)
    print("M2 Test Complete!")
    print("="*70)
