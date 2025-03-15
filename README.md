# Azure DeepSeek 聊天助手

这是一个基于 Azure AI 服务的流式聊天助手，使用 DeepSeek 模型提供流畅的对话体验。该项目展示了如何使用 Azure AI SDK 实现实时流式响应，以及如何跟踪和显示各种性能指标。

## 功能特点

- **流式响应**: 实时显示 AI 助手的回复，提供更自然的对话体验
- **性能统计**: 跟踪并显示 token 使用情况、响应时间和输出速率
- **友好界面**: 使用 prompt_toolkit 提供更好的命令行交互体验，支持历史记录和编辑功能
- **错误处理**: 完善的错误处理机制，确保程序在各种情况下都能稳定运行
- **灵活配置**: 通过环境变量轻松配置 Azure 端点、API 密钥和模型名称

## 项目结构

```
hello-azure-deepseek/
├── chat-with-stream.py  # 主要聊天应用（支持流式响应）
├── main.py              # 简单的示例脚本，展示基本 API 调用
├── .env-template        # 环境变量模板
├── pyproject.toml       # 项目依赖配置
└── README.md            # 项目文档
```

## 主要组件

### 1. AzureConfig 类
负责加载和验证 Azure 配置信息，包括端点、模型名称和 API 密钥。

### 2. AzureClient 类
封装了与 Azure AI 服务的交互逻辑，提供流式响应方法：
- `get_streaming_response()`: 获取实时流式响应，包括处理增量内容和获取 token 统计

### 3. ChatResponse 类
数据类，用于封装聊天响应的各种属性，包括内容、token 统计和性能指标。

### 4. ChatSession 类
管理整个聊天会话，包括消息历史、用户输入处理和统计信息跟踪。

## 安装与设置

1. 克隆仓库:
```bash
git clone <repository-url>
cd hello-azure-deepseek
```

2. 安装依赖:
```bash
pip install -e .
# 或使用 uv
uv pip install -e .
```

3. 配置环境变量:
```bash
cp .env-template .env
# 编辑 .env 文件，填入你的 Azure 凭据
```

## 使用方法

运行聊天助手:
```bash
python chat-with-stream.py
# 或使用 uv
uv run python chat-with-stream.py
```

基本示例:
```bash
python main.py
```

## 环境变量配置

在 `.env` 文件中设置以下变量:

```
AZURE_API_KEY=your_api_key
AZURE_ENDPOINT=https://your_endpoint.eastus2.models.ai.azure.com
AZURE_MODEL_NAME=DeepSeek-R1
```

## 依赖项

- Python >= 3.12
- azure-ai-inference >= 1.0.0b9
- python-dotenv >= 1.0.0
- prompt-toolkit >= 3.0.0

## 性能指标说明

聊天助手会显示以下性能指标：

- **本轮耗时**: 当前对话轮次的总耗时（秒）
- **提示词tokens**: 输入提示使用的 token 数量
- **完成词tokens**: 模型生成回复使用的 token 数量
- **总tokens**: 提示词和完成词 token 的总和
- **输出速率**: 每秒输出的字符数
- **Token输出速率**: 每秒生成的 token 数
- **总字符数**: 回复的总字符数
- **累计耗时**: 会话开始以来的总耗时

## 注意事项

- 流式响应功能需要 Azure AI SDK 1.0.0b9 或更高版本
- 确保你的 Azure 账户有足够的配额来使用 DeepSeek 模型
- 在某些情况下，如果无法直接从流式响应中获取 token 统计信息，程序会尝试使用备选方法来估算