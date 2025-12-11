"""
Answer Builder Node for NL2SQL system.
M9: Converts SQL execution results into natural language answers.
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


def is_numeric(value: Any) -> bool:
    """Check if a value is numeric."""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def extract_key_values(rows: List[Dict], columns: List[str]) -> Dict[str, Any]:
    """
    Extract key statistics from query results.
    
    Args:
        rows: Query result rows
        columns: Column names
        
    Returns:
        Dictionary with key statistics for each numeric column
    """
    if not rows:
        return {}
    
    key_values = {}
    
    for col in columns:
        # Extract non-null values for this column
        values = [row.get(col) for row in rows if row.get(col) is not None]
        
        if not values:
            continue
        
        # Check if all values are numeric
        numeric_values = []
        for v in values:
            if is_numeric(v):
                numeric_values.append(float(v))
        
        if numeric_values:
            key_values[col] = {
                "max": max(numeric_values),
                "min": min(numeric_values),
                "avg": sum(numeric_values) / len(numeric_values),
                "sum": sum(numeric_values),
                "count": len(numeric_values)
            }
        else:
            # For non-numeric columns, count unique values
            unique_values = set(str(v) for v in values)
            key_values[col] = {
                "unique_count": len(unique_values),
                "total_count": len(values)
            }
    
    return key_values


def format_data_summary(execution_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format data summary for answer generation.
    
    Args:
        execution_result: SQL execution result
        
    Returns:
        Formatted data summary
    """
    rows = execution_result.get("rows", [])
    row_count = execution_result.get("row_count", 0)
    columns = execution_result.get("columns", [])
    
    if row_count == 0:
        return {
            "type": "empty",
            "message": "查询结果为空，没有找到匹配的数据。"
        }
    
    if row_count <= 10:
        # Show all data for small result sets
        return {
            "type": "full",
            "data": rows,
            "total_count": row_count,
            "columns": columns
        }
    else:
        # Show sample + statistics for large result sets
        sample_rows = rows[:5]  # First 5 rows as sample
        key_values = extract_key_values(rows, columns)
        
        return {
            "type": "summary",
            "sample": sample_rows,
            "total_count": row_count,
            "columns": columns,
            "key_values": key_values,
            "message": f"查询返回 {row_count} 条记录，以下是前 5 条示例和关键统计信息。"
        }


def format_key_values_summary(key_values: Dict[str, Any]) -> str:
    """
    Format key values into a readable string.
    
    Args:
        key_values: Key values dictionary
        
    Returns:
        Formatted string
    """
    if not key_values:
        return "无关键统计信息"
    
    lines = []
    for col, stats in key_values.items():
        if "max" in stats:
            # Numeric column
            lines.append(f"- {col}:")
            lines.append(f"  - 最大值: {stats['max']:.2f}")
            lines.append(f"  - 最小值: {stats['min']:.2f}")
            lines.append(f"  - 平均值: {stats['avg']:.2f}")
            lines.append(f"  - 总计: {stats['sum']:.2f}")
            lines.append(f"  - 记录数: {stats['count']}")
        else:
            # Non-numeric column
            lines.append(f"- {col}:")
            lines.append(f"  - 唯一值数量: {stats.get('unique_count', 0)}")
            lines.append(f"  - 总记录数: {stats.get('total_count', 0)}")
    
    return "\n".join(lines)


@monitor_performance
def answer_builder_node(state: NL2SQLState) -> NL2SQLState:
    """
    Build natural language answer from SQL execution results.
    M9: Converts SQL results to natural language with conclusion, key values, and SQL provenance.
    
    Args:
        state: Current NL2SQL state
        
    Returns:
        Updated state with generated answer
    """
    question = state.get("question", "")
    candidate_sql = state.get("candidate_sql", "")
    execution_result = state.get("execution_result")
    
    print(f"\n=== Answer Builder Node (M9) ===")
    print(f"Question: {question}")
    
    # Check if execution result exists
    if not execution_result:
        print("⚠️  No execution result available")
        return {
            **state,
            "answer": "无法生成答案：SQL查询尚未执行或执行失败。",
            "answer_generated_at": datetime.now().isoformat()
        }
    
    # Check if execution was successful
    if not execution_result.get("ok"):
        error_msg = execution_result.get("error", "未知错误")
        print(f"⚠️  SQL execution failed: {error_msg}")
        return {
            **state,
            "answer": f"查询执行失败：{error_msg}。请检查SQL查询是否正确，或联系管理员。",
            "answer_generated_at": datetime.now().isoformat()
        }
    
    # Format data summary
    data_summary = format_data_summary(execution_result)
    print(f"Data summary type: {data_summary.get('type')}")
    
    # Extract key values
    rows = execution_result.get("rows", [])
    columns = execution_result.get("columns", [])
    key_values = extract_key_values(rows, columns)
    
    # Load answer prompt template
    try:
        prompt_template = load_prompt_template("answer")
    except FileNotFoundError:
        print("⚠️  Answer prompt template not found, using default")
        # Fallback to simple answer
        if data_summary.get("type") == "empty":
            answer = "查询结果为空，没有找到匹配的数据。"
        elif data_summary.get("type") == "full":
            answer = f"查询成功，返回了 {data_summary.get('total_count', 0)} 条记录。"
        else:
            answer = f"查询成功，返回了 {data_summary.get('total_count', 0)} 条记录。"
        
        return {
            **state,
            "answer": answer,
            "answer_generated_at": datetime.now().isoformat()
        }
    
    # Format data for prompt
    if data_summary.get("type") == "full":
        data_text = f"共 {data_summary.get('total_count', 0)} 条记录：\n"
        for i, row in enumerate(data_summary.get("data", []), 1):
            data_text += f"\n记录 {i}:\n"
            for col, value in row.items():
                data_text += f"  {col}: {value}\n"
    elif data_summary.get("type") == "summary":
        data_text = f"{data_summary.get('message', '')}\n\n"
        data_text += "示例数据（前5条）：\n"
        for i, row in enumerate(data_summary.get("sample", []), 1):
            data_text += f"\n记录 {i}:\n"
            for col, value in row.items():
                data_text += f"  {col}: {value}\n"
        data_text += f"\n关键统计信息：\n{format_key_values_summary(key_values)}"
    else:
        data_text = data_summary.get("message", "无数据")
    
    # Format key values for prompt
    key_values_text = format_key_values_summary(key_values) if key_values else "无关键统计信息"
    
    # Build prompt
    prompt = prompt_template.format(
        question=question,
        sql=candidate_sql,
        data_summary=data_text,
        key_values=key_values_text,
        row_count=execution_result.get("row_count", 0),
        columns=", ".join(columns)
    )
    
    try:
        # Call LLM to generate answer
        print("Calling LLM to generate answer...")
        response = llm_client.chat(prompt=prompt)
        
        # Extract answer (remove markdown if present)
        answer = response.strip()
        if "```" in answer:
            # Remove markdown code blocks
            lines = answer.split("\n")
            answer_lines = []
            in_code_block = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                if not in_code_block:
                    answer_lines.append(line)
            answer = "\n".join(answer_lines).strip()
        
        print(f"✓ Answer generated ({len(answer)} characters)")
        
        return {
            **state,
            "answer": answer,
            "answer_generated_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"✗ Error generating answer: {e}")
        # Fallback to simple answer
        if data_summary.get("type") == "empty":
            answer = "查询结果为空，没有找到匹配的数据。"
        else:
            answer = f"查询成功，返回了 {execution_result.get('row_count', 0)} 条记录。"
        
        return {
            **state,
            "answer": answer,
            "answer_generated_at": datetime.now().isoformat()
        }

