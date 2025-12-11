"""
NL2SQL 自然语言查询助手
面向最终用户的简洁版本
"""
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime
import os
import io
from contextlib import redirect_stdout, redirect_stderr

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from graphs.base_graph import run_query
from graphs.state import NL2SQLState


class NL2SQLChat:
    """NL2SQL 自然语言查询助手"""
    
    def __init__(self):
        self.session_id = f"chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.user_id = "user"
        self.current_state: Optional[NL2SQLState] = None
        self.show_sql = False  # 是否显示SQL（默认隐藏）
        
    def print_welcome(self):
        """打印欢迎信息"""
        print("\n" + "=" * 60)
        print("🤖 NL2SQL 自然语言查询助手")
        print("=" * 60)
        print("💡 提示：")
        print("  - 直接用自然语言提问，例如：'查询每个客户的订单数量'")
        print("  - 输入 'help' 查看帮助")
        print("  - 输入 'quit' 退出")
        print("=" * 60 + "\n")
    
    def print_help(self):
        """打印帮助信息"""
        print("\n" + "=" * 60)
        print("📖 使用帮助")
        print("=" * 60)
        print("\n基本使用：")
        print("  直接输入您的问题，例如：")
        print("    • 查询每个客户的订单数量")
        print("    • 查询客户ID为1的客户信息")
        print("    • 统计每个城市的客户数量")
        print("    • 查询销售额最高的前10个客户")
        print("\n命令：")
        print("  help          - 显示此帮助")
        print("  quit / exit   - 退出程序")
        print("  clear         - 清屏")
        print("  sql           - 切换显示/隐藏SQL查询")
        print("=" * 60 + "\n")
    
    def clear_screen(self):
        """清屏"""
        os.system('cls' if os.name == 'nt' else 'clear')
        self.print_welcome()
    
    def format_answer(self, answer: str) -> str:
        """格式化答案，使其更易读"""
        # 如果答案包含markdown格式，尝试美化
        lines = answer.split('\n')
        formatted_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                formatted_lines.append('')
                continue
            
            # 处理标题
            if line.startswith('###'):
                formatted_lines.append('')
                formatted_lines.append('📌 ' + line.replace('###', '').strip())
                formatted_lines.append('─' * 50)
            elif line.startswith('##'):
                formatted_lines.append('')
                formatted_lines.append('🔹 ' + line.replace('##', '').strip())
                formatted_lines.append('─' * 50)
            elif line.startswith('#'):
                formatted_lines.append('')
                formatted_lines.append('🔸 ' + line.replace('#', '').strip())
                formatted_lines.append('─' * 50)
            # 处理列表项
            elif line.startswith('-') or line.startswith('•'):
                formatted_lines.append('  ' + line)
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def handle_clarification(self, state: NL2SQLState) -> Optional[str]:
        """处理澄清问题（用户友好版本）"""
        clarification_question = state.get('clarification_question')
        clarification_options = state.get('clarification_options', [])
        clarification_count = state.get('clarification_count', 0)
        
        print(f"\n❓ {clarification_question}")
        
        if clarification_options:
            print("\n请选择：")
            for i, opt in enumerate(clarification_options, 1):
                print(f"  {i}. {opt}")
        
        print(f"\n💡 提示：输入选项编号，或直接输入答案（第 {clarification_count}/3 次澄清）")
        
        user_input = input("\n> ").strip()
        
        if user_input.lower() in ['skip', '跳过']:
            return None
        
        # 如果是数字，选择对应选项
        if user_input.isdigit():
            idx = int(user_input) - 1
            if 0 <= idx < len(clarification_options):
                return clarification_options[idx]
        
        return user_input if user_input else None
    
    def process_query(self, question: str, clarification_answer: Optional[str] = None):
        """处理查询（静默模式，不显示中间步骤）"""
        try:
            # 重定向所有输出到空设备，隐藏中间步骤
            f = io.StringIO()
            with redirect_stdout(f), redirect_stderr(f):
                # 静默运行查询
                result = run_query(
                    question=question,
                    session_id=self.session_id,
                    user_id=self.user_id,
                    clarification_answer=clarification_answer
                )
            
            self.current_state = result
            
            # 检查是否需要澄清（澄清问题需要用户交互，不能完全静默）
            if result.get('needs_clarification'):
                # 澄清时需要显示问题，所以暂时恢复输出
                clarification_answer = self.handle_clarification(result)
                
                if clarification_answer:
                    # 重新运行查询，带上澄清答案（会再次静默）
                    return self.process_query(question, clarification_answer)
                else:
                    print("⚠️  已跳过澄清，继续处理...\n")
                    # 跳过澄清后，需要重新静默运行
                    f = io.StringIO()
                    with redirect_stdout(f), redirect_stderr(f):
                        result = run_query(
                            question=question,
                            session_id=self.session_id,
                            user_id=self.user_id,
                            clarification_answer=None
                        )
                    self.current_state = result
                    # 继续执行后续的检查和显示逻辑
            
            # 检查执行结果
            execution_result = result.get('execution_result')
            if not execution_result:
                print("❌ 查询执行失败：未获取到执行结果")
                return
            
            if not execution_result.get('ok'):
                error = execution_result.get('error', '未知错误')
                print(f"❌ 查询执行失败：{error}")
                return
            
            # 显示答案
            answer = result.get('answer')
            if answer:
                print("\n" + "=" * 60)
                print("📊 查询结果")
                print("=" * 60)
                print(self.format_answer(answer))
                print("=" * 60)
            else:
                # 如果没有生成答案，显示基本信息
                row_count = execution_result.get('row_count', 0)
                columns = execution_result.get('columns', [])
                rows = execution_result.get('rows', [])
                
                print("\n" + "=" * 60)
                print("📊 查询结果")
                print("=" * 60)
                
                if row_count == 0:
                    print("查询结果为空，没有找到匹配的数据。")
                else:
                    print(f"✓ 查询成功，共找到 {row_count} 条记录")
                    
                    if row_count <= 10:
                        print("\n数据：")
                        for i, row in enumerate(rows, 1):
                            print(f"  [{i}] {row}")
                    else:
                        print(f"\n前5条数据：")
                        for i, row in enumerate(rows[:5], 1):
                            print(f"  [{i}] {row}")
                        print(f"  ... 还有 {row_count - 5} 条记录")
                
                print("=" * 60)
            
            # 可选：显示SQL（如果用户开启了显示）
            if self.show_sql:
                sql = result.get('candidate_sql')
                if sql:
                    print(f"\n💻 执行的SQL查询：")
                    print(f"   {sql}")
                    print()
            
        except Exception as e:
            print(f"\n❌ 发生错误：{str(e)}")
            print("💡 提示：请检查问题描述是否清晰，或联系管理员")
    
    def run(self):
        """运行聊天程序"""
        self.print_welcome()
        
        while True:
            try:
                # 获取用户输入
                user_input = input("💬 请输入您的问题: ").strip()
                
                if not user_input:
                    continue
                
                # 处理命令
                if user_input.lower() in ['quit', 'exit', 'q', '退出']:
                    print("\n👋 感谢使用，再见！\n")
                    break
                
                elif user_input.lower() == 'help':
                    self.print_help()
                
                elif user_input.lower() == 'clear':
                    self.clear_screen()
                
                elif user_input.lower() == 'sql':
                    self.show_sql = not self.show_sql
                    status = "显示" if self.show_sql else "隐藏"
                    print(f"\n💡 SQL查询已{status}\n")
                
                else:
                    # 作为问题处理
                    print(f"\n🔍 正在处理：{user_input}...")
                    # 处理查询（内部会重定向输出，隐藏中间步骤）
                    self.process_query(user_input)
                    print()  # 空行分隔
                
            except KeyboardInterrupt:
                print("\n\n⚠️  操作已中断")
                print("💡 提示：输入 'quit' 退出程序\n")
                continue
            except EOFError:
                print("\n\n👋 感谢使用，再见！\n")
                break
            except Exception as e:
                print(f"\n❌ 发生错误：{str(e)}")
                print("💡 提示：请重试或联系管理员\n")


def main():
    """主函数"""
    try:
        # 检查环境
        from tools.db import db_client
        from tools.llm_client import llm_client
        
        # 测试连接
        if not db_client.test_connection():
            print("❌ 数据库连接失败，请检查配置")
            return 1
        
        # 测试LLM
        try:
            llm_client.chat(prompt="test")
        except Exception as e:
            print(f"❌ LLM连接失败：{e}")
            print("💡 请检查LLM配置（.env文件）")
            return 1
        
        # 启动聊天程序
        chat = NL2SQLChat()
        chat.run()
        
        return 0
        
    except ImportError as e:
        print(f"❌ 导入错误：{e}")
        print("💡 请确保已安装所有依赖：pip install -r requirements.txt")
        return 1
    except Exception as e:
        print(f"❌ 启动失败：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

