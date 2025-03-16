import os
import time
import sys
import json
import datetime
from pathlib import Path
from typing import Optional, Generator, Any, Dict, List, Iterable, Tuple
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


class ChatHistory:
    """聊天历史记录类，负责管理跨会话的历史记录"""
    def __init__(self, history_file: str = None):
        """初始化聊天历史记录
        
        Args:
            history_file: 历史记录文件路径，默认为用户主目录下的 .azure_chat_history.json
        """
        if history_file is None:
            home_dir = str(Path.home())
            self.history_file = os.path.join(home_dir, ".azure_chat_history.json")
        else:
            self.history_file = history_file
        
        # 确保历史记录文件存在
        if not os.path.exists(self.history_file):
            # 创建空的历史记录文件
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def save_session(self, messages: List[Dict[str, Any]]) -> None:
        """保存当前会话到历史记录
        
        Args:
            messages: 当前会话的消息列表
        """
        # 跳过只有系统消息的会话
        if len(messages) <= 1:
            return
            
        # 转换消息格式，只保留角色和内容
        simplified_messages = []
        for msg in messages:
            if hasattr(msg, "role") and hasattr(msg, "content"):
                simplified_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            elif isinstance(msg, dict) and "role" in msg and "content" in msg:
                simplified_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # 读取现有历史记录
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            history = []
        
        # 添加新会话，包含时间戳
        history.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "messages": simplified_messages
        })
        
        # 保存更新后的历史记录
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def load_history(self) -> List[Dict[str, Any]]:
        """加载历史记录
        
        Returns:
            历史记录列表
        """
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def get_session_count(self) -> int:
        """获取历史会话数量
        
        Returns:
            历史会话数量
        """
        history = self.load_history()
        return len(history)
    
    def get_session(self, index: int) -> Tuple[str, List[Dict[str, str]]]:
        """获取指定索引的历史会话
        
        Args:
            index: 会话索引
            
        Returns:
            (时间戳, 消息列表)
        """
        history = self.load_history()
        if 0 <= index < len(history):
            session = history[index]
            return session["timestamp"], session["messages"]
        return "", []
    
    def display_session(self, index: int) -> None:
        """显示指定索引的历史会话
        
        Args:
            index: 会话索引
        """
        timestamp, messages = self.get_session(index)
        if not timestamp:
            print("未找到历史会话")
            return
        
        # 格式化时间戳
        try:
            dt = datetime.datetime.fromisoformat(timestamp)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            formatted_time = timestamp
        
        print(f"\n===== 历史会话 {index + 1} ({formatted_time}) =====")
        
        for msg in messages:
            if msg["role"] == "system":
                continue
            elif msg["role"] == "user":
                print(f"\n用户: {msg['content']}")
            elif msg["role"] == "assistant":
                print(f"\n助手: {msg['content']}")
        print("\n" + "=" * 50)
    
    def browse_history(self) -> None:
        """浏览历史会话"""
        history = self.load_history()
        if not history:
            print("没有历史会话记录")
            return
        
        session_count = len(history)
        page_size = 5
        current_page = 0
        total_pages = (session_count + page_size - 1) // page_size
        
        while True:
            # 清屏
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print(f"历史会话记录 (第 {current_page + 1}/{total_pages} 页)")
            print("=" * 50)
            
            # 显示当前页的会话
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, session_count)
            
            for i in range(start_idx, end_idx):
                session = history[i]
                # 格式化时间戳
                try:
                    dt = datetime.datetime.fromisoformat(session["timestamp"])
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    formatted_time = session["timestamp"]
                
                # 提取第一个用户问题作为摘要
                summary = "空会话"
                for msg in session["messages"]:
                    if msg["role"] == "user":
                        summary = msg["content"]
                        if len(summary) > 60:
                            summary = summary[:57] + "..."
                        break
                
                print(f"{i + 1}. [{formatted_time}] {summary}")
            
            print("\n" + "=" * 50)
            print("操作: [数字]查看详情 | [n]下一页 | [p]上一页 | [q]退出")
            
            choice = input("请输入: ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == 'n':
                if current_page < total_pages - 1:
                    current_page += 1
            elif choice == 'p':
                if current_page > 0:
                    current_page -= 1
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < session_count:
                    self.display_session(idx)
                    input("按回车键继续...")
                else:
                    print("无效的会话索引")
                    time.sleep(1)
            else:
                print("无效的输入")
                time.sleep(1)
    
    def search_history(self, keyword: str) -> None:
        """搜索历史会话
        
        Args:
            keyword: 搜索关键词
        """
        history = self.load_history()
        if not history:
            print("没有历史会话记录")
            return
        
        results = []
        
        # 搜索所有会话
        for i, session in enumerate(history):
            for msg in session["messages"]:
                if keyword.lower() in msg["content"].lower():
                    results.append((i, session["timestamp"]))
                    break
        
        if not results:
            print(f"未找到包含关键词 '{keyword}' 的历史会话")
            return
        
        print(f"找到 {len(results)} 个包含关键词 '{keyword}' 的历史会话:")
        print("=" * 50)
        
        for i, (idx, timestamp) in enumerate(results):
            # 格式化时间戳
            try:
                dt = datetime.datetime.fromisoformat(timestamp)
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                formatted_time = timestamp
            
            print(f"{i + 1}. [{formatted_time}] 会话 {idx + 1}")
        
        print("\n" + "=" * 50)
        print("输入数字查看详情，或按回车键返回")
        
        choice = input("请输入: ").strip()
        
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                self.display_session(results[idx][0])


def main():
    """主函数，实现一问一答的交互形式"""
    try:
        # 初始化历史记录管理器
        chat_history = ChatHistory()
        
        # 初始化配置和客户端
        config = AzureConfig()
        client = AzureClient(config)
        
        # 创建聊天会话
        chat_session = ChatSession(client)
        
        print("欢迎使用DeepSeek聊天助手！输入'退出'或'exit'结束对话。")
        print("支持编辑功能：Backspace删除，Home跳到行首，End跳到行尾，方向键移动光标")
        print("已启用流式响应模式，回复将实时显示")
        print("特殊命令：'history'查看历史会话，'search 关键词'搜索历史会话")
        
        # 开始对话循环
        while True:
            # 获取用户输入
            user_input = chat_session.get_user_input()
            
            # 处理空输入
            if not user_input:
                continue
                
            # 检查是否退出
            if user_input.lower() in ['退出', 'exit', 'quit', 'q']:
                # 保存当前会话到历史记录
                chat_history.save_session(chat_session.messages)
                chat_session.print_final_stats()
                break
            
            # 检查是否查看历史
            if user_input.lower() == 'history':
                chat_history.browse_history()
                continue
            
            # 检查是否搜索历史
            if user_input.lower().startswith('search '):
                keyword = user_input[7:].strip()
                if keyword:
                    chat_history.search_history(keyword)
                else:
                    print("请提供搜索关键词")
                continue
            
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
