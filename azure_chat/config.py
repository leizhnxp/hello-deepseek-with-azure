"""
Azure配置模块，负责加载和管理Azure相关配置
"""

import os
from dotenv import load_dotenv


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
