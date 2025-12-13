"""
Dialog Clarification Node for NL2SQL system.
M7: Supports multi-turn dialog and clarification questions.
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
from tools.schema_manager import schema_manager
from graphs.utils.performance import monitor_performance


def load_prompt_template(template_name: str) -> str:
    """Load prompt template from prompts/ directory."""
    template_path = Path(__file__).parent.parent.parent / "prompts" / f"{template_name}.txt"
    
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")
    
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()


def check_if_needs_clarification(question: str, candidate_sql: Optional[str] = None) -> Dict[str, Any]:
    """
    判断是否需要澄清的判据
    
    判据包括：
    1. 问题模糊（缺少关键信息：时间范围、具体字段、聚合方式等）
    2. 存在歧义（多个可能的解释）
    3. 表/字段匹配不明确
    4. 聚合函数不明确
    
    Returns:
        {
            "needs_clarification": bool,
            "reasons": List[str],  # 需要澄清的原因
            "clarification_type": str  # 澄清类型：time_range, field, aggregation, ambiguity等
        }
    """
    question_lower = question.lower()
    reasons = []
    clarification_type = None
    
    # 明确的时间范围关键词（如果包含这些，时间范围已明确）
    explicit_time_keywords = ["最近一周", "最近一个月", "最近三个月", "最近一年", 
                              "本月", "今年", "去年", "上个月", "上周", "昨天", "今天",
                              "2024", "2023", "2022", "2021", "年", "月", "日", "周"]
    
    # 明确的聚合方式关键词（如果包含这些，聚合方式已明确）
    explicit_aggregation_keywords = ["总数", "总和", "总金额", "总数量", "平均", "平均值", 
                                     "最大", "最小", "最多", "最少", "count", "sum", "avg", 
                                     "max", "min", "数量", "金额", "销售额"]
    
    # 明确的字段关键词（如果包含这些，字段需求已明确）
    explicit_field_keywords = ["ID", "名称", "日期", "金额", "数量", "地址", "城市", "国家",
                              "客户", "订单", "产品", "员工", "发票"]
    
    # 判据1: 缺少时间范围（但问题可能涉及时间）
    # 检查是否包含时间相关词汇
    has_time_related = any(kw in question for kw in ["时间", "日期", "什么时候", "何时", "最近"])
    # 检查是否有明确的时间范围
    has_explicit_time = any(kw in question for kw in explicit_time_keywords)
    
    if has_time_related and not has_explicit_time:
        reasons.append("问题涉及时间但缺少具体时间范围")
        clarification_type = "time_range"
    
    # 判据2: 模糊的聚合需求
    # 检查是否包含聚合相关词汇
    has_aggregation_related = any(kw in question_lower for kw in ["统计", "汇总", "分析", "查看", "查询"])
    # 检查是否有明确的聚合方式
    has_explicit_aggregation = any(kw in question for kw in explicit_aggregation_keywords)
    
    if has_aggregation_related and not has_explicit_aggregation:
        # 但如果问题已经非常具体（如"查询订单ID"），不需要澄清
        has_specific_query = any(kw in question for kw in ["查询", "显示", "列出", "查找"]) and \
                           any(kw in question for kw in explicit_field_keywords)
        if not has_specific_query:
            reasons.append("需要聚合但未明确聚合方式（数量/总和/平均等）")
            if not clarification_type:
                clarification_type = "aggregation"
    
    # 判据3: 模糊的字段需求
    # 检查是否包含模糊字段词汇
    has_vague_field = any(kw in question_lower for kw in ["信息", "数据", "详情", "情况"])
    # 检查是否有明确的字段或查询意图
    has_explicit_field = any(kw in question for kw in explicit_field_keywords) or \
                        any(kw in question for kw in ["哪些", "什么", "哪个", "哪"])
    
    # 如果问题已经包含明确的时间范围或聚合方式，且查询的是常见实体（客户、订单等），不需要澄清字段
    has_common_entity = any(kw in question for kw in ["客户", "订单", "产品", "员工", "发票", "销售", "购买"])
    is_sufficiently_specific = has_explicit_time or has_explicit_aggregation or has_common_entity
    
    if has_vague_field and not has_explicit_field and not is_sufficiently_specific:
        reasons.append("字段需求不明确")
        if not clarification_type:
            clarification_type = "field"
    
    # 判据4: 存在歧义词汇
    ambiguous_keywords = ["最好", "最差", "重要", "主要", "相关"]
    if any(kw in question for kw in ambiguous_keywords):
        reasons.append("存在可能产生歧义的词汇")
        if not clarification_type:
            clarification_type = "ambiguity"
    
    needs_clarification = len(reasons) > 0
    
    return {
        "needs_clarification": needs_clarification,
        "reasons": reasons,
        "clarification_type": clarification_type or "general"
    }


@monitor_performance
def clarify_node(state: NL2SQLState) -> NL2SQLState:
    """
    澄清节点：判断是否需要澄清，如果需要则生成澄清问题
    
    M7: Supports multi-turn dialog and clarification questions.
    使用已有的 dialog_history 字段维护对话历史。
    """
    question = state.get("question", "")
    candidate_sql = state.get("candidate_sql")
    clarification_answer = state.get("clarification_answer")  # 用户对澄清问题的回答
    clarification_count = state.get("clarification_count", 0)
    max_clarifications = state.get("max_clarifications", 3)
    
    # M7: 使用已有的 dialog_history 字段
    # M9.75: 使用上下文记忆管理器
    session_id = state.get("session_id")
    from graphs.utils.context_memory import get_context_manager
    context_manager = get_context_manager(session_id) if session_id else None
    
    dialog_history = state.get("dialog_history") or []
    user_id = state.get("user_id")  # M7: 使用已有的 user_id 字段
    
    print(f"\n=== Clarify Node (M7/M9.75) ===")
    print(f"Question: {question}")
    if user_id:
        print(f"User ID: {user_id}")
    print(f"Clarification count: {clarification_count}")
    print(f"Dialog history length: {len(dialog_history)}")
    
    # 如果用户已经回答了澄清问题，更新问题并继续
    if clarification_answer:
        print(f"User answered: {clarification_answer}")
        
        # 更新问题：将澄清信息整合到原问题中
        # 从对话历史中找到原始问题
        original_question = question
        for entry in reversed(dialog_history):
            if entry.get("role") == "user" and entry.get("content"):
                # 移除之前可能添加的澄清信息
                content = entry["content"]
                if "（" in content and "）" in content:
                    original_question = content.split("（")[0]
                else:
                    original_question = content
                break
        
        normalized_question = f"{original_question}（{clarification_answer}）"
        
        # M9.75: 使用上下文记忆管理器更新对话历史
        if context_manager:
            context_manager.add_clarification_answer(clarification_answer)
            updated_history = context_manager.get_all_history()
        else:
            # 回退到原有逻辑
            updated_history = dialog_history.copy()
            updated_history.append({
                "role": "assistant",
                "content": state.get("clarification_question", ""),
                "timestamp": datetime.now().isoformat(),
                "type": "clarification"
            })
            updated_history.append({
                "role": "user",
                "content": clarification_answer,
                "timestamp": datetime.now().isoformat(),
                "type": "clarification_answer"
            })
        
        return {
            **state,
            "question": normalized_question,  # 更新问题
            "normalized_question": normalized_question,
            "candidate_sql": None,  # 清空旧的SQL，需要重新生成
            "clarification_answer": None,  # 清空回答
            "clarification_question": None,  # 清空澄清问题
            "needs_clarification": False,  # 不再需要澄清
            "dialog_history": updated_history  # 更新对话历史
        }
    
    # 检查是否需要澄清
    clarification_check = check_if_needs_clarification(question, candidate_sql)
    needs_clarification = clarification_check["needs_clarification"]
    
    # 如果超过最大澄清次数，不再澄清
    if clarification_count >= max_clarifications:
        print(f"⚠️  已达到最大澄清次数 ({max_clarifications})，跳过澄清")
        needs_clarification = False
    
    if not needs_clarification:
        print("✓ No clarification needed")
        return {
            **state,
            "needs_clarification": False
        }
    
    # 需要澄清，生成澄清问题
    print(f"⚠️  Needs clarification: {clarification_check['reasons']}")
    
    try:
        # 加载澄清prompt模板
        prompt_template = load_prompt_template("clarify")
        
        # 获取schema用于上下文
        schema = schema_manager.get_smart_schema_for_question(question)
        
        # 构建prompt
        reasons_text = "\n".join(f"- {r}" for r in clarification_check["reasons"])
        clarification_type = clarification_check["clarification_type"]
        
        # M9.75: 使用上下文记忆管理器格式化历史上下文
        if context_manager:
            history_text = context_manager.format_context_for_clarification(
                question=question,
                candidate_sql=candidate_sql
            )
        else:
            # 回退到原有逻辑
            history_text = ""
            if dialog_history:
                history_text = "\n## 对话历史\n"
                for entry in dialog_history[-5:]:  # 只取最近5轮
                    role = entry.get("role", "unknown")
                    content = entry.get("content", "")
                    timestamp = entry.get("timestamp", "")
                    history_text += f"[{timestamp}] {role}: {content}\n"
        
        prompt = prompt_template.format(
            question=question,
            schema=schema,
            reasons=reasons_text,
            clarification_type=clarification_type,
            dialog_history=history_text
        )
        
        # 调用LLM生成澄清问题
        response = llm_client.chat(prompt=prompt)
        
        # 解析LLM响应，提取澄清问题和选项
        clarification_question, clarification_options = parse_clarification_response(response)
        
        print(f"\nGenerated clarification question:")
        print(f"  Q: {clarification_question}")
        if clarification_options:
            print(f"  Options:")
            for i, opt in enumerate(clarification_options, 1):
                print(f"    {i}. {opt}")
        
        # M9.75: 使用上下文记忆管理器更新对话历史
        if context_manager:
            context_manager.add_clarification(
                clarification_question=clarification_question,
                options=clarification_options,
                reasons=clarification_check["reasons"]
            )
            updated_history = context_manager.get_all_history()
        else:
            # 回退到原有逻辑
            updated_history = dialog_history.copy()
            updated_history.append({
                "role": "user",
                "content": question,
                "timestamp": datetime.now().isoformat(),
                "type": "question"
            })
            updated_history.append({
                "role": "assistant",
                "content": clarification_question,
                "timestamp": datetime.now().isoformat(),
                "type": "clarification",
                "options": clarification_options
            })
        
        return {
            **state,
            "needs_clarification": True,
            "clarification_question": clarification_question,
            "clarification_options": clarification_options,
            "clarification_count": clarification_count + 1,
            "dialog_history": updated_history  # 更新对话历史
        }
        
    except Exception as e:
        print(f"✗ Error generating clarification: {e}")
        import traceback
        traceback.print_exc()
        # 如果生成澄清问题失败，继续执行（不阻塞流程）
        return {
            **state,
            "needs_clarification": False
        }


def parse_clarification_response(response: str) -> tuple[str, List[str]]:
    """
    解析LLM响应，提取澄清问题和选项
    
    Expected format:
    问题: [澄清问题]
    
    选项:
    1. [选项1]
    2. [选项2]
    3. [选项3]
    
    Returns:
        (clarification_question, clarification_options)
    """
    import re
    
    # 提取问题
    question_match = re.search(r'问题[：:]\s*(.+?)(?:\n|选项|$)', response, re.DOTALL)
    if not question_match:
        # 尝试其他格式
        question_match = re.search(r'澄清问题[：:]\s*(.+?)(?:\n|选项|$)', response, re.DOTALL)
    
    clarification_question = question_match.group(1).strip() if question_match else "请提供更多信息以帮助我理解您的需求。"
    
    # 提取选项
    options = []
    # 匹配编号列表：1. 2. 3. 或 1) 2) 3)
    option_pattern = r'[0-9]+[\.\)、]\s*(.+?)(?:\n|$)'
    option_matches = re.findall(option_pattern, response)
    
    if option_matches:
        options = [opt.strip() for opt in option_matches]
    else:
        # 如果没有找到选项，尝试提取"选项"部分
        options_section = re.search(r'选项[：:]\s*(.+?)(?:\n\n|$)', response, re.DOTALL)
        if options_section:
            # 按行分割并清理
            lines = options_section.group(1).strip().split('\n')
            options = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
    
    # 如果仍然没有选项，至少提供一个默认选项
    if not options:
        options = ["继续执行查询", "取消查询"]
    
    return clarification_question, options


def should_ask_clarification(state: NL2SQLState) -> str:
    """
    条件判断函数：决定是否需要进入澄清流程
    
    Returns:
        "clarify": 需要澄清，输出澄清问题给用户
        "regenerate": 用户已回答，需要重新生成SQL
        "continue": 继续执行（不需要澄清）
    """
    needs_clarification = state.get("needs_clarification", False)
    clarification_answer = state.get("clarification_answer")
    
    # 如果用户已经回答了澄清问题，需要重新生成SQL
    if clarification_answer:
        return "regenerate"
    
    # 如果需要澄清且还没有生成澄清问题，进入澄清
    if needs_clarification and not state.get("clarification_question"):
        return "clarify"
    
    # 其他情况继续执行
    return "continue"

