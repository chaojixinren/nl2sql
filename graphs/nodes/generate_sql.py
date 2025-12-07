"""
SQL Generation Node for NL2SQL system.
M1: Uses prompt engineering to generate SQL from natural language.
M3: Enhanced with smart schema matching.
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
from tools.schema_manager import schema_manager  # M3: 新增 Schema Manager
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


def get_database_schema(question: str = "") -> str:
    """
    获取数据库 schema，支持智能匹配 (M3)
    
    Args:
        question: 用户问题（用于智能匹配相关表）
        
    Returns:
        格式化的 schema 文本
    """
    if question:
        # 智能模式：根据问题返回相关的 schema
        return schema_manager.get_smart_schema_for_question(question)
    else:
        # 完整模式：返回所有 schema
        return schema_manager.format_schema_for_prompt()


@monitor_performance
def generate_sql_node(state: NL2SQLState) -> NL2SQLState:
    """
    Generate SQL from natural language question using LLM.
    M3: Now uses smart schema matching based on question.
    """
    question = state.get("question", "")

    print(f"\n=== Generate SQL Node (M3) ===")
    print(f"Question: {question}")

    # Load prompt template
    prompt_template = load_prompt_template("nl2sql")

    # M3: 使用智能 schema（根据问题匹配相关表）
    real_schema = get_database_schema(question)
    
    # 打印匹配到的表信息
    relevant_tables = schema_manager.find_relevant_tables(question)
    if relevant_tables:
        print(f"Relevant tables: {', '.join(relevant_tables)}")

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

