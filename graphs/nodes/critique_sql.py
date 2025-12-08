"""
SQL Critique Node for NL2SQL system.
M4: Analyzes SQL errors and generates fix suggestions.
"""
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from graphs.state import NL2SQLState
from tools.llm_client import llm_client
from graphs.utils.performance import monitor_performance


def load_prompt_template(template_name: str) -> str:
    """Load prompt template from prompts/ directory."""
    template_path = Path(__file__).parent.parent.parent / "prompts" / f"{template_name}.txt"
    
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")
    
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


@monitor_performance
def critique_sql_node(state: NL2SQLState) -> NL2SQLState:
    """
    Analyze SQL errors and generate fix suggestions using LLM.
    
    M4: Provides detailed error analysis and actionable fix suggestions.
    
    Args:
        state: Current NL2SQL state
        
    Returns:
        Updated state with critique
    """
    question = state.get("question", "")
    candidate_sql = state.get("candidate_sql", "")
    validation_errors = state.get("validation_errors", [])
    validation_result = state.get("validation_result", {})
    
    print(f"\n=== Critique SQL Node (M4) ===")
    print(f"Analyzing {len(validation_errors)} error(s)...")
    
    # Load critique prompt template
    try:
        prompt_template = load_prompt_template("critique")
    except FileNotFoundError:
        # Fallback critique if template not found
        critique = f"SQL Validation Errors:\n" + "\n".join(f"- {e}" for e in validation_errors)
        print("⚠️  Critique template not found, using fallback")
        return {
            **state,
            "critique": critique
        }
    
    # Prepare error context
    errors_text = "\n".join(f"- {error}" for error in validation_errors)
    
    # Get schema for context
    from tools.schema_manager import schema_manager
    schema = schema_manager.get_smart_schema_for_question(question)
    
    # Fill in the prompt template
    prompt = prompt_template.format(
        question=question,
        sql=candidate_sql,
        errors=errors_text,
        schema=schema
    )
    
    try:
        # Call LLM for critique
        response = llm_client.chat(prompt=prompt)
        
        print(f"\nCritique generated:")
        print(f"{response[:200]}..." if len(response) > 200 else response)
        
        return {
            **state,
            "critique": response
        }
    
    except Exception as e:
        print(f"✗ Error generating critique: {e}")
        # Fallback critique
        critique = f"SQL Validation Errors:\n{errors_text}\n\nPlease fix the SQL syntax errors above."
        return {
            **state,
            "critique": critique
        }
