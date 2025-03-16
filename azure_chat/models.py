"""
数据模型模块，定义各种数据类和模型
"""


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
