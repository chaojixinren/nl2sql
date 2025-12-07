"""
SQL Generation Node for NL2SQL system.
M1: Uses prompt engineering to generate SQL from natural language.
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from graphs.state import NL2SQLState
from tools.llm_client import llm_client
from tools.db import db_client  
from graphs.utils.performance import monitor_performance


def load_prompt_template(template_name: str) -> str:
    """
    Load prompt template from prompts/ directory.

    Args:
        template_name: Name of the template file (without extension)

    Returns:
        Template content as string
    """
    template_path = Path(__file__).parent.parent.parent / "prompts" / f"{template_name}.txt"

    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")

    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def extract_sql_from_response(response: str) -> str:
    """
    Extract SQL from LLM response.
    Handles various response formats (with/without markdown code blocks).

    Args:
        response: LLM response text

    Returns:
        Extracted SQL statement
    """
    # Remove markdown code blocks
    if "```sql" in response:
        # Extract content between ```sql and ```
        start = response.find("```sql") + 6
        end = response.find("```", start)
        sql = response[start:end].strip()
    elif "```" in response:
        # Extract content between ``` and ```
        start = response.find("```") + 3
        end = response.find("```", start)
        sql = response[start:end].strip()
    else:
        # No code blocks, use the entire response
        sql = response.strip()

    # Clean up
    sql = sql.strip()

    # Ensure SQL ends with semicolon
    if not sql.endswith(";"):
        sql += ";"

    return sql


def get_database_schema() -> str:
    """从数据库动态获取真实 schema"""
    schemas = db_client.get_all_schemas()
    
    schema_text = "数据库类型: SQLite\n"
    schema_text += "数据库表结构:\n"
    
    for table in schemas:
        columns = ", ".join([
            f"{col['name']} ({col['type']}{'  PK' if col['primary_key'] else ''})"
            for col in table['columns']
        ])
        schema_text += f"- {table['table_name']} ({columns})\n"
    
    return schema_text


@monitor_performance
def generate_sql_node(state: NL2SQLState) -> NL2SQLState:
    """
    Generate SQL from natural language question using LLM.
    """
    question = state.get("question", "")

    print(f"\n=== Generate SQL Node ===")
    print(f"Question: {question}")

    # Load prompt template
    prompt_template = load_prompt_template("nl2sql")

    # 使用真实的数据库 schema（替换原来的占位符）
    real_schema = get_database_schema()

    # Fill in the prompt template
    prompt = prompt_template.format(
        schema=real_schema,
        question=question
    )

    try:
        # Call LLM
        response = llm_client.chat(prompt=prompt)

        print(f"\nLLM Response:\n{response}")

        # Extract SQL from response
        candidate_sql = extract_sql_from_response(response)

        print(f"\nExtracted SQL:\n{candidate_sql}")

        return {
            **state,
            "candidate_sql": candidate_sql,
            "sql_generated_at": datetime.now().isoformat()
        }

    except Exception as e:
        print(f"\n✗ Error generating SQL: {e}")

        return {
            **state,
            "candidate_sql": None,
            "sql_generated_at": datetime.now().isoformat()
        }


if __name__ == "__main__":
    """Test SQL generation node"""
    import sys

    print("=== SQL Generation Node Test ===\n")

    # Test cases
    test_questions = [
        "查询所有客户",
        "统计每个城市的客户数量",
        "查询销售额最高的前10个客户"
    ]

    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*60}")
        print(f"Test Case {i}")
        print(f"{'='*60}")

        test_state: NL2SQLState = {
            "question": question,
            "session_id": f"test-{i}",
            "timestamp": None,
            "intent": None,
            "candidate_sql": None,
            "sql_generated_at": None
        }

        result = generate_sql_node(test_state)

        print(f"\n✓ SQL Generated:")
        print(f"  {result.get('candidate_sql')}")

    print(f"\n{'='*60}")
    print("Test Complete!")
    print(f"{'='*60}")
