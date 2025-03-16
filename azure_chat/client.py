"""
Azure客户端模块，负责与Azure API交互
"""

import time
from typing import List
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import ChatRequestMessage, AssistantMessage
from azure.core.credentials import AzureKeyCredential

from azure_chat.config import AzureConfig
from azure_chat.models import ChatResponse


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
