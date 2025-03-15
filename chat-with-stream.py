import os
import time
import sys
from typing import Optional, Generator, Any, Dict, List, Iterable
from dotenv import load_dotenv
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage, ChatRequestMessage
from azure.ai.inference.models import StreamingChatCompletionsUpdate
from azure.core.credentials import AzureKeyCredential
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style


class ChatResponse:
    """封装聊天响应的数据类"""
    def __init__(self):
        self.content: str = ""
        self.prompt_tokens: int = 0
        self.completion_tokens: int = 0
        self.total_tokens: int = 0
        self.total_chars: int = 0
        self.elapsed_time: float = 0
        self.print_rate: float = 0
        self.token_rate: float = 0  # token输出速率


class AzureConfig:
    """Azure配置类，负责管理Azure相关配置"""
    def __init__(self):
        # 加载.env文件中的环境变量
        load_dotenv()
        
        # 从环境变量中获取配置
        self.endpoint = os.getenv("AZURE_ENDPOINT")
        self.model_name = os.getenv("AZURE_MODEL_NAME")
        self.api_key = os.getenv("AZURE_API_KEY")
        
        # 验证配置完整性
        if not all([self.endpoint, self.model_name, self.api_key]):
            raise ValueError("环境变量未正确设置，请检查 .env 文件")


class AzureClient:
    """Azure客户端类，负责与Azure API交互"""
    def __init__(self, config: AzureConfig):
        """初始化Azure AI客户端"""
        self.config = config
        self.client = ChatCompletionsClient(
            endpoint=config.endpoint,
            credential=AzureKeyCredential(config.api_key),
        )
        self.model_name = config.model_name
        
    def get_streaming_response(self, 
                              messages: List[ChatRequestMessage], 
                              temperature: float = 0.7, 
                              top_p: float = 0.95) -> ChatResponse:
        """获取流式响应"""
        response = ChatResponse()
        start_time = time.time()
        total_chars = 0
        last_chunk = None
        
        try:
            # 明确指定 stream=True 来启用流式响应
            stream_response = self.client.complete(
                messages=messages,
                max_tokens=32768,
                model=self.model_name,
                temperature=temperature,
                top_p=top_p,
                stream=True  # 关键参数：启用流式响应
            )
            
            # 处理流式响应
            for chunk in stream_response:
                # 保存最后一个块，用于获取token统计
                last_chunk = chunk
                
                if not hasattr(chunk, 'choices') or not chunk.choices:
                    continue
                
                # 处理增量内容
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    response.content += content
                    # 立即打印内容
                    print(content, end="", flush=True)
                    # 累计字符数
                    total_chars += len(content)
            
            # 计算打印速率
            end_time = time.time()
            elapsed_time = end_time - start_time
            response.elapsed_time = elapsed_time
            response.total_chars = total_chars
            response.print_rate = total_chars / elapsed_time if elapsed_time > 0 else 0
            
            # 流式响应完成后，获取完整的token统计信息
            # 方法1: 从最后一个块获取token统计（如果有）
            if last_chunk and hasattr(last_chunk, 'usage') and last_chunk.usage:
                response.prompt_tokens = last_chunk.usage.prompt_tokens
                response.completion_tokens = last_chunk.usage.completion_tokens
                response.total_tokens = last_chunk.usage.total_tokens
                response.token_rate = response.completion_tokens / elapsed_time if elapsed_time > 0 else 0
            
            # 方法2: 如果最后一个块没有token统计，则进行额外的API调用获取统计信息
            if response.total_tokens == 0:
                try:
                    # 创建一个新的非流式请求来获取token统计
                    non_stream_response = self.client.complete(
                        messages=messages + [AssistantMessage(content=response.content)],
                        max_tokens=0,  # 设置为0，只获取统计信息
                        model=self.model_name,
                        stream=False
                    )
                    
                    if hasattr(non_stream_response, 'usage') and non_stream_response.usage:
                        response.prompt_tokens = non_stream_response.usage.prompt_tokens
                        # 由于我们包含了助手的回复，所以这里不需要completion_tokens
                        response.completion_tokens = len(response.content) // 4  # 估算completion tokens
                        response.total_tokens = response.prompt_tokens + response.completion_tokens
                        response.token_rate = response.completion_tokens / elapsed_time if elapsed_time > 0 else 0
                except Exception as e:
                    print(f"\n获取token统计信息时发生错误: {str(e)}")
                    # 使用估算的token数量
                    response.prompt_tokens = len(str(messages)) // 4  # 粗略估算
                    response.completion_tokens = len(response.content) // 4  # 粗略估算
                    response.total_tokens = response.prompt_tokens + response.completion_tokens
                    response.token_rate = response.completion_tokens / elapsed_time if elapsed_time > 0 else 0
            
            return response
            
        except Exception as e:
            print(f"\n处理流式响应时发生错误: {str(e)}")
            raise  # 不再回退到普通响应，而是直接抛出异常


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


def main():
    """主函数，实现一问一答的交互形式"""
    try:
        # 初始化配置和客户端
        config = AzureConfig()
        client = AzureClient(config)
        
        # 创建聊天会话
        chat_session = ChatSession(client)
        
        print("欢迎使用DeepSeek聊天助手！输入'退出'或'exit'结束对话。")
        print("支持编辑功能：Backspace删除，Home跳到行首，End跳到行尾，方向键移动光标")
        print("已启用流式响应模式，回复将实时显示")
        
        # 开始对话循环
        while True:
            # 获取用户输入
            user_input = chat_session.get_user_input()
            
            # 处理空输入
            if not user_input:
                continue
                
            # 检查是否退出
            if user_input.lower() in ['退出', 'exit', 'quit', 'q']:
                chat_session.print_final_stats()
                break
            
            # 添加用户消息到历史
            chat_session.add_user_message(user_input)
            
            try:
                # 获取助手响应
                response = chat_session.get_assistant_response()
                
                # 打印统计信息
                chat_session.print_response_stats(response)
                
                # 将助手回复添加到消息历史
                chat_session.add_assistant_message(response.content)
                
            except Exception as e:
                print(f"\n发生错误: {str(e)}")
                print("请重试或检查网络连接")
    
    except Exception as e:
        print(f"程序初始化失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
