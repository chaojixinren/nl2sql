"""
SQL Generation Node for NL2SQL system.
M1: Uses prompt engineering to generate SQL from natural language.
M3: Enhanced with smart schema matching.
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

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
    M4: Supports regeneration with critique feedback.
    """
    question = state.get("question", "")
    critique = state.get("critique")  # M4: Get critique if available
    regeneration_count = state.get("regeneration_count", 0)  # M4: Track retries

    print(f"\n=== Generate SQL Node (M3/M4) ===")
    print(f"Question: {question}")

    if critique:
        print(f"Regeneration attempt: {regeneration_count + 1}")
        print(f"Using critique feedback for improvement")
    
    # Load prompt template
    prompt_template = load_prompt_template("nl2sql")

    # M3: 使用智能 schema（根据问题匹配相关表）
    real_schema = get_database_schema(question)
    
    # 打印匹配到的表信息
    relevant_tables = schema_manager.find_relevant_tables(question)
    if relevant_tables:
        print(f"Relevant tables: {', '.join(relevant_tables)}")

    # M4: If this is a regeneration, modify the prompt to include critique
    if critique:
        # Add critique section to prompt
        prompt_with_critique = f"""{prompt_template}

## 重要：之前的 SQL 有错误，请根据以下反馈修复

### 错误分析
{critique}

### 要求
请仔细阅读上述错误分析，生成一个语法正确、符合数据库 schema 的 SQL 查询。
确保：
1. SQL 语法完全正确
2. 表名和字段名与 Schema 完全匹配（区分大小写）
3. 修复所有报告的错误
"""
        prompt = prompt_with_critique.format(
            schema=real_schema,
            question=question
        )
    else:
        # Original prompt
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
        
        # M4: Increment regeneration count if this is a retry
        new_regeneration_count = regeneration_count + 1 if critique else 0

        return {
            **state,
            "candidate_sql": candidate_sql,
            "sql_generated_at": datetime.now().isoformat(),
            "regeneration_count": new_regeneration_count,  # M4: Track retries
            "critique": None  # Clear critique after using it
        }

    except Exception as e:
        print(f"\n✗ Error generating SQL: {e}")

        return {
            **state,
            "candidate_sql": None,
            "sql_generated_at": datetime.now().isoformat()
        }

