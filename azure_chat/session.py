"""
聊天会话模块，负责管理聊天会话
"""

from typing import Dict, Any
from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style

from azure_chat.client import AzureClient
from azure_chat.models import ChatResponse


class ChatSession:
    """聊天会话类，负责管理聊天会话"""
    def __init__(self, client: AzureClient):
        self.client = client
        self.messages = [
            SystemMessage(content="你是一个有帮助的助手，请用中文回答问题。")
        ]
        self.session = PromptSession(
            history=InMemoryHistory(),
            style=Style.from_dict({
                'prompt': '#00aa00 bold',
            })
        )
        # 统计信息
        self.stats = {
            'total_time': 0,
            'total_prompt_tokens': 0,
            'total_completion_tokens': 0,
            'total_tokens': 0
        }
    
    def add_user_message(self, content: str) -> None:
        """添加用户消息到会话"""
        self.messages.append(UserMessage(content=content))
    
    def add_assistant_message(self, content: str) -> None:
        """添加助手消息到会话"""
        self.messages.append(AssistantMessage(content=content))
    
    def get_user_input(self) -> str:
        """获取用户输入"""
        try:
            return self.session.prompt("\n用户: ")
        except (KeyboardInterrupt, EOFError) as e:
            if isinstance(e, KeyboardInterrupt):
                print("\n操作被中断")
                return ""
            else:  # EOFError
                print("\n再见！")
                return "exit"
    
    def get_assistant_response(self) -> ChatResponse:
        """获取助手响应"""
        print("\n助手: ", end="", flush=True)
        
        # 获取流式响应
        response = self.client.get_streaming_response(self.messages)
        
        # 更新统计信息
        self.stats['total_time'] += response.elapsed_time
        self.stats['total_prompt_tokens'] += response.prompt_tokens
        self.stats['total_completion_tokens'] += response.completion_tokens
        self.stats['total_tokens'] += response.total_tokens
        
        return response
    
    def print_response_stats(self, response: ChatResponse) -> None:
        """打印响应统计信息"""
        # 打印本轮统计信息
        print(f"\n\n本轮耗时: {response.elapsed_time:.2f}秒")
        print(f"提示词tokens: {response.prompt_tokens}")
        print(f"完成词tokens: {response.completion_tokens}")
        print(f"总tokens: {response.total_tokens}")
        print(f"输出速率: {response.print_rate:.2f} 字符/秒")
        if response.token_rate > 0:
            print(f"Token输出速率: {response.token_rate:.2f} tokens/秒")
        print(f"总字符数: {response.total_chars}")
        print(f"累计耗时: {self.stats['total_time']:.2f}秒")
    
    def print_final_stats(self) -> None:
        """打印最终统计信息"""
        print("\n会话统计信息:")
        print(f"总耗时: {self.stats['total_time']:.2f}秒")
        print(f"总提示词tokens: {self.stats['total_prompt_tokens']}")
        print(f"总完成词tokens: {self.stats['total_completion_tokens']}")
        print(f"总tokens: {self.stats['total_tokens']}")
        print("感谢使用，再见！")
