"""
Base LangGraph for NL2SQL system.
M0: Minimal runnable implementation with input/output nodes.
"""
import sys
import os
from langgraph.graph import StateGraph, END
from datetime import datetime
import uuid
import json

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

try:
    from graphs.state import NL2SQLState
except ImportError:
    from state import NL2SQLState


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
    """
    print(f"\n=== Echo Node ===")
    print(f"Session ID: {state.get('session_id')}")
    print(f"Question: {state.get('question')}")
    print(f"Intent: {json.dumps(state.get('intent', {}), indent=2, ensure_ascii=False)}")
    print(f"Timestamp: {state.get('timestamp')}")
    print(f"\n{'='*50}\n")

    return state


def build_graph() -> StateGraph:
    """
    Build the base NL2SQL graph.
    M0: Minimal graph with parse_intent -> echo
    """
    # Create graph
    workflow = StateGraph(NL2SQLState)

    # Add nodes
    workflow.add_node("parse_intent", parse_intent_node)
    workflow.add_node("echo", echo_node)

    # Define edges
    workflow.set_entry_point("parse_intent")
    workflow.add_edge("parse_intent", "echo")
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
        "intent": None
    }

    # Run graph
    print(f"\n{'='*50}")
    print(f"Starting NL2SQL Graph (M0 - Scaffold)")
    print(f"{'='*50}")

    result = graph.invoke(initial_state)

    return result


if __name__ == "__main__":
    """
    M0 Acceptance Test:
    Input a question and verify that intent object is correctly printed.
    """
    # Test cases
    test_questions = [
        "查询所有用户的订单数量",
        "What are the top 10 customers by revenue?",
        "统计每个月的销售额"
    ]

    print("\n" + "="*70)
    print("M0 - NL2SQL Base Graph Test")
    print("="*70)

    for i, question in enumerate(test_questions, 1):
        print(f"\n### Test Case {i} ###")
        result = run_query(question)
        print(f"\nFinal State Keys: {list(result.keys())}")
        print(f"Intent Parsed: {'✓' if result.get('intent') else '✗'}")

    print("\n" + "="*70)
    print("M0 Test Complete!")
    print("="*70)
