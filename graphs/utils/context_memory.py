"""
统一的上下文记忆管理器
整合了对话历史管理和澄清功能
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import json


class ContextMemoryManager:
    """
    统一的上下文记忆管理器
    
    功能：
    1. 管理对话历史（查询、澄清、回答）
    2. 基于上下文判断是否需要澄清
    3. 格式化历史上下文用于SQL生成和澄清生成
    4. 限制历史长度，防止上下文过长
    """
    
    def __init__(self, session_id: str, max_history: int = 10):
        """
        初始化上下文记忆管理器
        
        Args:
            session_id: 会话ID
            max_history: 最大历史记录数（默认10轮）
        """
        self.session_id = session_id
        self.max_history = max_history
        self.conversation_history: List[Dict[str, Any]] = []
    
    def add_query(self, question: str) -> None:
        """
        添加用户查询到历史
        
        Args:
            question: 用户问题
        """
        entry = {
            "role": "user",
            "content": question,
            "timestamp": datetime.now().isoformat(),
            "type": "query",
            "session_id": self.session_id
        }
        self.conversation_history.append(entry)
        self._trim_history()
    
    def add_clarification(self, clarification_question: str, 
                         options: Optional[List[str]] = None,
                         reasons: Optional[List[str]] = None) -> None:
        """
        添加澄清问题到历史
        
        Args:
            clarification_question: 澄清问题
            options: 澄清选项（如果有）
            reasons: 需要澄清的原因（如果有）
        """
        entry = {
            "role": "assistant",
            "content": clarification_question,
            "timestamp": datetime.now().isoformat(),
            "type": "clarification",
            "session_id": self.session_id,
            "options": options or [],
            "reasons": reasons or []
        }
        self.conversation_history.append(entry)
        self._trim_history()
    
    def add_clarification_answer(self, answer: str) -> None:
        """
        添加澄清回答到历史
        
        Args:
            answer: 用户对澄清问题的回答
        """
        entry = {
            "role": "user",
            "content": answer,
            "timestamp": datetime.now().isoformat(),
            "type": "clarification_answer",
            "session_id": self.session_id
        }
        self.conversation_history.append(entry)
        self._trim_history()
    
    def add_answer(self, answer: str, sql: Optional[str] = None, 
                   result_summary: Optional[Dict[str, Any]] = None) -> None:
        """
        添加系统答案到历史
        
        Args:
            answer: 系统生成的答案
            sql: 执行的SQL查询（可选）
            result_summary: 查询结果摘要（可选）
        """
        entry = {
            "role": "assistant",
            "content": answer,
            "timestamp": datetime.now().isoformat(),
            "type": "answer",
            "session_id": self.session_id
        }
        
        if sql:
            entry["sql"] = sql
        
        if result_summary:
            entry["result_summary"] = result_summary
        
        self.conversation_history.append(entry)
        self._trim_history()
    
    def add_chat_response(self, response: str) -> None:
        """
        添加聊天响应到历史
        
        Args:
            response: LLM的聊天回复
        """
        entry = {
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat(),
            "type": "chat",
            "session_id": self.session_id
        }
        self.conversation_history.append(entry)
        self._trim_history()
    
    def format_context_for_sql_generation(self, question: str, max_rounds: int = 5) -> str:
        """
        格式化历史上下文用于SQL生成
        
        Args:
            question: 当前问题
            max_rounds: 最多使用最近N轮对话（默认5轮）
            
        Returns:
            格式化后的上下文文本
        """
        if not self.conversation_history:
            return ""
        
        # 获取最近的对话（排除当前问题）
        recent_history = self.conversation_history[-max_rounds:]
        
        # 过滤掉澄清相关的对话（只保留查询和答案）
        filtered_history = []
        for entry in recent_history:
            entry_type = entry.get("type", "")
            if entry_type in ["query", "answer", "chat"]:
                filtered_history.append(entry)
        
        if not filtered_history:
            return ""
        
        # 格式化上下文
        context_lines = ["## 对话历史上下文"]
        context_lines.append("")
        
        for i, entry in enumerate(filtered_history, 1):
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            entry_type = entry.get("type", "")
            timestamp = entry.get("timestamp", "")
            
            # 格式化时间戳（只显示时间部分）
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp)
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = timestamp[:8] if len(timestamp) > 8 else timestamp
            else:
                time_str = ""
            
            if entry_type == "query":
                context_lines.append(f"### 第{i}轮对话 - 用户查询")
                context_lines.append(f"[{time_str}] 用户: {content}")
            elif entry_type == "answer":
                context_lines.append(f"### 第{i}轮对话 - 系统回答")
                context_lines.append(f"[{time_str}] 助手: {content}")
                
                # 如果有SQL，也显示
                sql = entry.get("sql")
                if sql:
                    context_lines.append(f"执行的SQL: {sql}")
                
                # 如果有结果摘要，显示基本信息（LLM可以从完整答案中自己理解关键发现）
                result_summary = entry.get("result_summary")
                if result_summary:
                    row_count = result_summary.get("row_count", 0)
                    if row_count > 0:
                        context_lines.append(f"查询返回 {row_count} 条记录")
            elif entry_type == "chat":
                context_lines.append(f"### 第{i}轮对话 - 聊天")
                context_lines.append(f"[{time_str}] 助手: {content}")
            
            context_lines.append("")
        
        context_lines.append("## 上下文理解提示")
        context_lines.append("注意：如果用户的问题涉及\"刚才\"、\"之前\"、\"上面\"、\"那\"、\"他们\"等指代，")
        context_lines.append("请参考对话历史上下文来理解用户意图。")
        context_lines.append("例如：\"那销售额最高的客户是谁？\" 中的\"那\"可能指代之前查询的客户列表。")
        context_lines.append("")
        
        return "\n".join(context_lines)
    
    def format_context_for_clarification(self, question: str, 
                                       candidate_sql: Optional[str] = None,
                                       max_rounds: int = 3) -> str:
        """
        格式化历史上下文用于澄清生成
        
        Args:
            question: 当前问题
            candidate_sql: 生成的SQL（如果有）
            max_rounds: 最多使用最近N轮对话（默认3轮）
            
        Returns:
            格式化后的上下文文本
        """
        if not self.conversation_history:
            return ""
        
        recent_history = self.conversation_history[-max_rounds:]
        
        context_lines = ["## 对话历史上下文"]
        context_lines.append("")
        
        for entry in recent_history:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            entry_type = entry.get("type", "")
            
            if entry_type == "query":
                context_lines.append(f"用户: {content}")
            elif entry_type == "answer":
                context_lines.append(f"助手: {content}")
                sql = entry.get("sql")
                if sql:
                    context_lines.append(f"SQL: {sql}")
            elif entry_type == "chat":
                context_lines.append(f"助手: {content}")
            
            context_lines.append("")
        
        return "\n".join(context_lines)
    
    def check_needs_clarification(self, question: str, 
                                  candidate_sql: Optional[str] = None) -> Dict[str, Any]:
        """
        基于历史上下文检查是否需要澄清
        
        Args:
            question: 当前问题
            candidate_sql: 生成的SQL（如果有）
            
        Returns:
            {
                "needs_clarification": bool,
                "reasons": List[str],
                "clarification_type": str
            }
        """
        from graphs.nodes.clarify import check_if_needs_clarification
        
        # 首先使用原有的澄清判断逻辑
        clarification_check = check_if_needs_clarification(question, candidate_sql)
        
        # 如果原有逻辑判断不需要澄清，直接返回
        if not clarification_check.get("needs_clarification", False):
            return clarification_check
        
        # 如果原有逻辑判断需要澄清，再检查历史上下文
        # 检查是否有指代词（那、他们、刚才等）
        reference_keywords = ["那", "他们", "刚才", "之前", "上面", "这个", "那个", "这些", "那些"]
        has_reference = any(ref in question for ref in reference_keywords)
        
        if has_reference:
            # 检查历史中是否有相关查询
            recent_queries = [
                h for h in self.conversation_history[-5:] 
                if h.get("type") == "query"
            ]
            recent_answers = [
                h for h in self.conversation_history[-5:] 
                if h.get("type") == "answer"
            ]
            
            # 如果有历史查询和答案，可能不需要澄清（上下文已明确）
            if recent_queries and recent_answers:
                # 检查历史答案中是否包含相关信息
                last_answer = recent_answers[-1] if recent_answers else None
                if last_answer:
                    answer_content = last_answer.get("content", "")
                    result_summary = last_answer.get("result_summary", {})
                    
                    # 如果历史答案中有内容，且问题包含指代词，可能不需要澄清
                    # LLM可以从完整答案内容中自己理解实体关系，不需要我们提取
                    if answer_content and has_reference:
                        # 简单检查：如果历史答案不为空，且问题有指代词，可能上下文已明确
                        # 更精确的判断应该由LLM在生成SQL时基于完整上下文进行
                        pass
        
        # 返回原有的澄清判断结果
        return clarification_check
    
    def get_recent_history(self, n: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取最近N轮对话
        
        Args:
            n: 轮数（如果为None，返回所有历史）
            
        Returns:
            对话历史列表
        """
        if n is None:
            return self.conversation_history.copy()
        
        return self.conversation_history[-n:].copy()
    
    def get_all_history(self) -> List[Dict[str, Any]]:
        """
        获取所有对话历史
        
        Returns:
            对话历史列表
        """
        return self.conversation_history.copy()
    
    def _trim_history(self) -> None:
        """限制历史长度，删除最旧的记录"""
        if len(self.conversation_history) > self.max_history:
            # 保留最近的记录
            self.conversation_history = self.conversation_history[-self.max_history:]
    
    def clear_history(self) -> None:
        """清空对话历史"""
        self.conversation_history = []
    
    def export_history(self) -> str:
        """
        导出对话历史为JSON字符串
        
        Returns:
            JSON格式的对话历史
        """
        return json.dumps(self.conversation_history, ensure_ascii=False, indent=2)
    
    def import_history(self, history_json: str) -> None:
        """
        从JSON字符串导入对话历史
        
        Args:
            history_json: JSON格式的对话历史
        """
        try:
            self.conversation_history = json.loads(history_json)
            self._trim_history()
        except json.JSONDecodeError as e:
            print(f"⚠️  导入对话历史失败: {e}")


# 全局上下文管理器存储（按session_id存储）
_context_managers: Dict[str, ContextMemoryManager] = {}


def get_context_manager(session_id: str, max_history: int = 10) -> ContextMemoryManager:
    """
    获取或创建上下文管理器
    
    Args:
        session_id: 会话ID
        max_history: 最大历史记录数
        
    Returns:
        ContextMemoryManager实例
    """
    if session_id not in _context_managers:
        _context_managers[session_id] = ContextMemoryManager(
            session_id=session_id,
            max_history=max_history
        )
    
    return _context_managers[session_id]


def clear_context_manager(session_id: str) -> None:
    """
    清除指定会话的上下文管理器
    
    Args:
        session_id: 会话ID
    """
    if session_id in _context_managers:
        del _context_managers[session_id]

