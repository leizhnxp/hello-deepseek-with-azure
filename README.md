# Azure DeepSeek 聊天助手

这是一个基于 Azure AI 服务的流式聊天助手，使用 DeepSeek 模型提供流畅的对话体验。该项目展示了如何使用 Azure AI SDK 实现实时流式响应，以及如何跟踪和显示各种性能指标。

## 功能特点

- **流式响应**: 实时显示 AI 助手的回复，提供更自然的对话体验
- **性能统计**: 跟踪并显示 token 使用情况、响应时间和输出速率
- **友好界面**: 使用 prompt_toolkit 提供更好的命令行交互体验，支持历史记录和编辑功能
- **错误处理**: 完善的错误处理机制，确保程序在各种情况下都能稳定运行
- **灵活配置**: 通过环境变量轻松配置 Azure 端点、API 密钥和模型名称
- **历史会话记录**: 支持保存和浏览历史会话，可以查看和搜索过去的对话内容
- **模块化结构**: 采用模块化设计，提高代码的可维护性和可扩展性

## 项目结构

```
hello-azure-deepseek/
├── azure_chat/                  # 主要包目录
│   ├── __init__.py              # 包初始化文件
│   ├── config.py                # 配置模块
│   ├── client.py                # Azure客户端模块
│   ├── models.py                # 数据模型模块
│   ├── session.py               # 聊天会话模块
│   └── history.py               # 聊天历史记录模块
├── chat_app.py                  # 新的主程序入口
├── chat-with-stream.py          # 原始的单文件版本(保留)
├── .env-template                # 环境变量模板
├── pyproject.toml               # 项目依赖配置
└── README.md                    # 项目文档
```

## 主要组件

### 1. AzureConfig 类 (azure_chat/config.py)
负责加载和验证 Azure 配置信息，包括端点、模型名称和 API 密钥。

### 2. AzureClient 类 (azure_chat/client.py)
封装了与 Azure AI 服务的交互逻辑，提供流式响应方法：
- `get_streaming_response()`: 获取实时流式响应，包括处理增量内容和获取 token 统计

### 3. ChatResponse 类 (azure_chat/models.py)
数据类，用于封装聊天响应的各种属性，包括内容、token 统计和性能指标。

### 4. ChatSession 类 (azure_chat/session.py)
管理整个聊天会话，包括消息历史、用户输入处理和统计信息跟踪。

### 5. ChatHistory 类 (azure_chat/history.py)
管理跨会话的历史记录，支持保存、浏览和搜索历史会话：
- `save_session()`: 保存当前会话到历史记录
- `browse_history()`: 浏览历史会话记录
- `search_history()`: 搜索包含特定关键词的历史会话

## 安装与设置

1. 克隆仓库:
```bash
git clone <repository-url>
cd hello-azure-deepseek
```

2. 安装依赖:
```bash
# 使用 pip
pip install -e .

# 或使用 uv (推荐)
uv pip install -e .

# 或安装开发依赖
uv pip install -e ".[dev]"
```

3. 配置环境变量:
```bash
cp .env-template .env
# 编辑 .env 文件，填入你的 Azure 凭据
```

## 使用方法

运行聊天助手:
```bash
# 使用新的模块化版本
python chat_app.py
# 或使用 uv
uv run python chat_app.py

# 或者使用原始单文件版本
python chat-with-stream.py
# 或使用 uv
uv run python chat-with-stream.py
```

基本示例:
```bash
python main.py
# 或使用 uv
uv run python main.py
```

### 特殊命令

在聊天过程中，您可以使用以下特殊命令：

- `history`: 浏览历史会话记录
- `search 关键词`: 搜索包含特定关键词的历史会话
- `exit`/`退出`/`quit`/`q`: 退出聊天应用

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

## 历史记录功能

历史记录功能允许您在不同会话之间保存和查看对话历史：

- 历史记录默认保存在用户主目录下的 `.azure_chat_history.json` 文件中
- 每次会话结束时，会自动保存当前会话到历史记录
- 您可以使用 `history` 命令浏览历史会话，支持分页显示和详细查看
- 您可以使用 `search 关键词` 命令搜索包含特定关键词的历史会话

历史记录仅用于查看，不会自动添加到新会话的上下文中，确保每次新会话都是独立的。

## 注意事项

- 流式响应功能需要 Azure AI SDK 1.0.0b9 或更高版本
- 确保你的 Azure 账户有足够的配额来使用 DeepSeek 模型
- 在某些情况下，如果无法直接从流式响应中获取 token 统计信息，程序会尝试使用备选方法来估算
- 历史记录功能会将会话内容保存在本地文件中，请确保不要在历史记录中包含敏感信息